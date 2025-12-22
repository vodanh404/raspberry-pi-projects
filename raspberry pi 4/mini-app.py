import os
import sys
import time
import subprocess
import threading
import signal
import datetime
import pygame
from PIL import Image, ImageFont, ImageDraw, ImageOps
from luma.core.interface.serial import spi as luma_spi
from luma.lcd.device import st7789
import busio
import digitalio

# ==========================================import os
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

font_icon = load_font(28)
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

        self.bt_devices = []
        self.bt_scanning = False
        self.book_content = []
        self.book_page = 0
        self.volume = 0.7
        self.current_media_path = ""

        self.video_process = None  # Để quản lý omxplayer

    # --- VẼ GIAO DIỆN ---
    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 50, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)
        if self.bt_devices:
            draw.text((WIDTH - 80, 5), "BT", fill="#94e2d5", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=8, fill=bg_color)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x + (w - tw)/2, y + (h - th)/2 - 2), text, fill=text_color, font=font_md)

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        title = "PI MEDIA CENTER"
        bbox = draw.textbbox((0,0), title, font=font_lg)
        draw.text(((WIDTH - (bbox[2]-bbox[0]))/2, 30), title, fill=ACCENT_COLOR, font=font_lg)

        items = [
            ("Music", "♫", "#f9e2af"),
            ("Video", "▶", "#f38ba8"),
            ("Photo", "🖼", "#a6e3a1"),
            ("Books", "📖", "#89b4fa"),
            ("Bluetooth", "📶", "#cba6f7")
        ]

        btn_w, btn_h = 100, 80
        gap_x, gap_y = 30, 25
        total_w = 2 * btn_w + gap_x
        start_x = (WIDTH - total_w) / 2
        start_y = 70

        for i, (label, icon, color) in enumerate(items):
            row = i // 2
            col = i % 2
            x = start_x + col * (btn_w + gap_x)
            y = start_y + row * (btn_h + gap_y)

            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=10, fill="#313244", outline=color, width=3)
            draw.text((x + 32, y + 10), icon, fill=color, font=font_icon)
            draw.text((x + (btn_w - font_md.getlength(label))/2, y + 50), label, fill="white", font=font_md)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-70, 26, 60, 22, "BACK", bg_color=WARN_COLOR)

        list_y = 55
        item_h = 32
        max_items = 5
        display_list = self.files[self.scroll_offset : self.scroll_offset + max_items]

        if not self.files:
            draw.text((WIDTH//2 - 60, 100), "Thư mục trống!", fill="grey", font=font_md)
            return

        for i, item in enumerate(display_list):
            global_idx = self.scroll_offset + i
            is_sel = (global_idx == self.selected_idx)
            bg = "#585b70" if is_sel else BG_COLOR
            fg = "cyan" if is_sel else TEXT_COLOR
            name = item['name'] if isinstance(item, dict) else item
            draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=bg)
            draw.text((15, list_y + i*item_h + 6), f"{'>' if is_sel else ' '} {name[:28]}", fill=fg, font=font_md)

        if len(self.files) > max_items:
            sb_h = int((max_items / len(self.files)) * 140)
            sb_y = list_y + int((self.scroll_offset / (len(self.files) - max_items + 1)) * (140 - sb_h))
            draw.rectangle((WIDTH-6, sb_y, WIDTH, sb_y+sb_h), fill="#89b4fa")

        btn_y = 205
        self.draw_button(draw, 10, btn_y, 90, 30, "▲ LÊN")
        self.draw_button(draw, 115, btn_y, 90, 30, "CHỌN", bg_color="#a6e3a1", text_color="black")
        self.draw_button(draw, 220, btn_y, 90, 30, "▼ XUỐNG")

    def draw_player_ui(self, draw):
        self.draw_status_bar(draw)
        draw.text((20, 40), "Đang phát:", fill="grey", font=font_md)
        if self.files:
            song = self.files[self.selected_idx][:40]
            draw.text((20, 70), song, fill="yellow", font=font_lg)

        progress = (pygame.mixer.music.get_pos() / 1000) % 10 / 10
        draw.rectangle((40, 130, 280, 140), fill="#45475a")
        draw.rectangle((40, 130, 40 + 240*progress, 140), fill=ACCENT_COLOR)

        self.draw_button(draw, 20, 180, 70, 40, "VOL -")
        self.draw_button(draw, 100, 180, 70, 40, "VOL +")
        self.draw_button(draw, 180, 180, 70, 40, "PAUSE")
        self.draw_button(draw, 260, 180, 50, 40, "BACK")

    def draw_reader(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#f9e2af")
        if not self.book_content:
            draw.text((50, 100), "Không đọc được file!", fill="red", font=font_md)
        else:
            lines = self.book_content[self.book_page]
            y = 15
            for line in lines:
                draw.text((15, y), line.rstrip(), fill="#1e1e2e", font=font_md)
                y += 24

        draw.rectangle((0, 200, WIDTH, HEIGHT), fill="#313244")
        draw.text((100, 210), f"Trang {self.book_page+1}/{len(self.book_content)}", fill="white", font=font_sm)
        self.draw_button(draw, 10, 205, 90, 30, "<< TRƯỚC")
        self.draw_button(draw, 220, 205, 90, 30, "SAU >>")
        self.draw_button(draw, WIDTH-80, 5, 70, 30, "EXIT", bg_color=WARN_COLOR)

    def draw_video_playing(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="black")
        draw.text((50, 80), "Đang phát Video", fill="white", font=font_lg)
        draw.text((70, 120), "Chạm màn hình để dừng", fill="grey", font=font_md)

    def render(self):
        image = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(image)

        if self.state == "MENU":
            self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            titles = {"MUSIC": "Thư viện Nhạc", "VIDEO": "Video", "PHOTO": "Ảnh", "BOOK": "Sách", "BT": "Bluetooth"}
            self.draw_list(draw, titles.get(self.state, ""))
        elif self.state == "PLAYING_MUSIC":
            self.draw_player_ui(draw)
        elif self.state == "READING":
            self.draw_reader(draw)
        elif self.state == "PLAYING_VIDEO":
            self.draw_video_playing(draw)

        if self.state != "VIEWING_PHOTO":
            device.display(image)

    # --- XỬ LÝ FILE & MEDIA ---
    def load_files(self, type_key, exts):
        if not isinstance(exts, tuple):
            exts = (exts,)
        self.files = sorted([f for f in os.listdir(DIRS[type_key])
                             if f.lower().endswith(exts)])
        self.selected_idx = 0
        self.scroll_offset = 0

    def paginate_book(self, filename):
        path = os.path.join(DIRS["BOOK"], filename)
        self.book_content = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for i in range(0, len(lines), 9):
                    self.book_content.append(lines[i:i+9])
        except:
            self.book_content = []
        self.book_page = 0

    def scan_bt(self):
        self.bt_scanning = True
        img = Image.new("RGB", (WIDTH, HEIGHT), "black")
        d = ImageDraw.Draw(img)
        d.text((60, 100), "Đang quét Bluetooth...", fill="#89b4fa", font=font_lg)
        device.display(img)

        self.bt_devices = []
        try:
            subprocess.run(["bluetoothctl", "scan", "on"], timeout=6, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
            out = subprocess.check_output(["bluetoothctl", "devices"]).decode()
            for line in out.splitlines():
                if "Device" in line:
                    parts = line.split(" ", 2)
                    if len(parts) > 2:
                        self.bt_devices.append({"mac": parts[1], "name": parts[2]})
        except:
            pass
        subprocess.run(["bluetoothctl", "scan", "off"], stdout=subprocess.DEVNULL)

        self.files = self.bt_devices
        self.bt_scanning = False
        self.state = "BT"
        self.render()

    def play_video(self, filepath):
        self.state = "PLAYING_VIDEO"
        self.render()

        cmd = [
            "omxplayer",
            "--no-osd",
            "--aspect-mode", "fill",
            "--win", f"0 0 {WIDTH} {HEIGHT}",
            "--adev", "both",   # both = jack + HDMI, dùng "local" nếu chỉ jack
            "--vol", str(int(self.volume * 10 * 100)),  # omxplayer dùng millibel
            filepath
        ]

        try:
            self.video_process = subprocess.Popen(cmd)
            self.video_process.wait()  # Chờ video kết thúc
        except Exception as e:
            print(f"Video error: {e}")
        finally:
            if self.video_process:
                try:
                    self.video_process.terminate()
                except:
                    pass
            self.video_process = None
            self.state = "VIDEO"
            self.render()

    def show_photo(self, filepath):
        self.state = "VIEWING_PHOTO"
        try:
            img = Image.open(filepath)
            img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            device.display(img)

            while True:
                time.sleep(0.2)
                if touch.is_touched():
                    time.sleep(0.3)
                    break
        except Exception as e:
            print(e)
        finally:
            self.state = "PHOTO"
            self.render()

    # --- XỬ LÝ CẢM ỨNG ---
    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3:
            return
        self.last_touch = now

        if self.state == "MENU":
            btn_w, btn_h = 100, 80
            gap_x, gap_y = 30, 25
            total_w = 2 * btn_w + gap_x
            start_x = (WIDTH - total_w) / 2
            start_y = 70

            col = int((x - start_x) // (btn_w + gap_x)) if x >= start_x else -1
            row = int((y - start_y) // (btn_h + gap_y)) if y >= start_y else -1

            if 0 <= col <= 1 and 0 <= row <= 2:
                idx = row * 2 + col
                actions = [
                    lambda: (setattr(self, "state", "MUSIC"), self.load_files("MUSIC", ('.mp3', '.wav', '.flac'))),
                    lambda: (setattr(self, "state", "VIDEO"), self.load_files("VIDEO", ('.mp4', '.avi', '.mkv'))),
                    lambda: (setattr(self, "state", "PHOTO"), self.load_files("PHOTO", ('.jpg', '.png', '.jpeg', '.bmp'))),
                    lambda: (setattr(self, "state", "BOOK"), self.load_files("BOOK", ('.txt',))),
                    lambda: threading.Thread(target=self.scan_bt).start()
                ]
                if idx < len(actions):
                    actions[idx]()
                    self.render()

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            if x > WIDTH - 70 and y < 50:  # BACK
                pygame.mixer.music.stop()
                self.state = "MENU"
                self.render()
                return

            if y > 200:
                if x < 105:
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset:
                        self.scroll_offset = self.selected_idx
                elif x > 215:
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5:
                        self.scroll_offset += 1
                else:  # CHỌN
                    if not self.files:
                        return
                    item = self.files[self.selected_idx]
                    name = item['name'] if isinstance(item, dict) else item
                    full_path = os.path.join(DIRS[self.state], name) if self.state != "BT" else None

                    if self.state == "MUSIC":
                        try:
                            pygame.mixer.music.load(full_path)
                            pygame.mixer.music.set_volume(self.volume)
                            pygame.mixer.music.play(-1)  # loop
                            self.state = "PLAYING_MUSIC"
                        except:
                            pass

                    elif self.state == "VIDEO":
                        threading.Thread(target=self.play_video, args=(full_path,)).start()
                        return

                    elif self.state == "PHOTO":
                        self.show_photo(full_path)
                        return

                    elif self.state == "BOOK":
                        self.paginate_book(name)
                        self.state = "READING"

                    elif self.state == "BT":
                        subprocess.run(["bluetoothctl", "connect", item['mac']])
                        time.sleep(2)
                        self.state = "MENU"

                self.render()

        elif self.state == "PLAYING_MUSIC":
            if y > 170:
                if x < 90:
                    self.volume = max(0.0, self.volume - 0.1)
                elif x < 170:
                    self.volume = min(1.0, self.volume + 0.1)
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
            if x > WIDTH - 80 and y < 40:  # EXIT
                self.state = "BOOK"
                self.render()
                return
            if y > 200:
                if x < 105:
                    self.book_page = max(0, self.book_page - 1)
                elif x > 215:
                    self.book_page = min(len(self.book_content)-1, self.book_page + 1)
                self.render()

        elif self.state == "PLAYING_VIDEO":
            if touch.is_touched():  # Bất kỳ chạm nào cũng dừng video
                if self.video_process:
                    self.video_process.terminate()
                time.sleep(0.5)
                self.state = "VIDEO"
                self.render()

    def run(self):
        self.render()
        while self.running:
            pt = touch.get_touch()
            if pt:
                self.handle_touch(*pt)
            time.sleep(0.05)

# ==========================================
# 4. KHỞI CHẠY
# ==========================================
if __name__ == "__main__":
    def cleanup(sig, frame):
        print("\nĐang thoát...")
        pygame.mixer.quit()
        if hasattr(app, 'video_process') and app.video_process:
            app.video_process.terminate()
        os.system("pkill -9 omxplayer.bin 2>/dev/null")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    app = PiMediaCenter()
    app.run()
# 1. CẤU HÌNH HỆ THỐNG
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
# 2. KHỞI TẠO PHẦN CỨNG (LCD + TOUCH)
# ==========================================
try:
    # LCD ST7789 (dùng SPI0 chính của Pi)
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    device.backlight(True)

    # Touch XPT2046 (dùng SPI1 phụ - cần bật SPI1 trong raspi-config)
    spi_touch = busio.SPI(clock=21, MOSI=20, MISO=19)  # BCM: SCLK=21, MOSI=20, MISO=19
    while not spi_touch.try_lock():
        pass
    spi_touch.configure(baudrate=2000000)

    cs_pin = digitalio.DigitalInOut(17)   # BCM 17
    cs_pin.direction = digitalio.Direction.OUTPUT
    cs_pin.value = True

    irq_pin = digitalio.DigitalInOut(26)  # BCM 26
    irq_pin.direction = digitalio.Direction.INPUT
    irq_pin.pull = digitalio.Pull.UP

except Exception as e:
    print(f"Hardware Error: {e}")
    print("Kiểm tra:")
    print("  - Đã bật SPI trong raspi-config?")
    print("  - Đã thêm dtoverlay=spi1-3cs vào /boot/config.txt và reboot?")
    print("  - Đã cài adafruit-blinka: sudo pip3 install adafruit-blinka")
    sys.exit(1)

# ==========================================
# 3. DRIVER TOUCH XPT2046
# ==========================================
class XPT2046:
    CMD_X = 0x90
    CMD_Y = 0xD0

    def __init__(self, spi, cs_pin, irq_pin, width=320, height=240,
                 x_min=100, x_max=1962, y_min=100, y_max=1900):
        self.spi = spi
        self.cs = cs_pin
        self.irq = irq_pin
        self.width = width
        self.height = height

        self.x_mult = width / (x_max - x_min)
        self.x_add = -x_min * self.x_mult
        self.y_mult = height / (y_max - y_min)
        self.y_add = -y_min * self.y_mult

        self._tx_buf = bytearray(3)
        self._rx_buf = bytearray(3)

    def is_touched(self):
        return not self.irq.value

    def _read(self, cmd):
        self._tx_buf[0] = cmd
        self._tx_buf[1] = 0
        self._tx_buf[2] = 0

        self.cs.value = False
        self.spi.write_readinto(self._tx_buf, self._rx_buf)
        self.cs.value = True

        return ((self._rx_buf[1] << 8) | self._rx_buf[2]) >> 4

    def get_touch(self):
        if not self.is_touched():
            return None

        samples = []
        for _ in range(10):
            if not self.is_touched():
                return None
            x = self._read(self.CMD_X)
            y = self._read(self.CMD_Y)
            if 0 < x < 4095 and 0 < y < 4095:
                samples.append((x, y))
            time.sleep(0.001)

        if len(samples) < 5:
            return None

        samples.sort()
        samples = samples[2:-2]

        avg_x = sum(s[0] for s in samples) // len(samples)
        avg_y = sum(s[1] for s in samples) // len(samples)

        px = int(avg_x * self.x_mult + self.x_add)
        py = int(avg_y * self.y_mult + self.y_add)

        px = max(0, min(px, self.width - 1))
        py = max(0, min(py, self.height - 1))

        return (px, py)

# Tạo touch
touch = XPT2046(spi_touch, cs_pin, irq_pin, WIDTH, HEIGHT)

pygame.mixer.init()

# ==========================================
# 4. CLASS MEDIA CENTER
# ==========================================
class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.running = True
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.last_touch = 0

        self.bt_devices = []
        self.book_content = []
        self.book_page = 0
        self.volume = 0.5

        self.video_stop_event = threading.Event()
        self.audio_proc = None

    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 40, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=5, fill=bg_color)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x + (w - tw)//2, y + (h - th)//2 - 2), text, fill=text_color, font=font_md)

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        title = "PI MEDIA CENTER"
        bbox = draw.textbbox((0,0), title, font=font_lg)
        draw.text(((WIDTH - (bbox[2]-bbox[0]))//2, 35), title, fill=ACCENT_COLOR, font=font_lg)

        items = [
            ("Music", "♪", "#f9e2af"), ("Video", "▶", "#f38ba8"),
            ("Photo", "▣", "#a6e3a1"), ("Books", "📖", "#89b4fa"),
            ("Bluetooth", "BT", "#cba6f7")
        ]

        start_y = 70
        btn_w, btn_h = 90, 70
        gap = 20
        start_x = (WIDTH - (btn_w * 3 + gap * 2)) // 2

        for i, (label, icon, color) in enumerate(items):
            row = i // 3
            col = i % 3
            x = start_x + col * (btn_w + gap)
            y = start_y + row * (btn_h + gap)
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=8, fill="#313244", outline=color, width=2)
            draw.text((x + 35, y + 10), icon, fill=color, font=font_icon)
            draw.text((x + (btn_w - font_sm.getlength(label))//2, y + 45), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR)

        list_y = 55
        item_h = 30
        max_items = 5
        display_list = self.files[self.scroll_offset:self.scroll_offset + max_items]

        if not self.files:
            draw.text((WIDTH//2 - 50, 100), "Trống / Empty", fill="grey", font=font_md)
            return

        for i, item in enumerate(display_list):
            idx = self.scroll_offset + i
            selected = idx == self.selected_idx
            bg = "#585b70" if selected else BG_COLOR
            fg = "cyan" if selected else "white"
            name = item['name'] if isinstance(item, dict) else item
            draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill=bg)
            draw.text((10, list_y + i*item_h + 5), f"{'>' if selected else ' '} {name[:28]}", fill=fg, font=font_md)

        if len(self.files) > max_items:
            sb_h = int(max_items / len(self.files) * 140)
            sb_y = list_y + int(self.scroll_offset / len(self.files) * 140)
            draw.rectangle((WIDTH-5, sb_y, WIDTH, sb_y + sb_h), fill="grey")

        btn_y = 205
        self.draw_button(draw, 10, btn_y, 90, 30, "▲ LÊN")
        self.draw_button(draw, 115, btn_y, 90, 30, "CHỌN ●", bg_color="#a6e3a1", text_color="black")
        self.draw_button(draw, 220, btn_y, 90, 30, "▼ XUỐNG")

    def draw_player_ui(self, draw):
        self.draw_status_bar(draw)
        draw.text((20, 40), "Now Playing:", fill="grey", font=font_sm)
        if self.files:
            name = self.files[self.selected_idx]
            draw.text((20, 60), name[:28], fill="yellow", font=font_lg)
            draw.text((20, 85), name[28:56], fill="yellow", font=font_lg)

        draw.rectangle((40, 120, 280, 130), fill="#45475a")
        import math
        prog = (math.sin(time.time() * 3) + 1) / 2
        draw.rectangle((40, 120, 40 + int(240 * prog), 130), fill=ACCENT_COLOR)

        self.draw_button(draw, 10, 180, 70, 40, "VOL-")
        self.draw_button(draw, 90, 180, 70, 40, "VOL+")
        self.draw_button(draw, 170, 180, 80, 40, "PAUSE/PLAY")
        self.draw_button(draw, 260, 180, 50, 40, "BACK")

    def draw_reader(self, draw):
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill="#0d0d0d")
        if not self.book_content:
            draw.text((10, 100), "Lỗi đọc file!", fill="red", font=font_md)
        else:
            lines = self.book_content[self.book_page]
            y = 15
            for line in lines:
                draw.text((15, y), line.rstrip(), fill="#f0f0f0", font=font_md)
                y += 24

        draw.line((0, 200, WIDTH, 200), fill="#555555")
        draw.text((130, 210), f"{self.book_page+1}/{len(self.book_content)}", fill="cyan", font=font_sm)
        self.draw_button(draw, 5, 205, 70, 30, "<< PREV")
        self.draw_button(draw, 245, 205, 70, 30, "NEXT >>")
        self.draw_button(draw, WIDTH - 75, 5, 70, 30, "EXIT", bg_color=WARN_COLOR)

    def render(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        if self.state == "MENU":
            self.draw_menu(draw)
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            titles = {"MUSIC": "Music", "VIDEO": "Video", "PHOTO": "Photo", "BOOK": "Books", "BT": "Bluetooth"}
            self.draw_list(draw, titles[self.state])
        elif self.state == "PLAYING_MUSIC":
            self.draw_player_ui(draw)
        elif self.state == "READING":
            self.draw_reader(draw)

        if self.state not in ["PLAYING_VIDEO", "VIEWING_PHOTO"]:
            device.display(img)

    def load_files(self, key, exts):
        path = DIRS[key]
        self.files = sorted([f for f in os.listdir(path) if f.lower().endswith(exts)])
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
            pass
        self.book_page = 0

    def scan_bt(self):
        self.bt_devices = []
        img = Image.new("RGB", (WIDTH, HEIGHT), "black")
        d = ImageDraw.Draw(img)
        d.text((70, 100), "Scanning Bluetooth...", fill="lime", font=font_md)
        device.display(img)

        try:
            subprocess.run(["bluetoothctl", "scan", "on"], timeout=6)
            out = subprocess.check_output(["bluetoothctl", "devices"]).decode()
            for line in out.splitlines():
                if "Device" in line:
                    parts = line.split(" ", 2)
                    if len(parts) > 2:
                        self.bt_devices.append({"mac": parts[1], "name": parts[2]})
        except:
            pass

        self.files = self.bt_devices
        self.state = "BT"
        self.render()

    def play_video_stream(self, filepath):
        self.state = "PLAYING_VIDEO"
        self.video_stop_event.clear()

        if self.audio_proc:
            self.audio_proc.terminate()
        os.system("pkill -9 ffmpeg ffplay")

        self.audio_proc = subprocess.Popen(
            ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', filepath],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        cmd = [
            'ffmpeg', '-i', filepath,
            '-vf', f'scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-'
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3*10)
        frame_size = WIDTH * HEIGHT * 3

        try:
            while not self.video_stop_event.is_set():
                if touch.is_touched():
                    time.sleep(0.1)
                    break
                raw = proc.stdout.read(frame_size)
                if len(raw) != frame_size:
                    break
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw)
                device.display(img)
                time.sleep(0.033)
        except:
            pass
        finally:
            proc.terminate()
            if self.audio_proc:
                self.audio_proc.terminate()
                self.audio_proc = None
            os.system("pkill -9 ffmpeg ffplay")
            self.state = "VIDEO"
            self.render()

    def show_photo(self, filepath):
        self.state = "VIEWING_PHOTO"
        try:
            img = Image.open(filepath)
            img = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            device.display(img)
            while True:
                time.sleep(0.1)
                if touch.is_touched():
                    time.sleep(0.2)
                    break
        except:
            pass
        self.state = "PHOTO"
        self.render()

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3:
            return
        self.last_touch = now

        if self.state == "MENU":
            start_y = 70
            btn_w, btn_h = 90, 70
            gap = 20
            start_x = (WIDTH - (btn_w * 3 + gap * 2)) // 2
            col = row = -1
            if start_y <= y < start_y + btn_h*2 + gap:
                if start_x <= x < start_x + btn_w: col = 0
                elif start_x + btn_w + gap <= x < start_x + 2*(btn_w + gap): col = 1
                elif start_x + 2*(btn_w + gap) <= x < start_x + 3*(btn_w + gap): col = 2
                if start_y <= y < start_y + btn_h: row = 0
                elif start_y + btn_h + gap <= y < start_y + 2*btn_h + gap: row = 1

            if row >= 0 and col >= 0:
                idx = row * 3 + col
                actions = [
                    ("MUSIC", ('.mp3','.wav','.flac')),
                    ("VIDEO", ('.mp4','.mkv','.avi')),
                    ("PHOTO", ('.jpg','.jpeg','.png','.bmp')),
                    ("BOOK", ('.txt',)),
                    ("BT", None)
                ]
                if idx < len(actions):
                    key, exts = actions[idx]
                    if key == "BT":
                        threading.Thread(target=self.scan_bt, daemon=True).start()
                    else:
                        self.state = key
                        self.load_files(key, exts)
                    self.render()

        elif self.state in ["MUSIC","VIDEO","PHOTO","BOOK","BT"]:
            if x > WIDTH-70 and y < 50:  # BACK
                self.state = "MENU"
                pygame.mixer.music.stop()
                self.render()
                return

            if y > 200:
                if x < 100:
                    self.selected_idx = max(0, self.selected_idx - 1)
                    if self.selected_idx < self.scroll_offset:
                        self.scroll_offset = self.selected_idx
                elif x > 220:
                    self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                    if self.selected_idx >= self.scroll_offset + 5:
                        self.scroll_offset += 1
                else:
                    if not self.files: return
                    item = self.files[self.selected_idx]
                    if self.state == "MUSIC":
                        path = os.path.join(DIRS["MUSIC"], item)
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.set_volume(self.volume)
                        pygame.mixer.music.play()
                        self.state = "PLAYING_MUSIC"
                    elif self.state == "VIDEO":
                        path = os.path.join(DIRS["VIDEO"], item)
                        threading.Thread(target=self.play_video_stream, args=(path,), daemon=True).start()
                        return
                    elif self.state == "PHOTO":
                        path = os.path.join(DIRS["PHOTO"], item)
                        self.show_photo(path)
                        return
                    elif self.state == "BOOK":
                        self.paginate_book(item)
                        self.state = "READING"
                    elif self.state == "BT":
                        subprocess.run(["bluetoothctl", "connect", item['mac']])
                self.render()

        elif self.state == "PLAYING_MUSIC":
            if y > 170:
                if x < 80:
                    self.volume = max(0.0, self.volume - 0.1)
                elif x < 160:
                    self.volume = min(1.0, self.volume + 0.1)
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
            elif y > 200:
                if x < 100:
                    self.book_page = max(0, self.book_page - 1)
                elif x > 220:
                    self.book_page = min(len(self.book_content)-1, self.book_page + 1)
                self.render()

        elif self.state == "PLAYING_VIDEO":
            self.video_stop_event.set()

        elif self.state == "VIEWING_PHOTO":
            self.state = "PHOTO"
            self.render()

    def run(self):
        self.render()
        while self.running:
            pt = touch.get_touch()
            if pt:
                self.handle_touch(pt[0], pt[1])
            time.sleep(0.05)

# ==========================================
# 5. CHẠY ỨNG DỤNG
# ==========================================
if __name__ == "__main__":
    def cleanup(sig=None, frame=None):
        pygame.mixer.quit()
        os.system("pkill -9 ffmpeg ffplay")
        spi_touch.unlock()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    app = PiMediaCenter()
    app.run()
