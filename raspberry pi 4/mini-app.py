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
BG_COLOR = "#1e1e2e"       # Màu nền tối (Catppuccin theme)
ACCENT_COLOR = "#89b4fa"   # Màu xanh điểm nhấn
TEXT_COLOR = "#cdd6f4"
WARN_COLOR = "#f38ba8"
SERIAL_SPEED = 40000000    # Tốc độ SPI cho video mượt mà

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

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ (LCD & TOUCH)
# ==========================================

def emergency_cleanup():
    """Dọn dẹp triệt để các tiến trình để tránh treo máy"""
    os.system("pkill -9 ffplay")
    os.system("pkill -9 ffmpeg")
    pygame.mixer.music.stop()

try:
    # Cấu hình LCD ST7789
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=SERIAL_SPEED)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    device.backlight(True)

    # Cấu hình Cảm ứng XPT2046
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900, 
                    baudrate=2000000)
except Exception as e:
    print(f"Lỗi phần cứng: {e}")
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
        self.book_content = []
        self.book_page = 0
        self.video_stop_event = threading.Event()

    # --- GIAO DIỆN (UI) ---
    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 40, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=5, fill=bg_color)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        draw.text((x + (w - (bbox[2]-bbox[0]))/2, y + (h - (bbox[3]-bbox[1]))/2 - 2), 
                  text, fill=text_color, font=font_md)

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        draw.text((80, 35), "PI MEDIA HOME", fill=ACCENT_COLOR, font=font_lg)
        items = [("Music", "♫", "#f9e2af"), ("Video", "►", "#f38ba8"),
                 ("Photo", "🖼", "#a6e3a1"), ("Books", "bd", "#89b4fa"),
                 ("BT", "ᛒ", "#cba6f7")]
        start_y, btn_w, btn_h, gap = 70, 90, 70, 20
        start_x = (WIDTH - (btn_w * 3 + gap * 2)) / 2
        for i, (label, icon, color) in enumerate(items):
            row, col = i // 3, i % 3
            x, y = start_x + col*(btn_w+gap), start_y + row*(btn_h+gap)
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=8, fill="#313244", outline=color, width=2)
            draw.text((x + 35, y + 10), icon, fill=color, font=font_icon)
            draw.text((x + (btn_w - font_sm.getlength(label))/2, y + 45), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR)
        list_y, item_h, max_items = 55, 30, 5
        display_list = self.files[self.scroll_offset : self.scroll_offset + max_items]
        if not self.files:
            draw.text((100, 100), "Trống / Empty", fill="grey", font=font_md)
        for i, item in enumerate(display_list):
            idx = self.scroll_offset + i
            is_sel = (idx == self.selected_idx)
            draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill="#585b70" if is_sel else BG_COLOR)
            name = item['name'] if isinstance(item, dict) else item
            draw.text((10, list_y + i*item_h + 5), f"{'>' if is_sel else ' '} {name[:25]}", fill="cyan" if is_sel else "white", font=font_md)
        self.draw_button(draw, 10, 205, 90, 30, "▲ UP")
        self.draw_button(draw, 115, 205, 90, 30, "OK ●", bg_color="#a6e3a1", text_color="black")
        self.draw_button(draw, 220, 205, 90, 30, "▼ DOWN")

    def draw_reader(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="black")
        if self.book_content:
            lines = self.book_content[self.book_page]
            for i, line in enumerate(lines):
                draw.text((10, 10 + i*22), line.strip(), fill="white", font=font_md)
        self.draw_button(draw, 5, 205, 80, 30, "<< PREV")
        self.draw_button(draw, 235, 205, 80, 30, "NEXT >>")
        self.draw_button(draw, WIDTH-60, 5, 50, 25, "EXIT", bg_color=WARN_COLOR)

    # --- LOGIC XỬ LÝ ---
    def load_files(self, type_key, ext):
        if os.path.exists(DIRS[type_key]):
            self.files = sorted([f for f in os.listdir(DIRS[type_key]) if f.lower().endswith(ext)])
        self.selected_idx, self.scroll_offset = 0, 0

    def play_video_stream(self, filepath):
        """Phát video mượt mà kèm âm thanh"""
        self.state = "PLAYING_VIDEO"
        emergency_cleanup()
        self.video_stop_event.clear()

        # Phát âm thanh qua ffplay
        audio_proc = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', filepath],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Phát hình ảnh qua ffmpeg
        video_cmd = ['ffmpeg', '-re', '-i', filepath, 
                     '-vf', f'scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black',
                     '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        video_proc = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3)

        try:
            while not self.video_stop_event.is_set():
                if touch.is_touched() or audio_proc.poll() is not None: break
                raw = video_proc.stdout.read(WIDTH * HEIGHT * 3)
                if len(raw) != WIDTH * HEIGHT * 3: break
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw)
                img = ImageOps.invert(img) # Đảo ngược màu cho ST7789
                device.display(img)
                time.sleep(0.001)
        finally:
            audio_proc.terminate()
            video_proc.terminate()
            emergency_cleanup()
            self.state = "VIDEO"
            self.render()

    def show_photo(self, filepath):
        self.state = "VIEWING_PHOTO"
        try:
            img = Image.open(filepath)
            img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            img = ImageOps.invert(img)
            device.display(img)
            while not touch.is_touched(): time.sleep(0.1)
            time.sleep(0.2)
        except: pass
        self.state = "PHOTO"
        self.render()

    def paginate_book(self, filename):
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_content = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for i in range(0, len(lines), 8):
                    self.book_content.append(lines[i:i+8])
        except: pass
        self.book_page = 0

    def render(self):
        if self.state in ["PLAYING_VIDEO", "VIEWING_PHOTO"]: return
        image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(image)
        if self.state == "MENU": self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]:
            titles = {"MUSIC": "Âm nhạc", "VIDEO": "Video", "PHOTO": "Hình ảnh", "BOOK": "Sách điện tử"}
            self.draw_list(draw, titles.get(self.state, ""))
        elif self.state == "READING": self.draw_reader(draw)
        elif self.state == "PLAYING_MUSIC": 
            self.draw_status_bar(draw)
            draw.text((20, 100), "Đang phát nhạc...", fill="yellow", font=font_lg)
            self.draw_button(draw, 110, 180, 100, 40, "STOP", bg_color=WARN_COLOR)
        device.display(image)

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "MENU":
            start_y, btn_w, btn_h, gap = 70, 90, 70, 20
            start_x = (WIDTH - (btn_w * 3 + gap * 2)) / 2
            col = int((x - start_x) // (btn_w + gap))
            row = int((y - start_y) // (btn_h + gap))
            if 0 <= col < 3 and 0 <= row < 2:
                idx = row * 3 + col
                mapping = [("MUSIC", ('.mp3', '.wav')), ("VIDEO", ('.mp4',)), 
                           ("PHOTO", ('.jpg', '.png')), ("BOOK", ('.txt',))]
                if idx < len(mapping):
                    self.state, ext = mapping[idx]
                    self.load_files(self.state, ext)
            self.render()

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]:
            if x > WIDTH - 70 and y < 50: self.state = "MENU"
            elif y > 200:
                if x < 100: self.selected_idx = max(0, self.selected_idx - 1)
                elif x > 220: self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                else: # OK
                    if not self.files: return
                    item = self.files[self.selected_idx]
                    path = os.path.join(DIRS[self.state], item)
                    if self.state == "MUSIC":
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.play()
                        self.state = "PLAYING_MUSIC"
                    elif self.state == "VIDEO":
                        threading.Thread(target=self.play_video_stream, args=(path,)).start()
                        return
                    elif self.state == "PHOTO": self.show_photo(path)
                    elif self.state == "BOOK":
                        self.paginate_book(item)
                        self.state = "READING"
            self.render()

        elif self.state == "READING":
            if x > WIDTH - 60 and y < 40: self.state = "BOOK"
            elif y > 200:
                if x < 100: self.book_page = max(0, self.book_page - 1)
                elif x > 220: self.book_page = min(len(self.book_content)-1, self.book_page + 1)
            self.render()

        elif self.state == "PLAYING_MUSIC":
            if 110 < x < 210 and 180 < y < 220:
                pygame.mixer.music.stop()
                self.state = "MUSIC"
            self.render()

    def run(self):
        self.render()
        while self.running:
            pt = touch.get_touch()
            if pt: self.handle_touch(*pt)
            time.sleep(0.05)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: (emergency_cleanup(), sys.exit(0)))
    app = PiMediaCenter()
    app.run()
