import os
import sys
import time
import subprocess
import threading
import signal
import datetime
import textwrap
import math
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

# Theme màu sắc
BG_COLOR = "#1e1e2e"
ACCENT_COLOR = "#89b4fa"
TEXT_COLOR = "#cdd6f4"
WARN_COLOR = "#f38ba8"
SUCCESS_COLOR = "#a6e3a1"
PLAYER_BG = "#181825"
READER_BG = "#11111b"
READER_TEXT = "#bac2de"

USER_HOME = "/home/dinhphuc"
DIRS = {
    "MUSIC": os.path.join(USER_HOME, "Music"),
    "VIDEO": os.path.join(USER_HOME, "Videos"),
    "PHOTO": os.path.join(USER_HOME, "Pictures"),
    "BOOK":  os.path.join(USER_HOME, "Documents")
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# Font: Sử dụng font mặc định nếu không tìm thấy font đẹp để tránh lỗi
def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

font_lg = load_font(18)
font_md = load_font(14)
font_sm = load_font(10)

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
# 3. CLASS CHÍNH
# ==========================================

class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.running = True
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.last_touch = 0
        
        # Bluetooth
        self.bt_devices = []
        self.bt_scanning = False
        
        # Book Reader
        self.book_lines = []
        self.book_page_lines = 9  # Giảm số dòng để chừa chỗ cho footer
        self.book_current_page = 0
        self.book_total_pages = 0
        
        # Music Player
        self.volume = 0.5
        self.music_start_time = 0
        self.music_paused_time = 0
        self.is_paused = False
        
        # Video
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

    # --- HELPER VẼ ---
    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 45, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white", font=None):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=6, fill=bg_color)
        f = font if font else font_md
        bbox = draw.textbbox((0, 0), text, font=f)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text((x + (w - text_w)/2, y + (h - text_h)/2 - 1), text, fill=text_color, font=f)

    # --- MÀN HÌNH ---
    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        title = "PI MEDIA"
        bbox = draw.textbbox((0,0), title, font=font_lg)
        draw.text(((WIDTH - (bbox[2]-bbox[0]))/2, 35), title, fill=ACCENT_COLOR, font=font_lg)

        # Sử dụng text đơn giản thay vì icon unicode để tránh lỗi font
        items = [
            ("MUSIC", "#f9e2af"), ("VIDEO", "#f38ba8"),
            ("PHOTO", "#a6e3a1"), ("E-BOOK", "#89b4fa"),
            ("BLUETOOTH", "#cba6f7")
        ]
        
        start_y = 70
        btn_w, btn_h = 90, 60
        gap = 15
        start_x = (WIDTH - (btn_w * 3 + gap * 2)) / 2

        for i, (label, color) in enumerate(items):
            row = i // 3
            col = i % 3
            x = start_x + col * (btn_w + gap)
            y = start_y + row * (btn_h + gap)
            
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=8, fill="#313244", outline=color, width=2)
            draw.text((x + (btn_w - font_sm.getlength(label))/2, y + 22), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR, text_color="black", font=font_sm)

        list_y = 55
        item_h = 30
        max_items = 5
        
        display_list = self.files[self.scroll_offset : self.scroll_offset + max_items]
        
        if not self.files:
            draw.text((WIDTH//2 - 60, 100), "(Empty)", fill="grey", font=font_md)
            return

        for i, item in enumerate(display_list):
            bg = "#585b70" if (self.scroll_offset + i) == self.selected_idx else BG_COLOR
            fg = "cyan" if (self.scroll_offset + i) == self.selected_idx else "white"
            name = item['name'] if isinstance(item, dict) else item
            
            draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=bg)
            # Dùng ký tự [F] thay vì icon
            draw.text((10, list_y + i*item_h + 5), f"[F] {name[:25]}", fill=fg, font=font_md)

        # Footer
        btn_y = 205
        self.draw_button(draw, 10, btn_y, 90, 30, "UP")
        self.draw_button(draw, 115, btn_y, 90, 30, "OPEN", bg_color=SUCCESS_COLOR, text_color="black")
        self.draw_button(draw, 220, btn_y, 90, 30, "DOWN")

    def draw_player_ui(self, draw):
        """Màn hình nghe nhạc - Đã sửa lỗi nút và icon"""
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=PLAYER_BG)
        
        # 1. Nút ESC (Góc trên cùng bên phải)
        self.draw_button(draw, WIDTH - 55, 5, 50, 25, "ESC", bg_color=WARN_COLOR, text_color="black", font=font_sm)
        
        # 2. Thông tin bài hát
        if self.files and 0 <= self.selected_idx < len(self.files):
            song_name = self.files[self.selected_idx]
            clean_name = os.path.splitext(song_name)[0]
            draw.text((20, 40), "Now Playing:", fill="grey", font=font_sm)
            # Tách chuỗi để tránh lỗi hiển thị nếu quá dài
            draw.text((20, 60), clean_name[:20], fill="white", font=font_lg)
            draw.text((20, 85), clean_name[20:40], fill="white", font=font_lg)

        # 3. Thanh Progress Bar (Giả lập)
        bar_y = 130
        draw.rectangle((20, bar_y, 300, bar_y+4), fill="#313244")
        if pygame.mixer.music.get_busy():
            # Hiệu ứng visual đơn giản
            import math
            prog = (math.sin(time.time()) + 1) / 2
            draw.rectangle((20, bar_y, 20 + 280*prog, bar_y+4), fill=ACCENT_COLOR)

        # 4. Nút điều khiển (Vẽ hình thay vì dùng font icon để tránh lỗi)
        btn_y = 170
        
        # Nút Prev ( |< )
        self.draw_button(draw, 20, btn_y, 60, 40, "|<", bg_color="#45475a")
        
        # Nút Play/Pause (Vẽ hình tam giác/hai gạch)
        cx, cy = 160, btn_y + 20
        draw.rounded_rectangle((130, btn_y, 190, btn_y+40), radius=10, fill=ACCENT_COLOR)
        if pygame.mixer.music.get_busy() and not self.is_paused:
            # Vẽ Pause (||)
            draw.rectangle((cx-6, cy-8, cx-2, cy+8), fill="black")
            draw.rectangle((cx+2, cy-8, cx+6, cy+8), fill="black")
        else:
            # Vẽ Play (Tam giác)
            draw.polygon([(cx-4, cy-8), (cx-4, cy+8), (cx+8, cy)], fill="black")

        # Nút Next ( >| )
        self.draw_button(draw, 240, btn_y, 60, 40, ">|", bg_color="#45475a")
        
        # Nút Volume (Hàng dưới cùng)
        vol_y = 220
        self.draw_button(draw, 50, vol_y, 40, 18, "-", font=font_sm)
        draw.text((140, vol_y), f"VOL: {int(self.volume*10)}" , fill="white", font=font_sm)
        self.draw_button(draw, 230, vol_y, 40, 18, "+", font=font_sm)

    def draw_reader(self, draw):
        """Màn hình đọc sách - 3 nút cùng hàng dưới đáy"""
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=READER_BG)
        
        # Nội dung sách
        margin_x = 10
        y = 10
        if not self.book_lines:
            draw.text((margin_x, 50), "Error loading file", fill="red", font=font_md)
        else:
            start = self.book_current_page * self.book_page_lines
            end = start + self.book_page_lines
            for line in self.book_lines[start:end]:
                draw.text((margin_x, y), line, fill=READER_TEXT, font=font_md)
                y += 22

        # FOOTER: 3 Nút (Trước - Thoát - Sau)
        footer_y = 205
        btn_h = 30
        btn_w = 80
        
        # Nút Trước
        self.draw_button(draw, 10, footer_y, btn_w, btn_h, "<< PREV", font=font_sm)
        
        # Nút Thoát (Ở giữa)
        self.draw_button(draw, 120, footer_y, btn_w, btn_h, "EXIT", bg_color=WARN_COLOR, text_color="black", font=font_sm)
        
        # Nút Sau
        self.draw_button(draw, 230, footer_y, btn_w, btn_h, "NEXT >>", font=font_sm)
        
        # Số trang (Nhỏ ở trên nút Exit)
        pg_str = f"{self.book_current_page+1}/{self.book_total_pages}"
        w_pg = font_sm.getlength(pg_str)
        draw.text(((WIDTH-w_pg)/2, footer_y - 12), pg_str, fill="grey", font=font_sm)

    def render(self):
        image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(image)

        if self.state == "MENU":
            self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            title_map = {"MUSIC": "MUSIC LIST", "VIDEO": "VIDEO LIST", "PHOTO": "PHOTO LIST", "BOOK": "BOOKS", "BT": "BLUETOOTH"}
            self.draw_list(draw, title_map.get(self.state, ""))
        elif self.state == "PLAYING_MUSIC":
            self.draw_player_ui(draw)
        elif self.state == "READING":
            self.draw_reader(draw)
        elif self.state == "VIEWING_PHOTO":
            pass 

        if self.state not in ["PLAYING_VIDEO", "VIEWING_PHOTO"]:
            device.display(image)

    # --- LOGIC ---
    def load_files(self, type_key, ext):
        self.files = sorted([f for f in os.listdir(DIRS[type_key]) if f.lower().endswith(ext)])
        self.selected_idx = 0
        self.scroll_offset = 0

    def play_song_at_index(self, index):
        """Hàm phụ trợ để phát nhạc theo index (Dùng cho Next/Prev)"""
        if 0 <= index < len(self.files):
            self.selected_idx = index
            full_path = os.path.join(DIRS["MUSIC"], self.files[index])
            try:
                pygame.mixer.music.load(full_path)
                pygame.mixer.music.play()
                self.music_start_time = time.time()
                self.is_paused = False
                self.state = "PLAYING_MUSIC"
            except Exception as e:
                print(f"Music Error: {e}")

    def prepare_book(self, filename):
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_lines = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            for line in lines:
                wrapped = textwrap.wrap(line.strip(), width=38) # Wrap chữ
                if not wrapped: self.book_lines.append("")
                else: self.book_lines.extend(wrapped)
            self.book_total_pages = math.ceil(len(self.book_lines) / self.book_page_lines)
            if self.book_total_pages == 0: self.book_total_pages = 1
        except: self.book_lines = ["Error reading file"]
        self.book_current_page = 0

    def scan_bt(self):
        self.bt_scanning = True
        self.bt_devices = []
        img = Image.new("RGB", (WIDTH, HEIGHT), "black")
        d = ImageDraw.Draw(img)
        d.text((80, 100), "Scanning BT...", fill="lime", font=font_md)
        device.display(img)
        # Giả lập scan để tránh treo nếu không có hardware bluetooth
        time.sleep(1)
        self.bt_scanning = False
        self.files = [{"name": "HC-05", "mac": "00:00:00:00:00:00"}] # Fake data
        self.state = "BT"
        self.render()

    def play_video(self, path):
        if self.is_video_playing: return
        self.is_video_playing = True
        self.state = "PLAYING_VIDEO"
        self.emergency_cleanup()
        
        # FFplay command
        cmd = ['ffplay', '-nodisp', '-autoexit', '-volume', str(int(self.volume*100)), path]
        try:
            self.audio_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Giả lập màn hình video đang chạy
            while self.audio_process.poll() is None:
                if touch.is_touched(): 
                    self.audio_process.kill()
                    break
                time.sleep(0.1)
        except: pass
        self.is_video_playing = False
        self.state = "VIDEO"
        self.render()

    def show_photo(self, path):
        self.state = "VIEWING_PHOTO"
        try:
            img = Image.open(path)
            img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            device.display(img)
            while True:
                time.sleep(0.1)
                if touch.is_touched(): 
                    time.sleep(0.3)
                    break
        except: pass
        self.state = "PHOTO"
        self.render()

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "MENU":
            # Grid logic đơn giản hóa
            if y > 70 and y < 200:
                row = (y - 70) // 75
                col = (x - 20) // 100
                idx = int(row * 3 + col)
                if idx == 0: 
                    self.state = "MUSIC"; self.load_files("MUSIC", ('.mp3', '.wav'))
                elif idx == 1: 
                    self.state = "VIDEO"; self.load_files("VIDEO", ('.mp4',))
                elif idx == 2: 
                    self.state = "PHOTO"; self.load_files("PHOTO", ('.jpg','.png'))
                elif idx == 3: 
                    self.state = "BOOK"; self.load_files("BOOK", ('.txt',))
                elif idx == 4: 
                    threading.Thread(target=self.scan_bt).start(); return
                self.render()

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            # Back Button
            if y < 50 and x > WIDTH - 70:
                self.state = "MENU"; pygame.mixer.music.stop(); self.render(); return
            
            # Nav List
            if y > 200:
                if x < 100: 
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset: self.scroll_offset = self.selected_idx
                elif x > 220:
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5: self.scroll_offset += 1
                else: # OPEN
                    if not self.files: return
                    f = self.files[self.selected_idx]
                    path = os.path.join(DIRS[self.state], f['name'] if isinstance(f, dict) else f)
                    
                    if self.state == "MUSIC": self.play_song_at_index(self.selected_idx)
                    elif self.state == "VIDEO": threading.Thread(target=self.play_video, args=(path,), daemon=True).start(); return
                    elif self.state == "PHOTO": self.show_photo(path); return
                    elif self.state == "BOOK": self.prepare_book(f); self.state = "READING"
                self.render()

        elif self.state == "PLAYING_MUSIC":
            # 1. Nút ESC (Góc trên phải)
            if y < 40 and x > WIDTH - 70:
                self.state = "MUSIC"; pygame.mixer.music.stop(); self.render(); return
            
            # 2. Controls (Hàng giữa: Prev - Play - Next)
            if 170 < y < 210:
                if x < 90: # Prev (Lùi bài)
                    new_idx = self.selected_idx - 1
                    if new_idx >= 0: self.play_song_at_index(new_idx)
                
                elif x < 200: # Play/Pause
                    if self.is_paused: pygame.mixer.music.unpause(); self.is_paused=False
                    else: pygame.mixer.music.pause(); self.is_paused=True
                
                else: # Next (Chuyển bài)
                    new_idx = self.selected_idx + 1
                    if new_idx < len(self.files): self.play_song_at_index(new_idx)

            # 3. Volume (Hàng dưới)
            if y > 220:
                if x < 100: self.volume = max(0, self.volume - 0.1)
                elif x > 200: self.volume = min(1, self.volume + 0.1)
                pygame.mixer.music.set_volume(self.volume)
            
            self.render()

        elif self.state == "READING":
            # Footer navigation (Y > 200)
            if y > 200:
                # Nút Trước (x < 100)
                if x < 100: 
                    self.book_current_page = max(0, self.book_current_page - 1)
                
                # Nút Thoát (100 < x < 220)
                elif x < 220:
                    self.state = "BOOK"
                
                # Nút Sau (x > 220)
                else:
                    self.book_current_page = min(self.book_total_pages - 1, self.book_current_page + 1)
                
                self.render()

    def run(self):
        self.render()
        while self.running:
            if self.state == "PLAYING_MUSIC" and not self.is_paused: self.render()
            pt = touch.get_touch()
            if pt: self.handle_touch(*pt)
            time.sleep(0.1)

if __name__ == "__main__":
    app = PiMediaCenter()
    app.run()
