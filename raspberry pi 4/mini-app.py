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
import math
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
TEXT_COLOR = "#cdd6f4"
WARN_COLOR = "#f38ba8"

USER_HOME = "/home/dinhphuc"
DIRS = {
    "MUSIC": os.path.join(USER_HOME, "Music"),
    "VIDEO": os.path.join(USER_HOME, "Videos"),
    "PHOTO": os.path.join(USER_HOME, "Pictures"),
    "BOOK":  os.path.join(USER_HOME, "Documents")
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

font_icon = load_font(24)
font_lg = load_font(18)
font_md = load_font(14)
font_sm = load_font(10)

def emergency_cleanup():
    """Dọn dẹp các tiến trình chạy ngầm"""
    subprocess.run(["pkill", "-9", "ffplay"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "ffmpeg"], stderr=subprocess.DEVNULL)
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ
# ==========================================
try:
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0)
    device.backlight(True)

    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900, 
                    baudrate=2000000)
except Exception as e:
    print(f"Hardware Error: {e}")
    sys.exit(1)

pygame.mixer.init()

# ==========================================
# 3. CLASS CHÍNH: PI MEDIA CENTER
# ==========================================

class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.running = True
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.last_touch = 0
        self.volume = 0.5
        self.bt_devices = []
        self.book_content = []
        self.book_page = 0
        self.video_stop_event = threading.Event()

    # --- UI DRAWING ---
    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 45, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=5, fill=bg_color)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((x + (w-tw)/2, y + (h-th)/2 - 2), text, fill=text_color, font=font_md)

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        draw.text((WIDTH//2 - 60, 35), "PI MEDIA HOME", fill=ACCENT_COLOR, font=font_lg)
        items = [
            ("Music", "♫", "#f9e2af"), ("Video", "►", "#f38ba8"),
            ("Photo", "🖼", "#a6e3a1"), ("Books", "📖", "#89b4fa"),
            ("BT", "ᛒ", "#cba6f7")
        ]
        start_y, btn_w, btn_h, gap = 70, 90, 70, 15
        start_x = (WIDTH - (btn_w * 3 + gap * 2)) / 2
        for i, (label, icon, color) in enumerate(items):
            row, col = i // 3, i % 3
            x, y = start_x + col*(btn_w+gap), start_y + row*(btn_h+gap)
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=8, fill="#313244", outline=color, width=2)
            draw.text((x + 30, y + 10), icon, fill=color, font=font_icon)
            draw.text((x + (btn_w - font_sm.getlength(label))/2, y + 45), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR)
        
        list_y, item_h, max_items = 55, 28, 5
        display_list = self.files[self.scroll_offset : self.scroll_offset + max_items]
        
        if not self.files:
            draw.text((WIDTH//2 - 40, 100), "Empty Folder", fill="grey", font=font_md)
        else:
            for i, item in enumerate(display_list):
                idx = self.scroll_offset + i
                is_sel = (idx == self.selected_idx)
                bg = "#585b70" if is_sel else BG_COLOR
                name = item['name'] if isinstance(item, dict) else item
                draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=bg)
                draw.text((15, list_y + i*item_h + 5), f"{'>' if is_sel else ' '} {name[:28]}", fill="cyan" if is_sel else "white", font=font_md)

        self.draw_button(draw, 10, 205, 90, 30, "UP")
        self.draw_button(draw, 115, 205, 90, 30, "SELECT", bg_color="#a6e3a1", text_color="black")
        self.draw_button(draw, 220, 205, 90, 30, "DOWN")

    def draw_player_ui(self, draw):
        self.draw_status_bar(draw)
        song_name = self.files[self.selected_idx] if self.files else "No Media"
        draw.text((20, 60), song_name[:25], fill="yellow", font=font_lg)
        # Progress bar
        draw.rectangle((40, 120, 280, 130), fill="#45475a")
        progress = (math.sin(time.time() * 2) + 1) / 2
        draw.rectangle((40, 120, 40 + 240*progress, 130), fill=ACCENT_COLOR)
        self.draw_button(draw, 10, 180, 90, 40, "VOL-")
        self.draw_button(draw, 115, 180, 90, 40, "PAUSE")
        self.draw_button(draw, 220, 180, 90, 40, "EXIT")

    def draw_reader(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#f5e0dc") # Màu giấy cũ
        if self.book_content:
            lines = self.book_content[self.book_page]
            for i, line in enumerate(lines):
                draw.text((10, 10 + i*22), line.strip(), fill="black", font=font_md)
        self.draw_button(draw, 5, 205, 80, 30, "PREV")
        self.draw_button(draw, WIDTH-85, 205, 80, 30, "NEXT")
        self.draw_button(draw, WIDTH//2-40, 205, 80, 30, "CLOSE", bg_color=WARN_COLOR)

    # --- LOGIC ---
    def load_files(self, key, ext):
        try:
            self.files = sorted([f for f in os.listdir(DIRS[key]) if f.lower().endswith(ext)])
        except: self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0

    def play_video_stream(self, filepath):
        self.state = "PLAYING_VIDEO"
        emergency_cleanup()
        # Audio
        audio_proc = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-volume', str(int(self.volume*100)), filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Video
        video_cmd = ['ffmpeg', '-re', '-i', filepath, '-vf', f'scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        video_proc = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3)
        
        try:
            while not self.video_stop_event.is_set():
                raw = video_proc.stdout.read(WIDTH * HEIGHT * 3)
                if not raw or touch.is_touched(): break
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw)
                device.display(img)
                if audio_proc.poll() is not None: break
        finally:
            audio_proc.terminate()
            video_proc.terminate()
            emergency_cleanup()
            self.state = "VIDEO"
            self.render()

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "MENU":
            if 70 <= y <= 210:
                col = (x - 25) // 105
                row = (y - 70) // 85
                idx = row * 3 + col
                if idx == 0: self.state = "MUSIC"; self.load_files("MUSIC", ('.mp3', '.wav'))
                elif idx == 1: self.state = "VIDEO"; self.load_files("VIDEO", ('.mp4', '.mkv'))
                elif idx == 2: self.state = "PHOTO"; self.load_files("PHOTO", ('.jpg', '.png'))
                elif idx == 3: self.state = "BOOK"; self.load_files("BOOK", ('.txt'))
                elif idx == 4: threading.Thread(target=self.scan_bt).start()

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]:
            if x > WIDTH-60 and y < 50: self.state = "MENU"
            elif y > 200:
                if x < 100: 
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset: self.scroll_offset -= 1
                elif x > 220:
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5: self.scroll_offset += 1
                elif 115 < x < 205 and self.files:
                    item = self.files[self.selected_idx]
                    path = os.path.join(DIRS[self.state], item)
                    if self.state == "MUSIC":
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.play()
                        self.state = "PLAYING_MUSIC"
                    elif self.state == "VIDEO":
                        threading.Thread(target=self.play_video_stream, args=(path,), daemon=True).start()
                    elif self.state == "PHOTO":
                        self.show_photo(path)
                    elif self.state == "BOOK":
                        self.load_book(path)
                        self.state = "READING"
        
        elif self.state == "PLAYING_MUSIC":
            if y > 170:
                if x < 100: self.volume = max(0, self.volume-0.1); pygame.mixer.music.set_volume(self.volume)
                elif x > 220: self.state = "MUSIC"; pygame.mixer.music.stop()
                else: 
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.pause()
                    else: pygame.mixer.music.unpause()

        elif self.state == "READING":
            if y > 200:
                if x < 100: self.book_page = max(0, self.book_page - 1)
                elif x > 220: self.book_page = min(len(self.book_content)-1, self.book_page + 1)
                else: self.state = "BOOK"
        
        self.render()

    def load_book(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                self.book_content = [lines[i:i+8] for i in range(0, len(lines), 8)]
            self.book_page = 0
        except: self.book_content = []

    def show_photo(self, path):
        img = Image.open(path)
        img = ImageOps.fit(img, (WIDTH, HEIGHT))
        device.display(img)
        while not touch.is_touched(): time.sleep(0.1)
        self.render()

    def scan_bt(self):
        # Hàm quét bluetooth cơ bản
        self.files = [{"name": "Scanning..."}]
        self.render()
        time.sleep(2)
        self.files = [{"name": "No Device Found"}]
        self.state = "MENU"
        self.render()

    def render(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        if self.state == "MENU": self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]: self.draw_list(draw, self.state)
        elif self.state == "PLAYING_MUSIC": self.draw_player_ui(draw)
        elif self.state == "READING": self.draw_reader(draw)
        
        if self.state != "PLAYING_VIDEO":
            device.display(img)

    def run(self):
        self.render()
        while self.running:
            p = touch.get_touch()
            if p: self.handle_touch(p[0], p[1])
            if self.state == "PLAYING_MUSIC": self.render(); time.sleep(0.5) # Update progress bar
            time.sleep(0.05)

if __name__ == "__main__":
    def shut(s, f):
        emergency_cleanup()
        sys.exit(0)
    signal.signal(signal.SIGINT, shut)
    PiMediaCenter().run()
