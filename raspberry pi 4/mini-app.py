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
from xpt2046 import XPT2046  # Đảm bảo file xpt2046 (1).py được đổi tên thành xpt2046.py 

# --- 1. CẤU HÌNH HỆ THỐNG ---
WIDTH, HEIGHT = 320, 240
BG_COLOR = "#1e1e2e"       
ACCENT_COLOR = "#89b4fa"   
WARN_COLOR = "#f38ba8"     

USER_HOME = "/home/dinhphuc"
DIRS = {
    "MUSIC": os.path.join(USER_HOME, "Music"),
    "VIDEO": os.path.join(USER_HOME, "Videos"),
    "PHOTO": os.path.join(USER_HOME, "Pictures"),
    "BOOK":  os.path.join(USER_HOME, "Documents")
}
for d in DIRS.values(): os.makedirs(d, exist_ok=True)

def get_fonts():
    try:
        # Ưu tiên font hệ thống nếu có
        return (ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18),
                ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14),
                ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10))
    except:
        return (ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default())

font_lg, font_md, font_sm = get_fonts()

# --- 2. KHỞI TẠO PHẦN CỨNG ---
try:
    # Khởi tạo màn hình ST7789 
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
    
    # Khởi tạo cảm ứng XPT2046 
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900, 
                    baudrate=1000000)
except Exception as e:
    print(f"Lỗi khởi tạo phần cứng: {e}")
    sys.exit(1)

pygame.mixer.init()

# --- 3. LỚP ĐIỀU KHIỂN CHÍNH ---
class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.volume = 0.5
        self.book_content = []
        self.book_page = 0
        self.bt_devices = []
        self.last_touch_time = 0
        self.is_running = True

    def draw_ui(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Thanh trạng thái (Status Bar)
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)
        draw.text((WIDTH-45, 5), datetime.datetime.now().strftime("%H:%M"), fill="white", font=font_sm)

        if self.state == "MENU":
            draw.text((WIDTH//2 - 70, 40), "PI MEDIA CENTER", fill=ACCENT_COLOR, font=font_lg)
            menus = ["Bluetooth", "Music", "Video", "Photos", "Books"]
            for i, m in enumerate(menus):
                draw.rounded_rectangle((40, 70+i*32, 280, 98+i*32), radius=5, fill="#45475a")
                draw.text((60, 75+i*32), m, fill="white", font=font_md)

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            draw.text((10, 30), f"Danh mục: {self.state}", fill="yellow", font=font_md)
            # Nút BACK
            draw.rounded_rectangle((WIDTH-65, 28, WIDTH-5, 50), radius=5, fill=WARN_COLOR)
            draw.text((WIDTH-55, 32), "BACK", fill="white", font=font_sm)
            
            items = self.bt_devices if self.state == "BT" else self.files
            for i in range(5):
                idx = self.scroll_offset + i
                if idx < len(items):
                    name = items[idx]['name'] if isinstance(items[idx], dict) else items[idx]
                    color = "cyan" if idx == self.selected_idx else "white"
                    draw.text((20, 60+i*28), f"{'>' if idx==self.selected_idx else ' '} {name[:28]}", fill=color, font=font_md)
            
            # Nút điều hướng
            draw.rounded_rectangle((10, 205, 100, 235), radius=5, fill="#45475a")
            draw.text((40, 210), "LÊN", font=font_md)
            draw.rounded_rectangle((110, 205, 210, 235), radius=5, fill="#a6e3a1")
            draw.text((140, 210), "OK", fill="black", font=font_md)
            draw.rounded_rectangle((220, 205, 310, 235), radius=5, fill="#45475a")
            draw.text((245, 210), "XUỐNG", font=font_md)

        device.display(img)

    def handle_touch(self, x, y):
        """Xử lý sự kiện chạm thông qua tọa độ """
        if time.time() - self.last_touch_time < 0.3: return
        self.last_touch_time = time.time()

        if self.state == "MENU":
            if 40 <= x <= 280:
                idx = (y - 70) // 32
                if idx == 0: self.state = "BT"; self.scan_bt()
                elif idx == 1: self.state = "MUSIC"; self.load_files("MUSIC", (".mp3", ".wav"))
                elif idx == 2: self.state = "VIDEO"; self.load_files("VIDEO", (".mp4",))
                elif idx == 3: self.state = "PHOTO"; self.load_files("PHOTO", (".jpg", ".png"))
                elif idx == 4: self.state = "BOOK"; self.load_files("BOOK", (".txt",))
        
        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT"]:
            # Xử lý nút BACK
            if x > WIDTH-70 and y < 60: 
                self.state = "MENU"
                pygame.mixer.music.stop()
                os.system("pkill -9 ffplay") # Dọn dẹp tiến trình video 
            elif y > 200:
                items = self.bt_devices if self.state == "BT" else self.files
                if not items: return
                if x < 110: # LÊN
                    self.selected_idx = (self.selected_idx - 1) % len(items)
                elif x > 210: # XUỐNG
                    self.selected_idx = (self.selected_idx + 1) % len(items)
                else: # OK
                    self.execute_action()
        self.draw_ui()

    def load_files(self, key, ext):
        self.files = sorted([f for f in os.listdir(DIRS[key]) if f.lower().endswith(ext)])
        self.selected_idx = 0
        self.scroll_offset = 0

    def scan_bt(self):
        """Quét thiết bị Bluetooth dùng bluetoothctl """
        self.bt_devices = []
        def _task():
            try:
                subprocess.run(["bluetoothctl", "scan", "on"], timeout=5, stdout=subprocess.DEVNULL)
                out = subprocess.check_output(["bluetoothctl", "devices"]).decode("utf-8")
                for line in out.split('\n'):
                    if "Device" in line:
                        p = line.split(' ', 2)
                        if len(p) > 2: self.bt_devices.append({"mac": p[1], "name": p[2]})
            except: pass
            self.draw_ui()
        threading.Thread(target=_task).start()

    def execute_action(self):
        """Thực hiện hành động dựa trên mục được chọn [cite: 1, 2]"""
        items = self.bt_devices if self.state == "BT" else self.files
        if not items: return
        item = items[self.selected_idx]

        if self.state == "MUSIC":
            path = os.path.join(DIRS["MUSIC"], item)
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
        
        elif self.state == "VIDEO":
            path = os.path.join(DIRS["VIDEO"], item)
            # Khởi chạy video thông qua ffplay để có âm thanh 
            os.system(f"ffplay -nodisp -autoexit -loglevel quiet '{path}' &")
        
        elif self.state == "BT":
            # Kết nối Bluetooth 
            mac = item['mac']
            subprocess.run(["bluetoothctl", "connect", mac])

    def run(self):
        """Vòng lặp điều khiển chính dùng poll() """
        touch.set_handler(self.handle_touch)
        self.draw_ui()
        try:
            while self.is_running:
                touch.poll() # Hàm này sẽ tự động kích hoạt callback handle_touch khi có chạm 
                time.sleep(0.05)
        except KeyboardInterrupt:
            pygame.mixer.quit()
            os.system("pkill -9 ffplay")
            sys.exit(0)

if __name__ == "__main__":
    app = PiMediaCenter()
    app.run()
