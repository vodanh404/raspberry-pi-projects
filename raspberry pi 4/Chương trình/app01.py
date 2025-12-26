import os
import sys
import time
import threading
import datetime
import textwrap
import math
import random
import requests
import psutil
import pygame
import board
import busio
from PIL import Image, ImageFont, ImageDraw, ImageOps
from luma.core.interface.serial import spi as luma_spi
from luma.lcd.device import st7789
from xpt2046 import XPT2046
from unidecode import unidecode
from googletrans import Translator

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & PHẦN CỨNG
# ==========================================
WIDTH, HEIGHT = 320, 240
APPS_PER_PAGE = 6

# Palette màu sắc hiện đại (Catppuccin Mocha)
BG_COLOR = "#1e1e2e"
CARD_COLOR = "#313244"
ACCENT_COLOR = "#89b4fa"
TEXT_COLOR = "#cdd6f4"
SUCCESS_COLOR = "#a6e3a1"
WARN_COLOR = "#f38ba8"

# Đường dẫn dữ liệu
USER_HOME = "/home/dinhphuc"
DIRS = {
    "MUSIC": os.path.join(USER_HOME, "Music"),
    "VIDEO": os.path.join(USER_HOME, "Videos"),
    "PHOTO": os.path.join(USER_HOME, "Pictures"),
    "BOOK":  os.path.join(USER_HOME, "Documents")
}
for d in DIRS.values(): os.makedirs(d, exist_ok=True)

# Khởi tạo phần cứng
try:
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0)
    
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26, 
                    width=WIDTH, height=HEIGHT, x_min=100, x_max=1900, y_min=100, y_max=1900)
except Exception as e:
    print(f"Lỗi phần cứng: {e}")
    sys.exit(1)

# Khởi tạo Font
def load_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except: return ImageFont.load_default()

font_sm = load_font(12)
font_md = load_font(16)
font_lg = load_font(22)
font_icon = load_font(32)

# ==========================================
# 2. LOGIC GAME BLOCK BLAST (TÍCH HỢP)
# ==========================================
class MiniGame:
    def __init__(self):
        self.grid = [[0]*8 for _ in range(8)]
        self.score = 0
        self.game_over = False

    def check_collision(self, x, y, shape):
        for r in range(len(shape)):
            for c in range(len(shape[0])):
                if shape[r][c] and (y+r >= 8 or x+c >= 8 or self.grid[y+r][x+c]): return False
        return True

    def place_shape(self, x, y, shape, color):
        for r in range(len(shape)):
            for c in range(len(shape[0])):
                if shape[r][c]: self.grid[y+r][x+c] = color
        self.clear_lines()

    def clear_lines(self):
        rows = [r for r in range(8) if all(self.grid[r])]
        cols = [c for c in range(8) if all(self.grid[r][c] for r in range(8))]
        for r in rows: self.grid[r] = [0]*8
        for c in cols:
            for r in range(8): self.grid[r][c] = 0
        self.score += (len(rows) + len(cols)) * 10

# ==========================================
# 3. CLASS CHÍNH: SMART OS
# ==========================================
class SmartOS:
    def __init__(self):
        self.state = "MENU"
        self.page = 0
        self.running = True
        self.translator = Translator()
        self.weather_info = "Đang tải..."
        
        # Danh sách 12 ứng dụng (Theo yêu cầu)
        self.apps = [
            {"name": "Đa phương tiện", "icon": "🎞️", "color": "#f9e2af", "cmd": self.go_media},
            {"name": "Trò chơi", "icon": "🎮", "color": "#a6e3a1", "cmd": self.go_game},
            {"name": "Thời tiết", "icon": "⛅", "color": "#89dceb", "cmd": self.go_weather},
            {"name": "Hệ thống", "icon": "🖥️", "color": "#89b4fa", "cmd": self.go_sys},
            {"name": "Dịch thuật", "icon": "🗣️", "color": "#cba6f7", "cmd": self.go_trans},
            {"name": "Wikipedia", "icon": "🌐", "color": "#fab387", "cmd": self.go_wiki},
            {"name": "Đồng hồ", "icon": "⏰", "color": "#f38ba8", "cmd": self.not_impl},
            {"name": "Ghi chú", "icon": "📝", "color": "#94e2d5", "cmd": self.not_impl},
            {"name": "Lịch", "icon": "📅", "color": "#eba0ac", "cmd": self.not_impl},
            {"name": "WiFi", "icon": "📡", "color": "#f5c2e7", "cmd": self.not_impl},
            {"name": "Cài đặt", "icon": "⚙️", "color": "#a6adc8", "cmd": self.not_impl},
            {"name": "Tắt máy", "icon": "🔌", "color": "#313244", "cmd": sys.exit}
        ]
        
        pygame.mixer.init()

    # --- Điều hướng Apps ---
    def go_media(self): self.state = "MEDIA_SELECT"
    def go_game(self): self.game = MiniGame(); self.state = "GAME"
    def go_sys(self): self.state = "SYS_INFO"
    def go_weather(self): 
        self.state = "WEATHER"
        threading.Thread(target=self.fetch_weather, daemon=True).start()
    def go_trans(self): self.state = "TRANS"
    def go_wiki(self): self.state = "WIKI"
    def not_impl(self): pass

    # --- Vẽ giao diện ---
    def draw_status_bar(self, draw):
        now = datetime.datetime.now().strftime("%H:%M")
        draw.rectangle((0, 0, WIDTH, 22), fill="#11111b")
        draw.text((WIDTH-45, 3), now, fill="white", font=font_sm)
        draw.text((10, 3), "OS v2.0", fill=ACCENT_COLOR, font=font_sm)

    def draw_menu(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        self.draw_status_bar(draw)

        start = self.page * APPS_PER_PAGE
        page_apps = self.apps[start : start + APPS_PER_PAGE]

        for i, app in enumerate(page_apps):
            ix = (i % 3) * 102 + 10
            iy = (i // 3) * 95 + 32
            draw.rounded_rectangle((ix, iy, ix+95, iy+85), radius=12, fill=CARD_COLOR, outline=app['color'], width=1)
            draw.text((ix+30, iy+15), app['icon'], fill="white", font=font_icon)
            # Tự động xuống dòng tên app nếu dài
            name_label = "\n".join(textwrap.wrap(app['name'], width=12))
            draw.text((ix+10, iy+52), name_label, fill=TEXT_COLOR, font=font_sm)

        # Footer Nav
        if self.page > 0: draw.text((10, 218), "<< TRƯỚC", fill=ACCENT_COLOR, font=font_sm)
        if (self.page+1)*APPS_PER_PAGE < len(self.apps): draw.text((WIDTH-70, 218), "SAU >>", fill=ACCENT_COLOR, font=font_sm)
        
        device.display(img)

    def draw_sys_info(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        self.draw_status_bar(draw)
        
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        temp = 0 # Cần thư viện hỗ trợ nhiệt độ Raspberry Pi cụ thể
        
        draw.text((20, 35), "THÔNG TIN HỆ THỐNG", fill=ACCENT_COLOR, font=font_md)
        draw.text((20, 70), f"CPU Usage: {cpu}%", fill="white", font=font_sm)
        draw.rectangle((20, 85, 20 + cpu*2.5, 95), fill=WARN_COLOR)
        
        draw.text((20, 110), f"RAM Usage: {ram}%", fill="white", font=font_sm)
        draw.rectangle((20, 125, 20 + ram*2.5, 135), fill=SUCCESS_COLOR)

        draw.rounded_rectangle((WIDTH-60, 205, WIDTH-10, 230), radius=5, fill=WARN_COLOR)
        draw.text((WIDTH-50, 210), "BACK", fill="black", font=font_sm)
        device.display(img)

    def fetch_weather(self):
        try:
            r = requests.get("http://api.openweathermap.org/data/2.5/weather?appid=383c5c635c88590b37c698bc100f6377&q=Hanoi,VN&units=metric&lang=vi")
            data = r.json()
            self.weather_info = f"{data['name']}\n{data['main']['temp']}°C\n{data['weather'][0]['description']}"
        except: self.weather_info = "Lỗi kết nối mạng!"

    # --- Xử lý cảm ứng ---
    def handle_touch(self, x, y):
        if self.state == "MENU":
            if y > 210:
                if x < 100 and self.page > 0: self.page -= 1
                elif x > 220 and (self.page+1)*APPS_PER_PAGE < len(self.apps): self.page += 1
            else:
                col, row = x // 105, (y-30) // 95
                idx = self.page * APPS_PER_PAGE + (row * 3 + col)
                if idx < len(self.apps): self.apps[idx]['cmd']()
        
        elif self.state in ["SYS_INFO", "WEATHER", "GAME", "MEDIA_SELECT"]:
            if x > 250 and y > 200: self.state = "MENU"

    def run(self):
        while self.running:
            if self.state == "MENU": self.draw_menu()
            elif self.state == "SYS_INFO": self.draw_sys_info()
            # Xử lý các state khác...
            
            p = touch.get_touch()
            if p: self.handle_touch(p[0], p[1])
            time.sleep(0.1)

if __name__ == "__main__":
    SmartOS().run()
