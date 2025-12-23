import os
import sys
import time
import subprocess
import threading
import signal
import datetime
import textwrap
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
BG_COLOR = "#1e1e2e"       # Catppuccin Mocha Base
ACCENT_COLOR = "#89b4fa"   # Blue
TEXT_COLOR = "#cdd6f4"     # Text
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
        # Đường dẫn font phổ biến trên Raspberry Pi OS
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()

fonts = {
    "sm": load_font(12),
    "md": load_font(16),
    "lg": load_font(20),
    "icon": load_font(28)
}

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ
# ==========================================
try:
    # Cấu hình LCD ST7789
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0)
    device.backlight(True)

    # Cấu hình Cảm ứng XPT2046
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=WIDTH, height=HEIGHT, 
                    x_min=150, x_max=1900, y_min=150, y_max=1850)
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
        self.last_touch_time = 0
        self.volume = 0.5
        
        # Biến điều khiển media
        self.is_playing = False
        self.current_proc_video = None
        self.current_proc_audio = None
        
        # Biến cho Sách
        self.book_pages = []
        self.current_page = 0
        self.book_title = ""

    def cleanup_processes(self):
        """Dọn dẹp tất cả tiến trình media đang chạy"""
        if self.current_proc_video:
            try: self.current_proc_video.kill()
            except: pass
        if self.current_proc_audio:
            try: self.current_proc_audio.kill()
            except: pass
        os.system("pkill -9 ffmpeg")
        os.system("pkill -9 ffplay")
        pygame.mixer.music.stop()

    # --- HÀM VẼ GIAO DIỆN ---

    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 45, 4), time_str, fill="white", font=fonts["sm"])
        draw.text((10, 4), f"Vol: {int(self.volume*100)}%", fill=ACCENT_COLOR, font=fonts["sm"])

    def draw_button(self, draw, x, y, w, h, text, bg="#45475a", fg="white", font_key="md"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=6, fill=bg)
        bbox = draw.textbbox((0, 0), text, font=fonts[font_key])
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((x + (w-tw)/2, y + (h-th)/2 - 2), text, fill=fg, font=fonts[font_key])

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        title = "PI MEDIA CENTER"
        draw.text(((WIDTH - fonts["lg"].getlength(title))/2, 35), title, fill=ACCENT_COLOR, font=fonts["lg"])

        items = [
            ("Nhạc", "♫", "#f9e2af"), ("Video", "▶", "#f38ba8"),
            ("Ảnh", "🖼", "#a6e3a1"), ("Sách", "📖", "#89b4fa"),
            ("BT", "ᛒ", "#cba6f7"), ("Tắt", "⏻", "#94e2d5")
        ]
        
        start_x, start_y = 25, 75
        btn_w, btn_h = 80, 65
        gap_x, gap_y = 20, 15

        for i, (label, icon, color) in enumerate(items):
            row, col = i // 3, i % 3
            x, y = start_x + col * (btn_w + gap_x), start_y + row * (btn_h + gap_y)
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=10, fill="#313244", outline=color, width=2)
            draw.text((x + 28, y + 10), icon, fill=color, font=fonts["icon"])
            draw.text((x + (btn_w - fonts["sm"].getlength(label))/2, y + 45), label, fill="white", font=fonts["sm"])

    def draw_file_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 52), fill="#45475a")
        draw.text((10, 30), title, fill="yellow", font=fonts["md"])
        self.draw_button(draw, WIDTH-65, 28, 55, 22, "THOÁT", bg=WARN_COLOR, font_key="sm")

        list_y, item_h, max_v = 55, 30, 5
        visible_files = self.files[self.scroll_offset : self.scroll_offset + max_v]
        
        if not self.files:
            draw.text((WIDTH//2 - 50, 110), "(Thư mục trống)", fill="grey", font=fonts["md"])
        else:
            for i, filename in enumerate(visible_files):
                idx = self.scroll_offset + i
                is_sel = (idx == self.selected_idx)
                rect_bg = "#585b70" if is_sel else BG_COLOR
                draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=rect_bg)
                prefix = "> " if is_sel else "  "
                draw.text((10, list_y + i*item_h + 5), f"{prefix}{filename[:35]}", fill="white", font=fonts["sm"])

        # Điều hướng
        self.draw_button(draw, 10, 205, 90, 30, "LÊN ▲")
        self.draw_button(draw, 115, 205, 90, 30, "CHỌN ●", bg=SUCCESS_COLOR, fg="black")
        self.draw_button(draw, 220, 205, 90, 30, "XUỐNG ▼")

    # --- TỐI ƯU HÓA TÍNH NĂNG ĐỌC SÁCH ---

    def paginate_book(self, filename):
        """Tối ưu: Tự động ngắt dòng và chia trang hợp lý"""
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_pages = []
        self.book_title = filename
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Cấu hình hiển thị
            chars_per_line = 38 # Ước lượng cho font md ở 320px
            lines_per_page = 9
            
            # Ngắt dòng thông minh
            raw_lines = content.split('\n')
            wrapped_lines = []
            for line in raw_lines:
                if not line.strip():
                    wrapped_lines.append("")
                else:
                    wrapped_lines.extend(textwrap.wrap(line, width=chars_per_line))
            
            # Chia trang
            for i in range(0, len(wrapped_lines), lines_per_page):
                self.book_pages.append(wrapped_lines[i:i+lines_per_page])
            
            if not self.book_pages: self.book_pages = [["(File không có nội dung)"]]
        except Exception as e:
            self.book_pages = [[f"Lỗi: {e}"]]
        self.current_page = 0

    def draw_reader(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#f4ebd0") # Màu giấy cũ cho đỡ mỏi mắt
        page_content = self.book_pages[self.current_page]
        
        # Vẽ nội dung
        y = 10
        for line in page_content:
            draw.text((15, y), line, fill="#2c3e50", font=fonts["md"])
            y += 22
        
        # Thanh trạng thái dưới
        draw.rectangle((0, 210, WIDTH, HEIGHT), fill="#34495e")
        info = f"Trang {self.current_page+1}/{len(self.book_pages)} | {self.book_title[:15]}..."
        draw.text((10, 218), info, fill="white", font=fonts["sm"])
        self.draw_button(draw, WIDTH-70, 214, 60, 22, "ĐÓNG", bg=WARN_COLOR, font_key="sm")

    # --- XỬ LÝ VIDEO & AUDIO ---

    def play_video(self, filename):
        if self.is_playing: return
        self.is_playing = True
        path = os.path.join(DIRS["VIDEO"], filename)
        self.cleanup_processes()

        # FFmpeg: Xuất raw RGB ra stdout
        v_cmd = [
            'ffmpeg', '-re', '-i', path,
            '-vf', f'scale={WIDTH}:{HEIGHT},format=rgb24',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', 
            '-threads', '1', '-preset', 'ultrafast', '-loglevel', 'quiet', '-'
        ]
        # FFplay: Chạy âm thanh ngầm
        a_cmd = ['ffplay', '-nodisp', '-autoexit', '-volume', str(int(self.volume*100)), path]

        try:
            self.current_proc_audio = subprocess.Popen(a_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.current_proc_video = subprocess.Popen(v_cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3)
            
            while self.is_playing:
                raw_frame = self.current_proc_video.stdout.read(WIDTH * HEIGHT * 3)
                if not raw_frame or self.current_proc_audio.poll() is not None:
                    break
                
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw_frame)
                img = ImageOps.invert(img) # Đảo màu cho ST7789 nếu cần
                device.display(img)

                if touch.is_touched(): # Chạm để thoát
                    break
        finally:
            self.is_playing = False
            self.cleanup_processes()
            self.state = "VIDEO"
            self.render()

    def show_photo(self, filename):
        path = os.path.join(DIRS["PHOTO"], filename)
        try:
            img = Image.open(path)
            img = ImageOps.fit(img, (WIDTH, HEIGHT), centering=(0.5, 0.5))
            img = ImageOps.invert(img)
            device.display(img)
            while not touch.is_touched(): time.sleep(0.1)
            time.sleep(0.3)
        except: pass
        self.state = "PHOTO"
        self.render()

    # --- LOGIC ĐIỀU KHIỂN ---

    def load_files(self, key, exts):
        self.files = sorted([f for f in os.listdir(DIRS[key]) if f.lower().endswith(exts)])
        self.selected_idx = 0
        self.scroll_offset = 0

    def render(self):
        if self.state == "PLAYING_VIDEO": return
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        if self.state == "MENU": self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]:
            titles = {"MUSIC":"Kho Nhạc", "VIDEO":"Phim/Clip", "PHOTO":"Thư viện Ảnh", "BOOK":"Kệ Sách"}
            self.draw_file_list(draw, titles[self.state])
        elif self.state == "READING":
            self.draw_reader(draw)
            
        device.display(img)

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch_time < 0.4: return
        self.last_touch_time = now

        if self.state == "MENU":
            if 75 <= y <= 210:
                col, row = (x - 25) // 100, (y - 75) // 80
                idx = row * 3 + col
                if idx == 0: self.state = "MUSIC"; self.load_files("MUSIC", ('.mp3', '.wav'))
                elif idx == 1: self.state = "VIDEO"; self.load_files("VIDEO", ('.mp4', '.mkv'))
                elif idx == 2: self.state = "PHOTO"; self.load_files("PHOTO", ('.jpg', '.png'))
                elif idx == 3: self.state = "BOOK"; self.load_files("BOOK", ('.txt',))
                elif idx == 5: self.running = False
                self.render()

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]:
            if x > WIDTH - 70 and y < 55: # Nút THOÁT
                self.state = "MENU"; self.render(); return
            
            if y > 200: # Điều hướng
                if x < 100: # LÊN
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset: self.scroll_offset = self.selected_idx
                elif x > 220: # XUỐNG
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5: self.scroll_offset += 1
                elif 100 < x < 220 and self.files: # CHỌN
                    fname = self.files[self.selected_idx]
                    if self.state == "VIDEO":
                        threading.Thread(target=self.play_video, args=(fname,), daemon=True).start()
                    elif self.state == "PHOTO":
                        self.show_photo(fname)
                    elif self.state == "BOOK":
                        self.paginate_book(fname)
                        self.state = "READING"
                    elif self.state == "MUSIC":
                        pygame.mixer.music.load(os.path.join(DIRS["MUSIC"], fname))
                        pygame.mixer.music.play()
                self.render()

        elif self.state == "READING":
            if x > WIDTH - 75 and y > 210: # Nút ĐÓNG
                self.state = "BOOK"; self.render()
            elif x < WIDTH // 2: # Chạm bên trái: Lùi trang
                self.current_page = max(0, self.current_page - 1)
                self.render()
            else: # Chạm bên phải: Tiến trang
                self.current_page = min(len(self.book_pages)-1, self.current_page + 1)
                self.render()

    def run(self):
        self.render()
        try:
            while self.running:
                p = touch.get_touch()
                if p: self.handle_touch(p[0], p[1])
                time.sleep(0.05)
        finally:
            self.cleanup_processes()
            pygame.mixer.quit()
            print("Đã thoát ứng dụng.")

# ==========================================
# 4. KHỞI CHẠY
# ==========================================
if __name__ == "__main__":
    app = PiMediaCenter()
    app.run()
