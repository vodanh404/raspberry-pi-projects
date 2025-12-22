import os
import sys
import time
import subprocess
import threading
import signal
import datetime
import pygame
import board
import busio
from PIL import Image, ImageFont, ImageDraw, ImageOps
from luma.core.interface.serial import spi as luma_spi
from luma.lcd.device import st7789
from xpt2046 import XPT2046

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & PHẦN CỨNG
# ==========================================
WIDTH, HEIGHT = 320, 240
BG_COLOR = "#1e1e2e"
ACCENT_COLOR = "#89b4fa"
WARN_COLOR = "#f38ba8"
SERIAL_SPEED = 60000000  # Tăng lên 60MHz để tối ưu FPS

USER_HOME = "/home/dinhphuc"
DIRS = {
    "MUSIC": os.path.join(USER_HOME, "Music"),
    "VIDEO": os.path.join(USER_HOME, "Videos"),
    "PHOTO": os.path.join(USER_HOME, "Pictures"),
    "BOOK":  os.path.join(USER_HOME, "Documents")
}

def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

font_icon = load_font(24); font_lg = load_font(18); font_md = load_font(14); font_sm = load_font(10)

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ
# ==========================================
def emergency_cleanup():
    os.system("pkill -9 ffplay")
    os.system("pkill -9 ffmpeg")
    pygame.mixer.music.stop()

try:
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=SERIAL_SPEED)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    device.backlight(True)
    
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26, width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900, baudrate=2000000)
except Exception as e:
    print(f"Lỗi: {e}"); sys.exit(1)

pygame.mixer.init()

# ==========================================
# 3. CLASS CHÍNH: PI MEDIA CENTER
# ==========================================
class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.running = True
        self.files = []; self.selected_idx = 0; self.scroll_offset = 0
        self.volume = 0.5; self.last_touch = 0
        self.video_stop_event = threading.Event()

    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        draw.text((WIDTH - 45, 5), datetime.datetime.now().strftime("%H:%M"), fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        items = [("Music", "♫", "#f9e2af"), ("Video", "►", "#f38ba8"), 
                 ("Photo", "🖼", "#a6e3a1"), ("Books", "bd", "#89b4fa"), ("BT", "ᛒ", "#cba6f7")]
        for i, (label, icon, color) in enumerate(items):
            x, y = (15 + (i%3)*105), (60 + (i//3)*85)
            draw.rounded_rectangle((x, y, x+90, y+70), radius=8, fill="#313244", outline=color, width=2)
            draw.text((x+35, y+10), icon, fill=color, font=font_icon)
            draw.text((x+25, y+45), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        display_list = self.files[self.scroll_offset:self.scroll_offset+5]
        for i, item in enumerate(display_list):
            idx = self.scroll_offset + i
            bg = "#585b70" if idx == self.selected_idx else BG_COLOR
            draw.rectangle((5, 55+i*30, WIDTH-5, 83+i*30), fill=bg)
            name = item['name'] if isinstance(item, dict) else item
            draw.text((10, 60+i*30), name[:30], fill="white", font=font_md)
        # Nút điều khiển
        draw.rectangle((0, 210, WIDTH, 240), fill="#313244")
        draw.text((20, 215), "▲ UP", fill="white", font=font_md)
        draw.text((130, 215), "[ OK ]", fill="#a6e3a1", font=font_md)
        draw.text((240, 215), "▼ DN", fill="white", font=font_md)

    def scan_bluetooth(self):
        """Quét và hiển thị thiết bị Bluetooth thực tế"""
        self.files = [{"name": "Đang quét...", "mac": ""}]
        self.render()
        try:
            # Bật adapter nếu đang tắt
            subprocess.run(["rfkill", "unblock", "bluetooth"])
            # Quét thiết bị
            out = subprocess.check_output(["bluetoothctl", "--timeout", "5", "scan", "on"], stderr=subprocess.STDOUT).decode()
            devices = subprocess.check_output(["bluetoothctl", "devices"]).decode().splitlines()
            self.files = []
            for d in devices:
                parts = d.split(' ', 2)
                if len(parts) >= 3:
                    self.files.append({"mac": parts[1], "name": parts[2]})
        except:
            self.files = [{"name": "Lỗi Bluetooth", "mac": ""}]
        self.render()

    def play_video(self, path):
        """Phát video tối ưu FPS và điều khiển âm lượng"""
        self.state = "PLAYING_VIDEO"
        emergency_cleanup()
        self.video_stop_event.clear()

        # ffplay cho âm thanh (hỗ trợ tăng giảm âm lượng qua phím số nếu có phím, hoặc điều khiển subprocess)
        audio_proc = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-volume', str(int(self.volume*100)), path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # ffmpeg tối ưu: giảm độ phân giải xuống đúng mức cần thiết và dùng pixel format nhanh
        video_cmd = ['ffmpeg', '-re', '-i', path, '-vf', f'scale={WIDTH}:{HEIGHT},format=rgb24', 
                     '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        video_proc = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3)

        try:
            while not self.video_stop_event.is_set():
                raw = video_proc.stdout.read(WIDTH * HEIGHT * 3)
                if not raw or audio_proc.poll() is not None: break
                
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw)
                img = ImageOps.invert(img) # Tùy chỉnh inversion cho LCD của bạn
                device.display(img)

                # Kiểm tra cảm ứng nhanh (Vùng trên: Vol+, Vùng dưới: Vol-, Giữa: Thoát)
                pt = touch.get_touch()
                if pt:
                    tx, ty = pt
                    if ty < 60: # Vol Up
                        self.volume = min(1.0, self.volume + 0.1)
                        os.system(f"amixer set Master {int(self.volume*100)}%")
                    elif ty > 180: # Vol Down
                        self.volume = max(0.0, self.volume - 0.1)
                        os.system(f"amixer set Master {int(self.volume*100)}%")
                    else: break # Thoát
        finally:
            audio_proc.terminate(); video_proc.terminate()
            self.state = "VIDEO"; self.render()

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "MENU":
            if 60 < y < 130:
                if 15 < x < 105: self.state = "MUSIC"; self.load_files("MUSIC", ('.mp3', '.wav'))
                elif 120 < x < 210: self.state = "VIDEO"; self.load_files("VIDEO", ('.mp4', '.avi'))
                elif 225 < x < 315: self.state = "PHOTO"; self.load_files("PHOTO", ('.jpg', '.png'))
            elif 145 < y < 215:
                if 15 < x < 105: self.state = "BOOK"; self.load_files("BOOK", ('.txt',))
                elif 120 < x < 210: self.state = "BT"; self.scan_bluetooth()
        
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            if y < 50 and x > 250: self.state = "MENU" # Nút BACK
            elif y > 200:
                if x < 100: self.selected_idx = max(0, self.selected_idx - 1)
                elif x > 220: self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                else: # OK
                    path = os.path.join(DIRS.get(self.state, ""), self.files[self.selected_idx] if self.state != "BT" else "")
                    if self.state == "VIDEO": self.play_video(path)
                    elif self.state == "MUSIC":
                        pygame.mixer.music.load(path); pygame.mixer.music.set_volume(self.volume); pygame.mixer.music.play()
                    elif self.state == "BT":
                        mac = self.files[self.selected_idx]['mac']
                        subprocess.run(["bluetoothctl", "connect", mac])
        self.render()

    def load_files(self, key, exts):
        self.files = [f for f in os.listdir(DIRS[key]) if f.lower().endswith(exts)]
        self.selected_idx = 0; self.scroll_offset = 0

    def render(self):
        if self.state == "PLAYING_VIDEO": return
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        if self.state == "MENU": self.draw_menu(draw)
        else: self.draw_list(draw, self.state)
        device.display(img)

    def run(self):
        self.render()
        while self.running:
            pt = touch.get_touch()
            if pt: self.handle_touch(*pt)
            time.sleep(0.05)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: (emergency_cleanup(), sys.exit(0)))
    app = PiMediaCenter(); app.run()
