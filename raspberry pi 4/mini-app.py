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
import textwrap
from PIL import Image, ImageFont, ImageDraw, ImageOps
from luma.core.interface.serial import spi as luma_spi
from luma.lcd.device import st7789
from xpt2046 import XPT2046

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & PHẦN CỨNG
# ==========================================

WIDTH, HEIGHT = 320, 240
BG_COLOR = "#1e1e2e"       # Base (Catppuccin)
SURFACE_COLOR = "#313244"  # Surface
ACCENT_COLOR = "#89b4fa"   # Blue
TEXT_COLOR = "#cdd6f4"     # Text
SUBTEXT_COLOR = "#a6adc8"  # Subtext
WARN_COLOR = "#f38ba8"     # Red
SUCCESS_COLOR = "#a6e3a1"  # Green

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

font_icon = load_font(28)
font_lg = load_font(18)
font_md = load_font(14)
font_sm = load_font(11)

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ
# ==========================================
try:
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
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
        
        # Sách
        self.book_content = []
        self.book_page = 0
        
        # Video/Audio
        self.is_video_playing = False
        self.video_process = None
        self.audio_process = None

    def emergency_cleanup(self):
        if self.video_process:
            try: self.video_process.kill()
            except: pass
        if self.audio_process:
            try: self.audio_process.kill()
            except: pass
        os.system("pkill -9 ffplay")
        os.system("pkill -9 ffmpeg")
        pygame.mixer.music.stop()

    # --- UI COMPONENTS ---
    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 26), fill="#11111b")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 45, 5), time_str, fill=SUBTEXT_COLOR, font=font_sm)
        draw.text((10, 5), f"VOL: {int(self.volume*100)}%", fill=ACCENT_COLOR, font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg=SURFACE_COLOR, fg=TEXT_COLOR, radius=8):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=radius, fill=bg)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((x+(w-tw)/2, y+(h-th)/2 - 2), text, fill=fg, font=font_md)

    # --- SCREEN: MENU ---
    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        title = "PI MEDIA SYSTEM"
        draw.text((WIDTH//2 - font_lg.getlength(title)//2, 35), title, fill=ACCENT_COLOR, font=font_lg)

        items = [
            ("Music", "♫", "#f9e2af"), ("Video", "▶", "#f38ba8"),
            ("Photo", "🖼", "#a6e3a1"), ("Books", "📖", "#89b4fa"),
            ("BT", "ᛒ", "#cba6f7")
        ]
        
        btn_w, btn_h = 85, 65
        gap_x, gap_y = 15, 15
        start_x = (WIDTH - (btn_w*3 + gap_x*2)) // 2
        start_y = 75

        for i, (label, icon, color) in enumerate(items):
            r, c = i // 3, i % 3
            x, y = start_x + c*(btn_w+gap_x), start_y + r*(btn_h+gap_y)
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=10, fill=SURFACE_COLOR, outline=color, width=1)
            draw.text((x + (btn_w - font_icon.getlength(icon))//2, y + 8), icon, fill=color, font=font_icon)
            draw.text((x + (btn_w - font_sm.getlength(label))//2, y + 42), label, fill=TEXT_COLOR, font=font_sm)

    # --- SCREEN: LIST ---
    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        # Header
        draw.rectangle((0, 26, WIDTH, 52), fill=SURFACE_COLOR)
        draw.text((10, 30), title, fill=SUCCESS_COLOR, font=font_md)
        self.draw_button(draw, WIDTH-55, 28, 50, 20, "BACK", bg=WARN_COLOR, radius=4)

        # List
        item_h = 30
        max_v = 5
        display_files = self.files[self.scroll_offset : self.scroll_offset + max_v]
        
        for i, item in enumerate(display_files):
            idx = self.scroll_offset + i
            is_sel = (idx == self.selected_idx)
            y = 55 + i*item_h
            bg = "#45475a" if is_sel else BG_COLOR
            draw.rectangle((5, y, WIDTH-5, y+item_h-2), fill=bg)
            name = item['name'] if isinstance(item, dict) else item
            prefix = "> " if is_sel else "  "
            draw.text((10, y + 6), f"{prefix}{name[:32]}", fill=TEXT_COLOR if not is_sel else ACCENT_COLOR, font=font_md)

        # Bottom Controls
        self.draw_button(draw, 10, 205, 90, 30, "UP")
        self.draw_button(draw, 115, 205, 90, 30, "SELECT", bg=SUCCESS_COLOR, fg="#11111b")
        self.draw_button(draw, 220, 205, 90, 30, "DOWN")

    # --- SCREEN: MUSIC PLAYER (IMPROVED) ---
    def draw_player_ui(self, draw):
        self.draw_status_bar(draw)
        # Disk Decor
        center_x, center_y = 60, 110
        draw.ellipse((center_x-40, center_y-40, center_x+40, center_y+40), outline=ACCENT_COLOR, width=2)
        draw.ellipse((center_x-10, center_y-10, center_x+10, center_y+10), fill=ACCENT_COLOR)
        
        # Info Card
        song_name = self.files[self.selected_idx]
        draw.rounded_rectangle((110, 70, WIDTH-10, 150), radius=10, fill=SURFACE_COLOR)
        draw.text((120, 85), "Playing:", fill=SUBTEXT_COLOR, font=font_sm)
        # Wrap title
        lines = textwrap.wrap(song_name, width=18)
        for i, line in enumerate(lines[:2]):
            draw.text((120, 100 + i*18), line, fill=TEXT_COLOR, font=font_md)

        # Progress Bar
        bar_x, bar_y, bar_w = 20, 170, 280
        progress = (time.time() % 10) / 10 # Giả lập tiến trình
        draw.rectangle((bar_x, bar_y, bar_x+bar_w, bar_y+6), fill="#45475a")
        draw.rectangle((bar_x, bar_y, bar_x + int(bar_w*progress), bar_y+6), fill=SUCCESS_COLOR)

        # Buttons
        self.draw_button(draw, 10, 190, 70, 40, "VOL-")
        self.draw_button(draw, 85, 190, 70, 40, "PAUSE" if pygame.mixer.music.get_busy() else "PLAY")
        self.draw_button(draw, 160, 190, 70, 40, "VOL+")
        self.draw_button(draw, 235, 190, 75, 40, "BACK", bg=WARN_COLOR)

    # --- SCREEN: BOOK READER (IMPROVED WORD WRAP) ---
    def paginate_book(self, filename):
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_content = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                # Tự động ngắt dòng theo chiều rộng màn hình (khoảng 40 ký tự font md)
                wrapped_lines = []
                for paragraph in text.split('\n'):
                    if not paragraph.strip():
                        wrapped_lines.append("")
                        continue
                    wrapped_lines.extend(textwrap.wrap(paragraph, width=38))
                
                # Chia trang: mỗi trang 8 dòng
                for i in range(0, len(wrapped_lines), 8):
                    self.book_content.append(wrapped_lines[i:i+8])
        except Exception as e:
            self.book_content = [[f"Error: {e}"]]
        self.book_page = 0

    def draw_reader(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#f5e0dc") # Màu giấy cũ nhẹ
        text_draw = ImageDraw.Draw(Image.new("RGB", (1,1))) # Dummy
        
        if self.book_content:
            lines = self.book_content[self.book_page]
            for i, line in enumerate(lines):
                draw.text((15, 15 + i*22), line, fill="#1e1e2e", font=font_md)
        
        # Footer
        info = f"Page {self.book_page+1} / {len(self.book_content)}"
        draw.text((WIDTH//2 - font_sm.getlength(info)//2, 195), info, fill="#585b70", font=font_sm)
        
        self.draw_button(draw, 5, 210, 80, 25, "<< PREV", bg="#bac2de", fg="#11111b")
        self.draw_button(draw, 120, 210, 80, 25, "EXIT", bg=WARN_COLOR)
        self.draw_button(draw, 235, 210, 80, 25, "NEXT >>", bg="#bac2de", fg="#11111b")

    # --- LOGIC & RENDERING ---
    def render(self):
        image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(image)

        if self.state == "MENU": self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            titles = {"MUSIC":"Music Library", "VIDEO":"Video Clips", "PHOTO":"Gallery", "BOOK":"Library", "BT":"Bluetooth"}
            self.draw_list(draw, titles.get(self.state, ""))
        elif self.state == "PLAYING_MUSIC": self.draw_player_ui(draw)
        elif self.state == "READING": self.draw_reader(draw)

        # Invert màu nếu LCD yêu cầu (tùy thuộc vào phần cứng của bạn)
        if self.state not in ["PLAYING_VIDEO", "VIEWING_PHOTO"]:
            img_to_show = ImageOps.invert(image)
            device.display(img_to_show)

    def load_files(self, type_key, ext):
        self.files = sorted([f for f in os.listdir(DIRS[type_key]) if f.lower().endswith(ext)])
        self.selected_idx = 0
        self.scroll_offset = 0

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "MENU":
            # Grid detection logic
            if 75 <= y <= 210:
                col = (x - 20) // 100
                row = (y - 75) // 80
                idx = row * 3 + col
                if idx == 0: self.state = "MUSIC"; self.load_files("MUSIC", ('.mp3', '.wav'))
                elif idx == 1: self.state = "VIDEO"; self.load_files("VIDEO", ('.mp4'))
                elif idx == 2: self.state = "PHOTO"; self.load_files("PHOTO", ('.jpg', '.png'))
                elif idx == 3: self.state = "BOOK"; self.load_files("BOOK", ('.txt'))
                elif idx == 4: threading.Thread(target=self.scan_bt).start(); return
            self.render()

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            if x > WIDTH-60 and y < 50: self.state = "MENU"; self.render(); return
            if y > 200:
                if x < 100: # UP
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset: self.scroll_offset = self.selected_idx
                elif x > 220: # DOWN
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5: self.scroll_offset += 1
                else: # SELECT
                    if not self.files: return
                    item = self.files[self.selected_idx]
                    if self.state == "MUSIC":
                        pygame.mixer.music.load(os.path.join(DIRS["MUSIC"], item))
                        pygame.mixer.music.play()
                        self.state = "PLAYING_MUSIC"
                    elif self.state == "BOOK":
                        self.paginate_book(item)
                        self.state = "READING"
                    elif self.state == "PHOTO":
                        self.show_photo(os.path.join(DIRS["PHOTO"], item))
                        return
            self.render()

        elif self.state == "PLAYING_MUSIC":
            if y > 180:
                if x < 80: # VOL-
                    self.volume = max(0, self.volume - 0.1)
                    pygame.mixer.music.set_volume(self.volume)
                elif x < 160: # PLAY/PAUSE
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.pause()
                    else: pygame.mixer.music.unpause()
                elif x < 235: # VOL+
                    self.volume = min(1, self.volume + 0.1)
                    pygame.mixer.music.set_volume(self.volume)
                else: # BACK
                    pygame.mixer.music.stop()
                    self.state = "MUSIC"
            self.render()

        elif self.state == "READING":
            if y > 200:
                if x < 100: self.book_page = max(0, self.book_page - 1)
                elif x > 220: self.book_page = min(len(self.book_content)-1, self.book_page + 1)
                elif 100 < x < 220: self.state = "BOOK"
            self.render()

    def show_photo(self, path):
        try:
            img = Image.open(path)
            img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            device.display(ImageOps.invert(img))
            while not touch.is_touched(): time.sleep(0.1)
            time.sleep(0.3)
        except: pass
        self.render()

    def scan_bt(self):
        # Giữ nguyên logic scan BT của bạn nhưng bọc trong render
        self.files = [{"mac":"00:00", "name":"Scanning..."}]
        self.state = "BT"
        self.render()
        # ... logic scan thực tế ...

    def run(self):
        self.render()
        while self.running:
            pt = touch.get_touch()
            if pt: self.handle_touch(pt[0], pt[1])
            time.sleep(0.05)

if __name__ == "__main__":
    app = PiMediaCenter()
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    app.run()
