import os
import time
import subprocess
import threading
import pygame
import board
import busio
import sys
import signal
from PIL import Image, ImageFont, ImageDraw
from luma.core.interface.serial import spi as luma_spi
from luma.lcd.device import st7789
from xpt2046 import XPT2046

# --- 1. CẤU HÌNH PHẦN CỨNG ---
WIDTH, HEIGHT = 320, 240
serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=40000000)
device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")

try:
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    # Khởi tạo cảm ứng dựa trên file xpt2046.py [cite: 1]
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                   width=WIDTH, height=HEIGHT, x_min=100, x_max=1962,
                   y_min=100, y_max=1900, baudrate=1000000)
except Exception as e:
    print(f"Lỗi cảm ứng: {e}")
    sys.exit(1)

# --- 2. BIẾN HỆ THỐNG ---
USER_PATH = "/home/dinhphuc"
PATHS = {
    "MUSIC": os.path.join(USER_PATH, "Music"),
    "VIDEO": os.path.join(USER_PATH, "Videos"),
    "PHOTO": os.path.join(USER_PATH, "Pictures"),
    "BOOK": os.path.join(USER_PATH, "Documents")
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

current_state = "MENU"
current_index = 0
files_list = []
bt_devices = []
last_touch_time = 0
current_book_text = ""

# Khởi tạo font và audio [cite: 1, 2]
def get_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

font_s, font_m, font_l = get_font(14), get_font(18), get_font(24)
pygame.mixer.init()

# --- 3. LOGIC XỬ LÝ BLUETOOTH & BOOK ---

def scan_bluetooth():
    global bt_devices, current_state
    bt_devices = []
    draw_msg("Đang quét Bluetooth...", "Vui lòng chờ 5 giây...")
    try:
        # Sử dụng bluetoothctl để quét thiết bị [cite: 4, 5]
        subprocess.run(["bluetoothctl", "scan", "on"], timeout=5, stdout=subprocess.DEVNULL)
        out = subprocess.check_output(["bluetoothctl", "devices"]).decode("utf-8")
        for line in out.split('\n'):
            if "Device" in line:
                parts = line.split(' ', 2)
                if len(parts) > 2:
                    bt_devices.append({"mac": parts[1], "name": parts[2]})
    except: pass
    current_state = "BT_LIST"
    ui_refresh()

def load_book_content(filename):
    global current_book_text
    path = os.path.join(PATHS["BOOK"], filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            current_book_text = f.read(1000) # Đọc 1000 ký tự đầu
    except:
        current_book_text = "Không thể đọc nội dung file này."

# --- 4. GIAO DIỆN (UI) ---

def draw_button(draw, x, y, w, h, text, bg="#262626", fg="white"):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=5, outline="white", fill=bg)
    bbox = draw.textbbox((0, 0), text, font=font_s)
    draw.text((x + (w-(bbox[2]-bbox[0]))/2, y + (h-(bbox[3]-bbox[1]))/2), text, fill=fg, font=font_s)

def draw_header(draw, title):
    draw.rectangle((0, 0, WIDTH, 40), fill="#1A1A1A")
    draw.text((10, 10), title, fill="yellow", font=font_m)
    draw_button(draw, 250, 5, 65, 30, "BACK", bg="#8B0000")

def draw_msg(line1, line2=""):
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        draw.text((20, 100), line1, fill="yellow", font=font_m)
        draw.text((20, 130), line2, fill="white", font=font_s)
        device.display(img)

def ui_refresh():
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        
        if current_state == "MENU":
            draw.text((80, 10), "PI MEDIA CENTER", fill="#00FF00", font=font_l)
            # Danh sách Menu đầy đủ 5 mục [cite: 2]
            menu_items = ["Bluetooth", "Music", "Video", "Photos", "Books"]
            for i, item in enumerate(menu_items):
                draw_button(draw, 40, 50 + i*35, 240, 30, item)
        
        elif current_state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT_LIST"]:
            title = current_state.replace("_LIST", "")
            draw_header(draw, title)
            items = bt_devices if current_state == "BT_LIST" else files_list
            
            if not items:
                draw.text((80, 100), "Danh sách trống", fill="red", font=font_m)
            else:
                for i, item in enumerate(items[0:4]):
                    name = item['name'] if isinstance(item, dict) else item
                    color = "cyan" if i == current_index else "white"
                    draw.text((10, 50 + i*35), f"{'>' if i==current_index else ' '} {name[:28]}", fill=color, font=font_s)
                
                draw_button(draw, 20, 200, 80, 35, "LÊN")
                draw_button(draw, 120, 200, 80, 35, "CHỌN")
                draw_button(draw, 220, 200, 80, 35, "XUỐNG")

        elif current_state == "READING":
            draw_header(draw, "ĐỌC SÁCH")
            lines = [current_book_text[i:i+40] for i in range(0, 400, 40)]
            for i, line in enumerate(lines):
                draw.text((10, 50 + i*20), line, fill="white", font=font_s)

        device.display(img)

# --- 5. XỬ LÝ CẢM ỨNG ---

def touch_callback(x, y):
    global current_state, current_index, files_list, last_touch_time, bt_devices
    if time.time() - last_touch_time < 0.4: return
    last_touch_time = time.time()

    # Nút BACK chung
    if x > 240 and y < 45 and current_state != "MENU":
        os.system("pkill -9 ffplay")
        pygame.mixer.music.stop()
        current_state = "MENU"
        ui_refresh()
        return

    if current_state == "MENU":
        if 40 <= x <= 280:
            idx = (y - 50) // 35
            # Sửa logic: Gán đúng trạng thái cho từng nút 
            if idx == 0: # Bluetooth
                current_state = "BT_SCAN"
                threading.Thread(target=scan_bluetooth).start()
                return
            elif idx == 1: # Music
                current_state = "MUSIC"
                files_list = sorted([f for f in os.listdir(PATHS["MUSIC"]) if f.endswith(('.mp3', '.wav'))])
            elif idx == 2: # Video
                current_state = "VIDEO"
                files_list = sorted([f for f in os.listdir(PATHS["VIDEO"]) if f.endswith('.mp4')])
            elif idx == 3: # Photo
                current_state = "PHOTO"
                files_list = sorted([f for f in os.listdir(PATHS["PHOTO"]) if f.lower().endswith(('.jpg', '.png'))])
            elif idx == 4: # Book
                current_state = "BOOK"
                files_list = sorted([f for f in os.listdir(PATHS["BOOK"]) if f.endswith('.txt')])
            
            current_index = 0
            ui_refresh()

    elif current_state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT_LIST"]:
        items = bt_devices if current_state == "BT_LIST" else files_list
        if not items: return

        if y > 190:
            if 20 <= x <= 100: current_index = (current_index - 1) % len(items) # LÊN
            elif 220 <= x <= 300: current_index = (current_index + 1) % len(items) # XUỐNG
            elif 120 <= x <= 200: # CHỌN
                if current_state == "MUSIC":
                    pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], files_list[current_index]))
                    pygame.mixer.music.play()
                elif current_state == "BOOK":
                    load_book_content(files_list[current_index])
                    current_state = "READING"
                elif current_state == "BT_LIST":
                    mac = bt_devices[current_index]['mac']
                    draw_msg("Đang kết nối...", mac)
                    subprocess.run(["bluetoothctl", "connect", mac])
            ui_refresh()

# --- 6. MAIN ---
if __name__ == "__main__":
    touch.set_handler(touch_callback)
    ui_refresh()
    while True:
        touch.poll() # Liên tục kiểm tra cảm ứng [cite: 1]
        time.sleep(0.05)
