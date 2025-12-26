import os
import sys
import time
import subprocess
import threading
import signal
import datetime
import textwrapit
import math
import random
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

# Theme màu sắc
BG_COLOR = "#1e1e2e"       
ACCENT_COLOR = "#89b4fa"   
TEXT_COLOR = "#cdd6f4"     
WARN_COLOR = "#f38ba8"     
SUCCESS_COLOR = "#a6e3a1"  
PLAYER_BG = "#181825"      
READER_BG = "#11111b"      
READER_TEXT = "#bac2de"    

# Đường dẫn thư mục
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

font_icon_lg = load_font(32)
font_icon = load_font(24)
font_lg = load_font(18)
font_md = load_font(14)
font_sm = load_font(10)

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ
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
    print(f"Lỗi phần cứng: {e}")
    sys.exit(1)

pygame.mixer.init()

# ==========================================
# 3. GAME BLOCK BLAST ENGINE
# ==========================================
class BlockBlastEngine:
    """Class xử lý logic game, chạy độc lập khi được gọi"""
    GRID_SIZE = 8
    CELL_SIZE = 26  # Điều chỉnh cho vừa màn hình 240 dọc (Game xoay ngang hoặc dọc tùy thiết kế)
    # Ở đây ta giữ màn hình ngang 320x240.
    # Grid sẽ nằm bên trái (208x208), Panel điều khiển bên phải.
    
    SHAPES = [
        [[1]], [[1, 1]], [[1], [1]], [[1, 1], [1, 1]],
        [[1, 1, 1]], [[1], [1], [1]], [[1, 0], [1, 0], [1, 1]], [[0, 1, 0], [1, 1, 1]]
    ]
    COLORS = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF"]

    def __init__(self, display_device, touch_driver):
        self.device = display_device
        self.touch = touch_driver
        self.grid = [[0]*8 for _ in range(8)]
        self.score = 0
        self.running = False
        self.game_over = False
        
        self.available_shapes = []
        self.selected_shape_idx = None
        self.refill_shapes()

    def refill_shapes(self):
        self.available_shapes = []
        for _ in range(3):
            shape = random.choice(self.SHAPES)
            color = random.choice(self.COLORS)
            self.available_shapes.append({'shape': shape, 'color': color, 'active': True})
        self.selected_shape_idx = None

    def check_collision(self, start_x, start_y, shape):
        rows = len(shape)
        cols = len(shape[0])
        if start_x + cols > 8 or start_y + rows > 8: return False
        for r in range(rows):
            for c in range(cols):
                if shape[r][c] == 1 and self.grid[start_y + r][start_x + c] != 0:
                    return False
        return True

    def place_shape(self, start_x, start_y, shape_obj):
        shape = shape_obj['shape']
        color = shape_obj['color']
        rows = len(shape)
        cols = len(shape[0])
        for r in range(rows):
            for c in range(cols):
                if shape[r][c] == 1:
                    self.grid[start_y + r][start_x + c] = color
        
        shape_obj['active'] = False
        self.selected_shape_idx = None
        self.check_lines()
        
        if all(not s['active'] for s in self.available_shapes):
            self.refill_shapes()
            
        if not self.can_place_any():
            self.game_over = True

    def check_lines(self):
        lines = 0
        rows_to_clear = [r for r in range(8) if all(self.grid[r])]
        cols_to_clear = [c for c in range(8) if all(self.grid[r][c] for r in range(8))]
        
        for r in rows_to_clear:
            for c in range(8): self.grid[r][c] = 0
        for c in cols_to_clear:
            for r in range(8): self.grid[r][c] = 0
            
        if rows_to_clear or cols_to_clear:
            self.score += (len(rows_to_clear) + len(cols_to_clear)) * 10

    def can_place_any(self):
        for s in self.available_shapes:
            if not s['active']: continue
            for y in range(8):
                for x in range(8):
                    if self.check_collision(x, y, s['shape']): return True
        return False

    def render(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), "#202020")
        draw = ImageDraw.Draw(img)
        
        # 1. Vẽ Grid (Bên trái)
        offset_x, offset_y = 10, 16
        cell_size = 26
        
        # Vẽ khung grid
        draw.rectangle((offset_x-2, offset_y-2, offset_x + 8*cell_size + 1, offset_y + 8*cell_size + 1), outline="white")
        
        for r in range(8):
            for c in range(8):
                x = offset_x + c * cell_size
                y = offset_y + r * cell_size
                col = self.grid[r][c]
                if col == 0:
                    draw.rectangle((x, y, x+cell_size-1, y+cell_size-1), outline="#404040")
                else:
                    draw.rectangle((x, y, x+cell_size-1, y+cell_size-1), fill=col)

        # 2. UI Bên phải (Score, Shapes, Exit)
        right_panel_x = 230
        draw.text((right_panel_x, 10), "ĐIỂM SỐ", fill="white", font=font_sm)
        draw.text((right_panel_x, 25), str(self.score), fill="yellow", font=font_lg)
        
        # Nút thoát
        draw.rounded_rectangle((right_panel_x, HEIGHT - 40, right_panel_x + 80, HEIGHT - 10), radius=5, fill="#cc3333")
        draw.text((right_panel_x + 20, HEIGHT - 35), "THOÁT", fill="white", font=font_md)

        # 3. Vẽ Shape (3 ô dọc bên phải)
        spawn_y = 60
        for idx, item in enumerate(self.available_shapes):
            if not item['active']: continue
            shape = item['shape']
            color = item['color']
            is_sel = (idx == self.selected_shape_idx)
            
            base_y = spawn_y + idx * 50
            outline = "white" if is_sel else None
            
            # Vẽ mini preview
            for r in range(len(shape)):
                for c in range(len(shape[0])):
                    if shape[r][c]:
                        sx = right_panel_x + c * 8
                        sy = base_y + r * 8
                        draw.rectangle((sx, sy, sx+7, sy+7), fill=color, outline=outline)

        if self.game_over:
            draw.rectangle((50, 80, 200, 160), fill="black", outline="red")
            draw.text((80, 100), "GAME OVER", fill="red", font=font_lg)
            draw.text((70, 130), "Chạm để reset", fill="white", font=font_sm)

        self.device.display(img)

    def run(self):
        """Vòng lặp chính của game"""
        self.running = True
        self.game_over = False
        self.grid = [[0]*8 for _ in range(8)]
        self.score = 0
        self.refill_shapes()
        
        while self.running:
            self.render()
            
            # Logic cảm ứng
            t = self.touch.get_touch()
            if t:
                tx, ty = t
                # Xử lý thoát
                if tx > 230 and ty > HEIGHT - 40:
                    self.running = False
                    return

                if self.game_over:
                    self.game_over = False
                    self.grid = [[0]*8 for _ in range(8)]
                    self.score = 0
                    self.refill_shapes()
                    time.sleep(0.5)
                    continue

                # Xử lý chọn Shape (Bên phải)
                if tx > 230 and ty < HEIGHT - 50:
                    slot = (ty - 60) // 50
                    if 0 <= slot < 3 and self.available_shapes[slot]['active']:
                        self.selected_shape_idx = slot

                # Xử lý đặt vào Grid (Bên trái)
                elif tx < 10 + 8*26 and ty < 16 + 8*26:
                    if self.selected_shape_idx is not None:
                        g_x = int((tx - 10) // 26)
                        g_y = int((ty - 16) // 26)
                        shape_obj = self.available_shapes[self.selected_shape_idx]
                        if self.check_collision(g_x, g_y, shape_obj['shape']):
                            self.place_shape(g_x, g_y, shape_obj)

            time.sleep(0.05)

# ==========================================
# 4. CLASS CHÍNH: MEDIA CENTER
# ==========================================

class PiMediaCenter:
    def __init__(self):
        self.state = "MENU" # Các state: MENU, MEDIA_SELECT, GAME, BT, ...
        self.running = True
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.last_touch = 0
        
        # Biến hệ thống
        self.bt_devices = []
        self.volume = 0.5
        self.music_start_time = 0
        self.music_paused_time = 0
        self.is_paused = False
        self.book_lines = []
        self.book_current_page = 0
        self.book_total_pages = 0

    def cleanup(self):
        os.system("pkill -9 ffplay")
        os.system("pkill -9 ffmpeg")
        pygame.mixer.music.stop()

    # --- UI MENU CHÍNH (GRID 12 APPS) ---
    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        
        # Lưới 3 cột x 4 hàng
        cols = 3
        rows = 4
        btn_w, btn_h = 90, 45
        gap_x, gap_y = 10, 10
        start_x = (WIDTH - (btn_w * cols + gap_x * (cols-1))) // 2
        start_y = 35

        # Danh sách 12 Ứng dụng
        apps = [
            ("Đa p.tiện", "📂", "#f9e2af", "MEDIA_SELECT"), 
            ("Trò chơi", "🎮", "#a6e3a1", "GAME"),
            ("Bluetooth", "📶", "#89b4fa", "BT"),
            ("Cài đặt", "⚙", "#fab387", "SETTINGS"),
            ("WiFi", "📡", "#cba6f7", "WIFI"),
            ("Lịch", "📅", "#eba0ac", "CALENDAR"),
            ("Hệ thống", "🖥", "#94e2d5", "SYS"),
            ("Ghi âm", "🎤", "#f5c2e7", "REC"),
            ("Thời tiết", "⛅", "#f2cdcd", "WEATHER"),
            ("Đồng hồ", "⏰", "#f38ba8", "CLOCK"),
            ("Ghi chú", "📝", "#a6adc8", "NOTE"),
            ("Tắt máy", "🔌", "#313244", "SHUTDOWN")
        ]

        for i, (label, icon, color, action) in enumerate(apps):
            r = i // cols
            c = i % cols
            x = start_x + c * (btn_w + gap_x)
            y = start_y + r * (btn_h + gap_y)
            
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=8, fill="#313244", outline=color, width=2)
            # Icon bên trái, Text bên phải
            draw.text((x + 10, y + 8), icon, fill=color, font=font_icon)
            draw.text((x + 40, y + 15), label, fill="white", font=font_sm)

    def draw_media_select(self, draw):
        """Menu con chọn loại Media"""
        self.draw_status_bar(draw)
        draw.text((20, 30), "THƯ VIỆN MEDIA", fill=ACCENT_COLOR, font=font_lg)
        
        # Nút Back
        self.draw_button(draw, WIDTH-70, 30, 60, 25, "BACK", bg_color=WARN_COLOR)

        items = [
            ("Nghe Nhạc", "♫", "#f9e2af", "MUSIC"),
            ("Xem Phim", "►", "#f38ba8", "VIDEO"),
            ("Xem Ảnh", "☘", "#a6e3a1", "PHOTO"),
            ("Đọc Sách", "☕", "#89b4fa", "BOOK")
        ]
        
        # Grid 2x2
        bx, by = 40, 70
        bw, bh = 110, 70
        gap = 20
        
        for i, (label, icon, color, mode) in enumerate(items):
            r = i // 2
            c = i % 2
            x = bx + c*(bw+gap)
            y = by + r*(bh+gap)
            
            draw.rounded_rectangle((x, y, x+bw, y+bh), radius=10, fill="#313244", outline=color)
            draw.text((x+45, y+10), icon, fill=color, font=font_icon)
            draw.text((x+20, y+45), label, fill="white", font=font_md)

    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 45, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white", icon_font=None):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=8, fill=bg_color)
        f = icon_font if icon_font else font_md
        bbox = draw.textbbox((0, 0), text, font=f)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x + (w - text_w)/2, y + (h - text_h)/2 - 1), text, fill=text_color, font=f)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR, text_color="black")

        list_y = 55
        item_h = 30
        max_items = 5
        display_list = self.files[self.scroll_offset : self.scroll_offset + max_items]
        
        if not self.files:
            draw.text((80, 100), "Trống rỗng...", fill="grey", font=font_md)
        
        for i, item in enumerate(display_list):
            is_sel = (self.scroll_offset + i == self.selected_idx)
            bg = "#585b70" if is_sel else BG_COLOR
            name = item['name'] if isinstance(item, dict) else item
            draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=bg)
            draw.text((10, list_y + i*item_h + 5), f"> {name[:28]}", fill="cyan" if is_sel else "white", font=font_md)

        # Footer Nav
        btn_y = 205
        self.draw_button(draw, 10, btn_y, 90, 30, "▲ LÊN")
        self.draw_button(draw, 115, btn_y, 90, 30, "CHỌN", bg_color=SUCCESS_COLOR, text_color="black")
        self.draw_button(draw, 220, btn_y, 90, 30, "▼ XUỐNG")

    # --- LOGIC XỬ LÝ ---
    def load_files(self, type_key, ext):
        try:
            self.files = sorted([f for f in os.listdir(DIRS[type_key]) if f.lower().endswith(ext)])
        except: self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0

    def play_music_file(self):
        if not self.files: return
        path = os.path.join(DIRS["MUSIC"], self.files[self.selected_idx])
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play()
        self.music_start_time = time.time()
        self.state = "PLAYING_MUSIC"

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        # 1. MENU CHÍNH (GRID 12)
        if self.state == "MENU":
            start_x, start_y = 15, 35
            btn_w, btn_h = 90, 45
            gap_x, gap_y = 10, 10
            
            # Tính toán tọa độ lưới
            col = int((x - start_x) // (btn_w + gap_x))
            row = int((y - start_y) // (btn_h + gap_y))
            
            if 0 <= col < 3 and 0 <= row < 4:
                idx = row * 3 + col
                if idx == 0: self.state = "MEDIA_SELECT" # Đa phương tiện
                elif idx == 1: # Game
                    game = BlockBlastEngine(device, touch)
                    game.run() # Chặn luồng chính cho đến khi game thoát
                    self.state = "MENU" # Quay về menu khi thoát game
                elif idx == 2: # Bluetooth
                    self.state = "BT"
                    threading.Thread(target=self.scan_bt).start()
                elif idx == 11: # Shutdown
                    sys.exit(0)
                # Các app khác là placeholder
            self.render()

        # 2. MEDIA SELECT (SUB-MENU)
        elif self.state == "MEDIA_SELECT":
            if x > WIDTH - 70 and y < 60: # Back
                self.state = "MENU"
                self.render()
                return
            
            # Grid 2x2
            bx, by = 40, 70
            bw, bh = 110, 70
            gap = 20
            
            col = int((x - bx) // (bw + gap))
            row = int((y - by) // (bh + gap))
            
            if 0 <= col < 2 and 0 <= row < 2:
                midx = row * 2 + col
                if midx == 0: 
                    self.state = "MUSIC"
                    self.load_files("MUSIC", ('.mp3',))
                elif midx == 1:
                    self.state = "VIDEO"
                    self.load_files("VIDEO", ('.mp4',))
                elif midx == 2:
                    self.state = "PHOTO"
                    self.load_files("PHOTO", ('.jpg', '.png'))
                elif midx == 3:
                    self.state = "BOOK"
                    self.load_files("BOOK", ('.txt',))
            self.render()

        # 3. LIST FILES & PLAYER UI
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            # Back Button
            if x > WIDTH - 70 and y < 50:
                self.cleanup()
                self.state = "MEDIA_SELECT" if self.state != "BT" else "MENU"
                self.render()
                return

            # Nav Buttons
            if y > 200:
                if x < 100: # UP
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset: self.scroll_offset = self.selected_idx
                elif x > 220: # DOWN
                    self.selected_idx = min(len(self.files) - 1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5: self.scroll_offset += 1
                else: # SELECT
                    if not self.files: return
                    if self.state == "MUSIC": self.play_music_file()
                    elif self.state == "VIDEO":
                        path = os.path.join(DIRS["VIDEO"], self.files[self.selected_idx])
                        threading.Thread(target=self.play_video_stream, args=(path,), daemon=True).start()
                    elif self.state == "PHOTO":
                        path = os.path.join(DIRS["PHOTO"], self.files[self.selected_idx])
                        self.show_photo(path)
                    elif self.state == "BOOK":
                        self.prepare_book(self.files[self.selected_idx])
                        self.state = "READING"
            self.render()

        # 4. MUSIC PLAYING UI
        elif self.state == "PLAYING_MUSIC":
            if x > WIDTH - 60 and y < 30: # Close
                pygame.mixer.music.stop()
                self.state = "MUSIC"
            elif y > 170: # Controls
                if x < 60: self.volume = max(0, self.volume-0.1); pygame.mixer.music.set_volume(self.volume)
                elif x < 120: pass # Prev logic
                elif x < 190: 
                    if self.is_paused: pygame.mixer.music.unpause(); self.is_paused=False
                    else: pygame.mixer.music.pause(); self.is_paused=True
                elif x < 250: pass # Next logic
                else: self.volume = min(1, self.volume+0.1); pygame.mixer.music.set_volume(self.volume)
            self.render()
            
        # 5. READING UI
        elif self.state == "READING":
            if x > WIDTH - 60 and y < 30: self.state = "BOOK"
            elif y > 180:
                if x < 100: self.book_current_page = max(0, self.book_current_page - 1)
                elif x > 220: self.book_current_page = min(self.book_total_pages - 1, self.book_current_page + 1)
            self.render()

    # --- CÁC HÀM HỖ TRỢ HIỂN THỊ CŨ (RÚT GỌN) ---
    def render(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        if self.state == "MENU": self.draw_menu(draw)
        elif self.state == "MEDIA_SELECT": self.draw_media_select(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            title = {"MUSIC":"NHẠC", "VIDEO":"PHIM", "PHOTO":"ẢNH", "BOOK":"SÁCH", "BT":"BLUETOOTH"}.get(self.state,"")
            self.draw_list(draw, title)
        elif self.state == "PLAYING_MUSIC": self.draw_player_ui(draw)
        elif self.state == "READING": self.draw_reader(draw)
        
        if self.state != "PLAYING_VIDEO" and self.state != "VIEWING_PHOTO":
            device.display(img)

    def draw_player_ui(self, draw):
        # (Giữ nguyên logic vẽ Player UI từ code cũ)
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=PLAYER_BG)
        self.draw_status_bar(draw)
        draw.text((120, 40), "Đang phát...", fill="white", font=font_lg)
        if self.files: draw.text((120, 65), self.files[self.selected_idx][:20], fill="cyan", font=font_md)
        # Control Buttons
        btn_y = 180
        self.draw_button(draw, 20, btn_y, 40, 30, "-")
        self.draw_button(draw, 130, btn_y, 60, 40, "||" if not self.is_paused else "►", bg_color=ACCENT_COLOR, text_color="black")
        self.draw_button(draw, 260, btn_y, 40, 30, "+")
        # Nút đóng
        self.draw_button(draw, WIDTH-60, 5, 50, 25, "X", bg_color=WARN_COLOR)

    def draw_reader(self, draw):
        # (Giữ nguyên logic vẽ Reader UI từ code cũ)
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=READER_BG)
        if self.book_lines:
            s, e = self.book_current_page*10, (self.book_current_page+1)*10
            for i, line in enumerate(self.book_lines[s:e]):
                draw.text((10, 15 + i*20), line, fill=READER_TEXT, font=font_md)
        draw.text((120, 215), f"{self.book_current_page+1}/{self.book_total_pages}", fill="grey", font=font_sm)
        self.draw_button(draw, 5, 210, 60, 25, "< PREV")
        self.draw_button(draw, WIDTH-65, 210, 60, 25, "NEXT >")
        self.draw_button(draw, WIDTH-60, 5, 50, 25, "EXIT", bg_color=WARN_COLOR)

    def prepare_book(self, filename):
        # Logic wrap text như cũ
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_lines = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    self.book_lines.extend(textwrapit.wrap(line.strip(), 36) or [""])
            self.book_total_pages = math.ceil(len(self.book_lines) / 10) or 1
        except: pass
        self.book_current_page = 0

    def scan_bt(self):
        # (Giữ logic cũ)
        pass

    def play_video_stream(self, filepath):
        # (Giữ logic cũ)
        self.state = "PLAYING_VIDEO"
        self.cleanup()
        cmd = ['ffplay', '-nodisp', '-autoexit', '-volume', str(int(self.volume*100)), filepath]
        vid = ['ffmpeg', '-re', '-i', filepath, '-vf', f'scale={WIDTH}:{HEIGHT},format=rgb24', 
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        try:
            ap = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            vp = subprocess.Popen(vid, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3)
            while True:
                raw = vp.stdout.read(WIDTH*HEIGHT*3)
                if not raw or ap.poll() is not None: break
                device.display(ImageOps.invert(Image.frombytes('RGB', (WIDTH, HEIGHT), raw)))
                if touch.is_touched(): break
        except: pass
        self.cleanup()
        self.state = "VIDEO"
        self.render()

    def show_photo(self, filepath):
        # (Giữ logic cũ)
        try:
            img = ImageOps.fit(Image.open(filepath), (WIDTH, HEIGHT))
            device.display(ImageOps.invert(img))
            while not touch.is_touched(): time.sleep(0.1)
        except: pass
        self.state = "PHOTO"
        self.render()
    
    def run(self):
        self.render()
        while True:
            if self.state == "PLAYING_MUSIC" and not self.is_paused: self.render()
            pt = touch.get_touch()
            if pt: self.handle_touch(*pt)
            time.sleep(0.1)

if __name__ == "__main__":
    app = PiMediaCenter()
    app.run()
