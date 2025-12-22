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

# Cấu hình Màn hình
WIDTH, HEIGHT = 320, 240
BG_COLOR = "#1e1e2e"       # Màu nền tối (Dark theme)
ACCENT_COLOR = "#89b4fa"   # Màu điểm nhấn
TEXT_COLOR = "#cdd6f4"     # Màu chữ sáng
WARN_COLOR = "#f38ba8"     # Màu cảnh báo

# Đường dẫn thư mục (Tự động tạo nếu thiếu)
USER_HOME = "/home/dinhphuc"
DIRS = {
    "MUSIC": os.path.join(USER_HOME, "Music"),
    "VIDEO": os.path.join(USER_HOME, "Videos"),
    "PHOTO": os.path.join(USER_HOME, "Pictures"),
    "BOOK":  os.path.join(USER_HOME, "Documents")
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# Khởi tạo Fonts
def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

font_icon = load_font(24) # Giả lập icon bằng text to
font_lg = load_font(18)
font_md = load_font(14)
font_sm = load_font(10)

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ (LCD & TOUCH)
# ==========================================
try:
    # LCD ST7789
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    device.backlight(True)

    # Cảm ứng XPT2046
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900, 
                    baudrate=2000000)
except Exception as e:
    print(f"Hardware Error: {e}")
    sys.exit(1)

# Âm thanh
pygame.mixer.init()

# ==========================================
# 3. CLASS CHÍNH: MEDIA CENTER
# ==========================================

class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"  # MENU, MUSIC, VIDEO, PHOTO, BOOK, BT, READING, PLAYING_VIDEO, VIEWING_PHOTO
        self.running = True
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.last_touch = 0
        
        # Biến trạng thái chức năng
        self.bt_devices = []
        self.bt_scanning = False
        self.book_content = []
        self.book_page = 0
        self.volume = 0.5
        self.current_media_path = ""
        
        # Cờ điều khiển luồng
        self.video_stop_event = threading.Event()

    # --- HÀM VẼ GIAO DIỆN (UI) ---
    def draw_status_bar(self, draw):
        """Vẽ thanh trạng thái trên cùng"""
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 40, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)
        if self.bt_devices: # Icon giả lập BT
            draw.text((WIDTH - 70, 5), "BT", fill="#94e2d5", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white"):
        """Vẽ nút bấm bo tròn"""
        draw.rounded_rectangle((x, y, x+w, y+h), radius=5, fill=bg_color)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text((x + (w - text_w)/2, y + (h - text_h)/2 - 2), text, fill=text_color, font=font_md)

    def draw_menu(self, draw):
        """Vẽ Menu chính dạng lưới 2x2 hoặc 2x3"""
        self.draw_status_bar(draw)
        title = "PI MEDIA HOME"
        bbox = draw.textbbox((0,0), title, font=font_lg)
        draw.text(((WIDTH - (bbox[2]-bbox[0]))/2, 35), title, fill=ACCENT_COLOR, font=font_lg)

        # Danh sách mục menu: (Label, IconChar, Color)
        items = [
            ("Music", "♫", "#f9e2af"), ("Video", "►", "#f38ba8"),
            ("Photo", "🖼", "#a6e3a1"), ("Books", "bd", "#89b4fa"),
            ("BlueTooth", "ᛒ", "#cba6f7")
        ]
        
        # Vẽ lưới nút
        start_y = 70
        btn_w, btn_h = 90, 70
        gap = 20
        start_x = (WIDTH - (btn_w * 3 + gap * 2)) / 2

        for i, (label, icon, color) in enumerate(items):
            row = i // 3
            col = i % 3
            x = start_x + col * (btn_w + gap)
            y = start_y + row * (btn_h + gap)
            
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=8, fill="#313244", outline=color, width=2)
            # Vẽ icon (chữ to)
            draw.text((x + 35, y + 10), icon, fill=color, font=font_icon)
            # Vẽ nhãn
            draw.text((x + (btn_w - font_sm.getlength(label))/2, y + 45), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        """Vẽ danh sách file chung cho Music, Video, Photo, BT"""
        self.draw_status_bar(draw)
        # Header
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR)

        # List items
        list_y = 55
        item_h = 30
        max_items = 5
        
        # Tính toán view
        display_list = self.files[self.scroll_offset : self.scroll_offset + max_items]
        
        if not self.files:
            draw.text((WIDTH//2 - 40, 100), "Trống / Empty", fill="grey", font=font_md)
            return

        for i, item in enumerate(display_list):
            global_idx = self.scroll_offset + i
            is_sel = (global_idx == self.selected_idx)
            
            bg = "#585b70" if is_sel else BG_COLOR
            fg = "cyan" if is_sel else "white"
            
            name = item['name'] if isinstance(item, dict) else item
            
            draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=bg)
            draw.text((10, list_y + i*item_h + 5), f"{'>' if is_sel else ' '} {name[:30]}", fill=fg, font=font_md)

        # Thanh cuộn ảo
        if len(self.files) > max_items:
            sb_h = int((max_items / len(self.files)) * 140)
            sb_y = list_y + int((self.scroll_offset / len(self.files)) * 140)
            draw.rectangle((WIDTH-5, sb_y, WIDTH, sb_y+sb_h), fill="grey")

        # Nút điều hướng dưới cùng
        btn_y = 205
        self.draw_button(draw, 10, btn_y, 90, 30, "▲ LÊN")
        self.draw_button(draw, 115, btn_y, 90, 30, "CHỌN ●", bg_color="#a6e3a1", text_color="black")
        self.draw_button(draw, 220, btn_y, 90, 30, "▼ XUỐNG")

    def draw_player_ui(self, draw):
        """Giao diện phát nhạc đơn giản"""
        self.draw_status_bar(draw)
        draw.text((20, 40), "Now Playing:", fill="grey", font=font_sm)
        if self.files:
            song_name = self.files[self.selected_idx]
            # Wrap text nếu quá dài
            draw.text((20, 60), song_name[:25], fill="yellow", font=font_lg)
            draw.text((20, 85), song_name[25:50], fill="yellow", font=font_lg)
        
        # Visualizer giả
        draw.rectangle((40, 120, 280, 130), fill="#45475a") # Bar nền
        import math
        progress = (math.sin(time.time()) + 1) / 2 # Giả lập chạy
        draw.rectangle((40, 120, 40 + 240*progress, 130), fill=ACCENT_COLOR)

        self.draw_button(draw, 10, 180, 70, 40, "VOL-")
        self.draw_button(draw, 90, 180, 70, 40, "VOL+")
        self.draw_button(draw, 170, 180, 80, 40, "PAUSE/PLAY")
        self.draw_button(draw, 260, 180, 50, 40, "BACK")

    def draw_reader(self, draw):
        """Giao diện đọc sách"""
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="black")
        if not self.book_content:
            draw.text((10, 100), "Lỗi đọc file!", fill="red", font=font_md)
        else:
            lines = self.book_content[self.book_page]
            y = 10
            for line in lines:
                draw.text((10, y), line.rstrip(), fill="white", font=font_md)
                y += 22
        
        # Footer
        draw.line((0, 200, WIDTH, 200), fill="grey")
        draw.text((140, 210), f"{self.book_page+1}/{len(self.book_content)}", fill="cyan", font=font_sm)
        self.draw_button(draw, 5, 205, 70, 30, "<< PREV")
        self.draw_button(draw, 245, 205, 70, 30, "NEXT >>")

    def render(self):
        """Hàm render chính, điều phối vẽ dựa trên state"""
        image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(image)

        if self.state == "MENU":
            self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            title_map = {"MUSIC": "Music Library", "VIDEO": "Video Clip", "PHOTO": "Photo Gallery", "BOOK": "Book Library", "BT": "Bluetooth Devices"}
            self.draw_list(draw, title_map.get(self.state, ""))
        elif self.state == "PLAYING_MUSIC":
            self.draw_player_ui(draw)
        elif self.state == "READING":
            self.draw_reader(draw)
        elif self.state == "VIEWING_PHOTO":
            # Chế độ xem ảnh xử lý riêng ở logic hiển thị
            pass 

        if self.state != "PLAYING_VIDEO" and self.state != "VIEWING_PHOTO":
            device.display(image)

    # --- LOGIC XỬ LÝ (BACKEND) ---

    def load_files(self, type_key, ext):
        self.files = sorted([f for f in os.listdir(DIRS[type_key]) if f.lower().endswith(ext)])
        self.selected_idx = 0
        self.scroll_offset = 0

    def paginate_book(self, filename):
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_content = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Chia 8 dòng mỗi trang, giữ nguyên định dạng
                for i in range(0, len(lines), 8):
                    self.book_content.append(lines[i:i
