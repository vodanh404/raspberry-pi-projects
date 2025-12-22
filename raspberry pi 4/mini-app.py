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
from xpt2046 import XPT2046 # Sử dụng file xpt2046.py của bạn

# --- 1. CẤU HÌNH ---
WIDTH, HEIGHT = 320, 240
BG_COLOR = "#1e1e2e"       
ACCENT_COLOR = "#89b4fa"   
DIRS = {
    "MUSIC": "/home/dinhphuc/Music",
    "VIDEO": "/home/dinhphuc/Videos",
    "PHOTO": "/home/dinhphuc/Pictures",
    "BOOK":  "/home/dinhphuc/Documents"
}
for d in DIRS.values(): os.makedirs(d, exist_ok=True)

def get_fonts():
    try:
        return (ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18),
                ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14))
    except:
        return (ImageFont.load_default(), ImageFont.load_default())

font_lg, font_md = get_fonts()

# --- 2. KHỞI TẠO PHẦN CỨNG ---
try:
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    # Khởi tạo cảm ứng theo đúng tham số thư viện của bạn
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900, 
                    baudrate=1000000)
except Exception as e:
    print(f"Hardware Error: {e}"); sys.exit(1)

pygame.mixer.init()

# --- 3. CLASS TRUNG TÂM ---
class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.book_content = []
        self.book_page = 0
        self.bt_devices = []
        self.last_touch = 0

    def draw_ui(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Status Bar
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        draw.text((WIDTH-50, 4), datetime.datetime.now().strftime("%H:%M"), fill="white")

        if self.state == "MENU":
            draw.text((WIDTH//2 - 70, 40), "PI MEDIA CENTER", fill=ACCENT_COLOR, font=font_lg)
            menus = ["Bluetooth", "Music", "Video", "Photos", "Books"]
            for i, m in enumerate(menus):
                draw.rounded_rectangle((40, 70+i*32, 280, 98+i*32), radius=5, fill="#45475a")
                draw.text((60, 75+i*32), m, fill="white", font=font_md)

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            draw.text((10, 30), f"List: {self.state}", fill="yellow", font=font_md)
            draw.rounded_rectangle((WIDTH-60, 26, WIDTH-5, 48), radius=5, fill="#f38ba8")
            draw.text((WIDTH-55, 30), "BACK", fill="white")
            
            items = self.bt_devices if self.state == "BT" else self.files
            for i in range(5):
                idx = self.scroll_offset + i
                if idx < len(items):
                    name = items[idx]['name'] if isinstance(items[idx], dict) else items[idx]
                    color = "cyan" if idx == self.selected_idx else "white"
                    draw.text((20, 60+i*28), f"{'>' if idx==self.selected_idx else ' '} {name[:28]}", fill=color, font=font_md)
            
            # Nav buttons
            for i, btn in enumerate(["UP", "OK", "DOWN"]):
                draw.rounded_rectangle((10+i*105, 205, 100+i*105, 235), radius=5, fill="#45475a")
                draw.text((35+i*105, 212), btn, fill="white")

        device.display(img)

    def handle_touch(self, x, y):
        if time.time() - self.last_touch < 0.3: return
        self.last_touch = time.time()

        if self.state == "MENU":
            if 40 <= x <= 280:
                idx = (y - 70) // 32
                if idx == 0: self.state = "BT"; self.scan_bt()
                elif idx == 1: self.state = "MUSIC"; self.load_files("MUSIC", (".mp3", ".wav"))
                elif idx == 2: self.state = "VIDEO"; self.load_files("VIDEO", (".mp4",))
                elif idx == 3: self.state = "PHOTO"; self.load_files("PHOTO", (".jpg", ".png"))
                elif idx == 4: self.state = "BOOK"; self.load_files("BOOK", (".txt",))
        
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            if x > WIDTH-60 and y < 60: 
                self.state = "MENU"; pygame.mixer.music.stop(); os.system("pkill -9 ffplay")
            elif y > 200:
                items = self.bt_devices if self.state == "BT" else self.files
                if x < 110: self.selected_idx = max(0, self.selected_idx - 1)
                elif x > 210: self.selected_idx = min(len(items)-1, self.selected_idx + 1)
                else: self.execute_action()
        self.draw_ui()

    def load_files(self, key, ext):
        self.files = sorted([f for f in os.listdir(DIRS[key]) if f.lower().endswith(ext)])
        self.selected_idx = 0; self.scroll_offset = 0

    def scan_bt(self):
        self.bt_devices = []
        def _task():
            subprocess.run(["bluetoothctl", "scan", "on"], timeout=4, stdout=subprocess.DEVNULL)
            out = subprocess.check_output(["bluetoothctl", "devices"]).decode("utf-8")
            for line in out.split('\n'):
                if "Device" in line:
                    p = line.split(' ', 2)
                    if len(p) > 2: self.bt_devices.append({"mac": p[1], "name": p[2]})
            self.draw_ui()
        threading.Thread(target=_task).start()

    def execute_action(self):
        items = self.bt_devices if self.state == "BT" else self.files
        if not items: return
        item = items[self.selected_idx]

        if self.state == "MUSIC":
            pygame.mixer.music.load(os.path.join(DIRS["MUSIC"], item))
            pygame.mixer.music.play()
        elif self.state == "VIDEO":
            path = os.path.join(DIRS["VIDEO"], item)
            # Dùng ffplay chạy ngầm để phát cả hình và tiếng
            os.system(f"ffplay -autoexit -loglevel quiet '{path}' &")
        elif self.state == "BT":
            subprocess.run(["bluetoothctl", "connect", item['mac']])

    def run(self):
        touch.set_handler(self.handle_touch)
        self.draw_ui()
        try:
            while True:
                touch.poll() # Hàm poll của thư viện bạn sẽ tự gọi handle_touch
                time.sleep(0.05)
        except KeyboardInterrupt:
            pygame.mixer.quit(); sys.exit(0)

if __name__ == "__main__":
    app = PiMediaCenter()
    app.run()
