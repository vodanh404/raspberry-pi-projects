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
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
WIDTH, HEIGHT = 320, 240
BG_COLOR = "#1e1e2e"
ACCENT_COLOR = "#89b4fa"
SERIAL_SPEED = 60000000 # Tốc độ cao để tăng FPS

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

font_lg = load_font(18); font_md = load_font(14); font_sm = load_font(10)

# ==========================================
# 2. KHỞI TẠO PHẦN CỨNG
# ==========================================
def emergency_cleanup():
    os.system("pkill -9 ffplay")
    os.system("pkill -9 ffmpeg")
    pygame.mixer.music.stop()

try:
    # LCD ST7789
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=SERIAL_SPEED)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    device.backlight(True)
    
    # Touch XPT2046
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26, 
                    width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900)
except Exception as e:
    print(f"Hardware Fail: {e}"); sys.exit(1)

pygame.mixer.init()

# ==========================================
# 3. CLASS CHÍNH
# ==========================================
class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.running = True
        self.files = []; self.selected_idx = 0; self.scroll_offset = 0
        self.volume = 50 # 0-100
        self.last_touch = 0

    def set_system_volume(self, val):
        self.volume = max(0, min(100, val))
        os.system(f"amixer set Master {self.volume}% > /dev/null 2>&1")
        pygame.mixer.music.set_volume(self.volume / 100.0)

    def draw_list(self, draw, title):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        draw.text((10, 5), f"{title} | Vol: {self.volume}%", fill="white", font=font_sm)
        
        # Nút BACK
        draw.rectangle((WIDTH-50, 2, WIDTH-5, 22), fill="#f38ba8")
        draw.text((WIDTH-45, 5), "BACK", fill="white", font=font_sm)

        items = self.files[self.scroll_offset:self.scroll_offset+6]
        for i, item in enumerate(items):
            idx = self.scroll_offset + i
            color = "#585b70" if idx == self.selected_idx else BG_COLOR
            draw.rectangle((5, 30+i*28, WIDTH-5, 55+i*28), fill=color)
            name = item['name'] if isinstance(item, dict) else item
            draw.text((15, 35+i*28), f"{idx+1}. {name[:28]}", fill="white", font=font_md)

        # Thanh điều hướng dưới cùng
        draw.rectangle((0, 210, WIDTH, 240), fill="#313244")
        draw.text((20, 215), "V-", fill="white", font=font_md)
        draw.text((60, 215), "UP", fill="white", font=font_md)
        draw.text((130, 215), "[ OK ]", fill="#a6e3a1", font=font_md)
        draw.text((210, 215), "DN", fill="white", font=font_md)
        draw.text((270, 215), "V+", fill="white", font=font_md)

    def scan_bluetooth(self):
        self.files = [{"name": "Scanning...", "mac": ""}]
        self.render()
        try:
            os.system("rfkill unblock bluetooth")
            time.sleep(1)
            # Dùng hcitool để nhanh hơn
            cmd = "hcitool scan | grep -v 'Scanning'"
            out = subprocess.check_output(cmd, shell=True).decode()
            self.files = []
            for line in out.splitlines():
                p = line.strip().split('\t')
                if len(p) >= 2: self.files.append({"mac": p[0], "name": p[1]})
        except: self.files = [{"name": "No devices found", "mac": ""}]
        self.render()

    def play_video(self, path):
        self.state = "PLAYING_VIDEO"
        emergency_cleanup()
        
        # ffplay cho âm thanh
        audio_cmd = ['ffplay', '-nodisp', '-autoexit', '-volume', str(self.volume), path]
        audio_proc = subprocess.Popen(audio_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # ffmpeg cho hình ảnh (Tối ưu buffer)
        video_cmd = ['ffmpeg', '-re', '-i', path, '-vf', f'scale={WIDTH}:{HEIGHT},format=rgb24', 
                     '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        video_proc = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3*2)

        try:
            while True:
                raw = video_proc.stdout.read(WIDTH * HEIGHT * 3)
                if not raw or audio_proc.poll() is not None: break
                
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw)
                img = ImageOps.invert(img) # Đảo màu cho ST7789
                device.display(img)

                # Chạm bất kỳ để thoát video
                if touch.is_touched(): break
        finally:
            audio_proc.terminate(); video_proc.terminate()
            emergency_cleanup()
            self.state = "VIDEO"; self.render()

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        # Logic Menu chính
        if self.state == "MENU":
            if 60 < y < 130:
                if 15 < x < 105: self.state = "MUSIC"; self.load_files("MUSIC", ('.mp3', '.wav'))
                elif 120 < x < 210: self.state = "VIDEO"; self.load_files("VIDEO", ('.mp4', '.avi'))
                elif 225 < x < 315: self.state = "PHOTO"; self.load_files("PHOTO", ('.jpg', '.png'))
            elif 145 < y < 215:
                if 120 < x < 210: self.state = "BT"; self.scan_bluetooth()
        
        # Logic trong danh sách
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BT"]:
            if y < 30 and x > WIDTH-60: self.state = "MENU" # Nút BACK
            elif y > 200:
                if x < 50: self.set_system_volume(self.volume - 10) # V-
                elif 50 < x < 100: # UP
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset: self.scroll_offset = self.selected_idx
                elif 250 < x: self.set_system_volume(self.volume + 10) # V+
                elif 200 < x < 250: # DN
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 6: self.scroll_offset += 1
                elif 110 < x < 190: # OK
                    if not self.files: return
                    item = self.files[self.selected_idx]
                    path = os.path.join(DIRS.get(self.state, ""), item if self.state != "BT" else "")
                    if self.state == "VIDEO": self.play_video(path)
                    elif self.state == "MUSIC":
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.play()
                    elif self.state == "BT":
                        os.system(f"bluetoothctl connect {item['mac']}")
        self.render()

    def load_files(self, key, exts):
        try:
            self.files = [f for f in os.listdir(DIRS[key]) if f.lower().endswith(exts)]
        except: self.files = []
        self.selected_idx = 0; self.scroll_offset = 0

    def render(self):
        if self.state == "PLAYING_VIDEO": return
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        if self.state == "MENU":
            draw.text((80, 20), "PI MEDIA CENTER", fill=ACCENT_COLOR, font=font_lg)
            items = [("Music", "♫"), ("Video", "►"), ("Photo", "🖼"), ("BT", "ᛒ")]
            for i, (label, icon) in enumerate(items):
                x, y = (25 + (i%3)*100), (60 + (i//3)*85)
                draw.rounded_rectangle((x, y, x+80, y+65), radius=8, fill="#313244", outline=ACCENT_COLOR)
                draw.text((x+30, y+10), icon, fill="white", font=font_lg)
                draw.text((x+20, y+40), label, fill="white", font=font_sm)
        else:
            self.draw_list(draw, self.state)
            
        device.display(img)

    def run(self):
        self.set_system_volume(self.volume)
        self.render()
        while self.running:
            pt = touch.get_touch()
            if pt: self.handle_touch(*pt)
            time.sleep(0.05)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: (emergency_cleanup(), sys.exit(0)))
    app = PiMediaCenter(); app.run()
