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
SERIAL_SPEED = 40000000 

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
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=SERIAL_SPEED)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    device.backlight(True)
    device.command(0x20) # Tắt Inversion để màu ảnh chuẩn
    
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26, 
                    width=WIDTH, height=HEIGHT, x_min=100, x_max=1962, y_min=100, y_max=1900)
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
        self.volume = 70 
        self.book_pages = []; self.current_page = 0
        self.last_touch = 0

    def set_vol(self, delta):
        self.volume = max(0, min(100, self.volume + delta))
        os.system(f"amixer set Master {self.volume}% > /dev/null 2>&1")
        pygame.mixer.music.set_volume(self.volume / 100.0)

    # --- TÍNH NĂNG XEM ẢNH (FIXED) ---
    def show_photo(self, path):
        try:
            img = Image.open(path)
            # Tự động xoay ảnh dựa trên EXIF
            img = ImageOps.exif_transpose(img)
            # Resize khớp màn hình nhưng giữ tỉ lệ
            img.thumbnail((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            # Tạo nền đen và dán ảnh vào giữa
            final_img = Image.new("RGB", (WIDTH, HEIGHT), "black")
            final_img.paste(img, ((WIDTH - img.size[0]) // 2, (HEIGHT - img.size[1]) // 2))
            device.display(final_img)
            
            # Chờ chạm để thoát
            while not touch.is_touched(): time.sleep(0.1)
            time.sleep(0.3)
        except Exception as e:
            print(f"Photo Error: {e}")
        self.render()

    # --- TÍNH NĂNG ĐỌC SÁCH (FIXED) ---
    def open_book(self, path):
        self.book_pages = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                # Chia văn bản thành các trang (khoảng 500 ký tự mỗi trang)
                lines = text.splitlines()
                for i in range(0, len(lines), 10): # 10 dòng mỗi trang
                    self.book_pages.append("\n".join(lines[i:i+10]))
            self.current_page = 0
            self.state = "READING"
        except: pass
        self.render()

    def draw_reader(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), "#fdf6e3") # Màu giấy cũ dễ đọc
        draw = ImageDraw.Draw(img)
        if self.book_pages:
            content = self.book_pages[self.current_page]
            draw.text((10, 10), content, fill="#586e75", font=font_md)
            draw.text((WIDTH//2 - 20, 220), f"{self.current_page+1}/{len(self.book_pages)}", fill="grey", font=font_sm)
        draw.rectangle((0, 210, 80, 240), fill="#eee8d5")
        draw.text((15, 215), "<< PREV", fill="black", font=font_sm)
        draw.rectangle((WIDTH-80, 210, WIDTH, 240), fill="#eee8d5")
        draw.text((WIDTH-65, 215), "NEXT >>", fill="black", font=font_sm)
        draw.text((WIDTH-40, 5), "EXIT", fill="red", font=font_sm)
        device.display(img)

    # --- TÍNH NĂNG BLUETOOTH (FIXED) ---
    def scan_bluetooth(self):
        self.files = [{"name": "Đang tìm thiết bị...", "mac": ""}]
        self.render()
        try:
            os.system("rfkill unblock bluetooth")
            # Quét thiết bị bằng bluetoothctl để lấy tên chính xác
            proc = subprocess.Popen(['bluetoothctl', '--timeout', '5', 'scan', 'on'], stdout=subprocess.PIPE)
            time.sleep(5)
            proc.terminate()
            out = subprocess.check_output(['bluetoothctl', 'devices']).decode()
            self.files = []
            for line in out.splitlines():
                if "Device" in line:
                    parts = line.split(' ', 2)
                    self.files.append({"mac": parts[1], "name": parts[2]})
        except: 
            self.files = [{"name": "Không tìm thấy thiết bị", "mac": ""}]
        self.render()

    # --- GIAO DIỆN DANH SÁCH ---
    def draw_list(self, draw, title):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        draw.text((10, 5), f"{title} | Vol: {self.volume}%", fill="white", font=font_sm)
        draw.rectangle((WIDTH-50, 2, WIDTH-5, 22), fill="#f38ba8")
        draw.text((WIDTH-45, 5), "BACK", fill="white", font=font_sm)

        items = self.files[self.scroll_offset:self.scroll_offset+6]
        for i, item in enumerate(items):
            idx = self.scroll_offset + i
            color = "#585b70" if idx == self.selected_idx else BG_COLOR
            draw.rectangle((5, 30+i*28, WIDTH-5, 55+i*28), fill=color)
            name = item['name'] if isinstance(item, dict) else item
            draw.text((15, 35+i*28), f"{name[:28]}", fill="white", font=font_md)

        # Thanh điều khiển
        btns = [("V-", 0), ("UP", 60), ("OK", 120), ("DN", 210), ("V+", 270)]
        for txt, x in btns:
            draw.text((x+10, 215), txt, fill=ACCENT_COLOR if txt!="OK" else "#a6e3a1", font=font_md)

    def play_video(self, path):
        self.state = "PLAYING_VIDEO"
        emergency_cleanup()
        audio_proc = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-volume', str(self.volume), path])
        video_cmd = ['ffmpeg', '-re', '-i', path, '-vf', f'scale={WIDTH}:{HEIGHT},format=rgb24', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        video_proc = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3)
        try:
            while True:
                raw = video_proc.stdout.read(WIDTH * HEIGHT * 3)
                if not raw or audio_proc.poll() is not None: break
                device.display(Image.frombytes('RGB', (WIDTH, HEIGHT), raw))
                if touch.is_touched(): break
        finally:
            audio_proc.terminate(); video_proc.terminate(); emergency_cleanup()
            self.state = "VIDEO"; self.render()

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "READING":
            if x > WIDTH - 50 and y < 40: self.state = "BOOK"; self.render()
            elif x < 100 and y > 200: self.current_page = max(0, self.current_page - 1); self.draw_reader()
            elif x > 220 and y > 200: self.current_page = min(len(self.book_pages)-1, self.current_page + 1); self.draw_reader()
            return

        if self.state == "MENU":
            if 60 < y < 130:
                if 15 < x < 105: self.state = "MUSIC"; self.load_files("MUSIC", ('.mp3', '.wav'))
                elif 120 < x < 210: self.state = "VIDEO"; self.load_files("VIDEO", ('.mp4', '.avi'))
                elif 225 < x < 315: self.state = "PHOTO"; self.load_files("PHOTO", ('.jpg', '.png'))
            elif 145 < y < 215:
                if 15 < x < 105: self.state = "BOOK"; self.load_files("BOOK", ('.txt',))
                elif 120 < x < 210: self.state = "BT"; self.scan_bluetooth()
        
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            if y < 30 and x > WIDTH-60: self.state = "MENU"
            elif y > 200:
                if x < 50: self.set_vol(-10)
                elif 50 < x < 110: 
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset: self.scroll_offset = self.selected_idx
                elif 260 < x: self.set_vol(10)
                elif 200 < x < 260:
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 6: self.scroll_offset += 1
                elif 120 < x < 190:
                    if not self.files: return
                    item = self.files[self.selected_idx]
                    path = os.path.join(DIRS.get(self.state, ""), item if self.state != "BT" else "")
                    if self.state == "VIDEO": self.play_video(path)
                    elif self.state == "PHOTO": self.show_photo(path)
                    elif self.state == "BOOK": self.open_book(path)
                    elif self.state == "MUSIC": pygame.mixer.music.load(path); pygame.mixer.music.play()
                    elif self.state == "BT": os.system(f"bluetoothctl connect {item['mac']}")
        self.render()

    def load_files(self, key, exts):
        try: self.files = [f for f in os.listdir(DIRS[key]) if f.lower().endswith(exts)]
        except: self.files = []
        self.selected_idx = 0; self.scroll_offset = 0

    def render(self):
        if self.state == "READING": self.draw_reader(); return
        if self.state == "PLAYING_VIDEO": return
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        if self.state == "MENU":
            draw.text((80, 20), "PI MEDIA CENTER", fill=ACCENT_COLOR, font=font_lg)
            menu = [("Music", "♫"), ("Video", "►"), ("Photo", "🖼"), ("Book", "bd"), ("BT", "ᛒ")]
            for i, (label, icon) in enumerate(menu):
                x, y = (20 + (i%3)*100), (60 + (i//3)*85)
                draw.rounded_rectangle((x, y, x+85, y+70), radius=8, fill="#313244", outline=ACCENT_COLOR)
                draw.text((x+30, y+10), icon, fill="white", font=font_lg)
                draw.text((x+25, y+45), label, fill="white", font=font_sm)
        else: self.draw_list(draw, self.state)
        device.display(img)

    def run(self):
        self.set_vol(0); self.render()
        while self.running:
            pt = touch.get_touch()
            if pt: self.handle_touch(*pt)
            time.sleep(0.05)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: (emergency_cleanup(), sys.exit(0)))
    app = PiMediaCenter(); app.run()
