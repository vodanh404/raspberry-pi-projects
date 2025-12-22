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

# ==========================================
# 2. KHỞI TẠO THIẾT BỊ
# ==========================================
try:
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=60000000)
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

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

# ==========================================
# 3. CLASS CHÍNH: MEDIA CENTER
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
        self.current_media_path = ""

        self.video_stop_event = threading.Event()
        self.video_thread = None
        self.audio_proc = None

    # --- UI DRAWING ---
    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 40, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=5, fill=bg_color)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        text_w, text_h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text((x + (w - text_w)/2, y + (h - text_h)/2 - 2), text, fill=text_color, font=font_md)

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        title = "PI MEDIA HOME"
        bbox = draw.textbbox((0,0), title, font=font_lg)
        draw.text(((WIDTH - (bbox[2]-bbox[0]))/2, 35), title, fill=ACCENT_COLOR, font=font_lg)

        items = [
            ("Music", "♫", "#f9e2af"), ("Video", "►", "#f38ba8"),
            ("Photo", "🖼", "#a6e3a1"), ("Books", "📖", "#89b4fa"),
            ("BlueTooth", "🔵", "#cba6f7")
        ]

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
            draw.text((x + 35, y + 10), icon, fill=color, font=font_icon)
            draw.text((x + (btn_w - font_sm.getlength(label))/2, y + 45), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR)

        list_y = 55
        item_h = 30
        max_items = 5
        display_list = self.files[self.scroll_offset : self.scroll_offset + max_items]

        if not self.files:
            draw.text((WIDTH//2 - 40, 100), "Trống / Empty", fill="grey", font=font_md)
        else:
            for i, item in enumerate(display_list):
                global_idx = self.scroll_offset + i
                is_sel = (global_idx == self.selected_idx)
                bg = "#585b70" if is_sel else BG_COLOR
                fg = "cyan" if is_sel else "white"
                name = item['name'] if isinstance(item, dict) else item
                draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=bg)
                draw.text((10, list_y + i*item_h + 5), f"{'>' if is_sel else ' '} {name[:30]}", fill=fg, font=font_md)

        if len(self.files) > max_items:
            sb_h = int((max_items / len(self.files)) * 140)
            sb_y = list_y + int((self.scroll_offset / len(self.files)) * 140)
            draw.rectangle((WIDTH-5, sb_y, WIDTH, sb_y+sb_h), fill="grey")

        btn_y = 205
        self.draw_button(draw, 10, btn_y, 90, 30, "▲ LÊN")
        self.draw_button(draw, 115, btn_y, 90, 30, "CHỌN ●", bg_color="#a6e3a1", text_color="black")
        self.draw_button(draw, 220, btn_y, 90, 30, "▼ XUỐNG")

    def draw_player_ui(self, draw):
        self.draw_status_bar(draw)
        draw.text((20, 40), "Now Playing:", fill="grey", font=font_sm)
        if self.files:
            song_name = self.files[self.selected_idx]
            draw.text((20, 60), song_name[:25], fill="yellow", font=font_lg)
            if len(song_name) > 25:
                draw.text((20, 85), song_name[25:50], fill="yellow", font=font_lg)

        progress = (pygame.mixer.music.get_pos() / 1000) % 10 / 10 if pygame.mixer.music.get_busy() else 0.5
        draw.rectangle((40, 120, 280, 130), fill="#45475a")
        draw.rectangle((40, 120, 40 + 240*progress, 130), fill=ACCENT_COLOR)

        self.draw_button(draw, 10, 180, 70, 40, "VOL-")
        self.draw_button(draw, 90, 180, 70, 40, "VOL+")
        self.draw_button(draw, 170, 180, 80, 40, "⏸/▶")
        self.draw_button(draw, 260, 180, 50, 40, "BACK")

    def draw_reader(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="black")
        if not hasattr(self, 'book_content') or not self.book_content:
            draw.text((10, 100), "Lỗi đọc file!", fill="red", font=font_md)
        else:
            lines = self.book_content[self.book_page]
            y = 10
            for line in lines:
                draw.text((10, y), line.rstrip(), fill="white", font=font_md)
                y += 22

        draw.line((0, 200, WIDTH, 200), fill="grey")
        draw.text((140, 210), f"{self.book_page+1}/{len(self.book_content)}", fill="cyan", font=font_sm)
        self.draw_button(draw, 5, 205, 70, 30, "<< PREV")
        self.draw_button(draw, 245, 205, 70, 30, "NEXT >>")
        self.draw_button(draw, WIDTH - 75, 5, 70, 30, "EXIT", bg_color=WARN_COLOR)

    def render(self):
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

        if self.state not in ["PLAYING_VIDEO", "VIEWING_PHOTO"]:
            device.display(image)

    # --- BACKEND LOGIC ---
    def cleanup_media(self):
        self.video_stop_event.set()
        if self.audio_proc and self.audio_proc.poll() is None:
            self.audio_proc.terminate()
        os.system("pkill -9 ffmpeg")
        os.system("pkill -9 ffplay")

    def load_files(self, type_key, ext):
        path = DIRS[type_key]
        self.files = sorted([f for f in os.listdir(path) if f.lower().endswith(ext)])
        self.selected_idx = 0
        self.scroll_offset = 0

    def paginate_book(self, filename):
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_content = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for i in range(0, len(lines), 8):
                    self.book_content.append(lines[i:i+8])
        except:
            self.book_content = []
        self.book_page = 0

    def scan_bt(self):
        self.bt_devices = []
        try:
            subprocess.run(["bluetoothctl", "scan", "on"], timeout=6, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
            subprocess.run(["bluetoothctl", "scan", "off"], stdout=subprocess.DEVNULL)
            out = subprocess.check_output(["bluetoothctl", "devices"]).decode("utf-8")
            for line in out.split('\n'):
                if "Device" in line:
                    parts = line.split(' ', 2)
                    if len(parts) > 2:
                        self.bt_devices.append({"mac": parts[1], "name": parts[2]})
        except:
            pass
        self.files = self.bt_devices
        self.state = "BT"
        self.render()

    def play_video_with_audio(self, filepath):
        self.state = "PLAYING_VIDEO"
        self.video_stop_event.clear()
        self.cleanup_media()

        frame_size = WIDTH * HEIGHT * 3

        # 1. Phát âm thanh riêng bằng ffplay
        self.audio_proc = subprocess.Popen([
            'ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', filepath
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 2. Phát video bằng ffmpeg -> rawvideo
        video_cmd = [
            'ffmpeg', '-re', '-i', filepath,
            '-vf', f'scale={WIDTH}:{HEIGHT}:flags=lanczos',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-loglevel', 'quiet', '-'
        ]
        video_proc = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, bufsize=frame_size * 2)

        try:
            while not self.video_stop_event.is_set():
                if touch.is_touched():
                    time.sleep(0.2)
                    break

                raw = video_proc.stdout.read(frame_size)
                if len(raw) != frame_size:
                    break

                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw)
                img = ImageOps.invert(img)  # Sửa màu âm bản nếu cần
                device.display(img)
                time.sleep(0.033)  # ~30fps
        except Exception as e:
            print(f"Video error: {e}")
        finally:
            self.cleanup_media()
            self.state = "VIDEO"
            self.render()

    def show_photo(self, filepath):
        self.state = "VIEWING_PHOTO"
        try:
            img = Image.open(filepath)
            img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            img = ImageOps.invert(img)
            device.display(img)

            while True:
                time.sleep(0.1)
                if touch.is_touched():
                    time.sleep(0.2)
                    break
        except Exception as e:
            print(e)
        finally:
            self.state = "PHOTO"
            self.render()

    # --- TOUCH HANDLING ---
    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "MENU":
            start_y = 70
            btn_w, btn_h = 90, 70
            gap = 20
            start_x = (WIDTH - (btn_w * 3 + gap * 2)) / 2

            col = int((x - start_x) // (btn_w + gap)) if x >= start_x else -1
            row = int((y - start_y) // (btn_h + gap)) if y >= start_y else -1

            if 0 <= row <= 1 and 0 <= col <= 2:
                idx = row * 3 + col
                actions = [
                    ("MUSIC", ('.mp3', '.wav', '.flac')),
                    ("VIDEO", ('.mp4', '.avi', '.mkv')),
                    ("PHOTO", ('.jpg', '.jpeg', '.png', '.bmp')),
                    ("BOOK", ('.txt',)),
                    None  # BT
                ]
                if idx < 4:
                    self.state = actions[idx][0]
                    self.load_files(actions[idx][0], actions[idx][1])
                    self.render()
                elif idx == 4:
                    threading.Thread(target=self.scan_bt, daemon=True).start()

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            if x > WIDTH - 70 and y < 50:  # BACK
                self.cleanup_media()
                pygame.mixer.music.stop()
                self.state = "MENU"
                self.render()
                return

            if y > 200:
                if x < 100:  # UP
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset:
                        self.scroll_offset = self.selected_idx
                elif x > 220:  # DOWN
                    self.selected_idx = min(len(self.files) - 1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5:
                        self.scroll_offset += 1
                else:  # SELECT
                    if not self.files: return
                    item = self.files[self.selected_idx]
                    name = item['name'] if isinstance(item, dict) else item

                    if self.state == "MUSIC":
                        path = os.path.join(DIRS["MUSIC"], name)
                        try:
                            pygame.mixer.music.load(path)
                            pygame.mixer.music.set_volume(self.volume)
                            pygame.mixer.music.play()
                            self.state = "PLAYING_MUSIC"
                        except: pass

                    elif self.state == "VIDEO":
                        path = os.path.join(DIRS["VIDEO"], name)
                        self.video_thread = threading.Thread(target=self.play_video_with_audio, args=(path,), daemon=True)
                        self.video_thread.start()
                        return

                    elif self.state == "PHOTO":
                        path = os.path.join(DIRS["PHOTO"], name)
                        threading.Thread(target=self.show_photo, args=(path,), daemon=True).start()
                        return

                    elif self.state == "BOOK":
                        self.paginate_book(name)
                        self.state = "READING"

                    elif self.state == "BT":
                        mac = item['mac']
                        subprocess.run(["bluetoothctl", "connect", mac], timeout=10)

                self.render()

        elif self.state == "PLAYING_MUSIC":
            if y > 170:
                if x < 80:
                    self.volume = max(0, self.volume - 0.1)
                elif x < 160:
                    self.volume = min(1, self.volume + 0.1)
                elif x < 250:
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
                else:
                    pygame.mixer.music.stop()
                    self.state = "MUSIC"
                pygame.mixer.music.set_volume(self.volume)
                self.render()

        elif self.state == "READING":
            if x > WIDTH - 75 and y < 40:  # EXIT
                self.state = "BOOK"
                self.render()
                return
            if y > 200:
                if x < 100:
                    self.book_page = max(0, self.book_page - 1)
                elif x > 220:
                    self.book_page = min(len(self.book_content)-1, self.book_page + 1)
                self.render()

        elif self.state in ["PLAYING_VIDEO", "VIEWING_PHOTO"]:
            self.video_stop_event.set()
            time.sleep(0.3)
            self.cleanup_media()
            self.state = "VIDEO" if self.state == "PLAYING_VIDEO" else "PHOTO"
            self.render()

    def run(self):
        self.render()
        while self.running:
            touch_pt = touch.get_touch()
            if touch_pt:
                tx, ty = touch_pt
                self.handle_touch(tx, ty)
            time.sleep(0.05)

# ==========================================
# 4. ENTRY POINT
# ==========================================
if __name__ == "__main__":
    def signal_handler(sig, frame):
        print("Shutting down...")
        pygame.mixer.quit()
        os.system("pkill -9 ffmpeg ffplay")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app = PiMediaCenter()
    try:
        app.run()
    finally:
        app.cleanup_media()
        pygame.mixer.quit()
