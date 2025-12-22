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
bt_devices = [] # Lưu danh sách thiết bị bluetooth 
last_touch_time = 0

def get_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

font_s, font_m, font_l = get_font(14), get_font(18), get_font(24)

pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

# --- 3. HÀM TIỆN ÍCH UI ---

def draw_button(draw, x, y, w, h, text, bg="#262626", fg="white"):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=5, outline="white", fill=bg)
    bbox = draw.textbbox((0, 0), text, font=font_s)
    draw.text((x + (w-(bbox[2]-bbox[0]))/2, y + (h-(bbox[3]-bbox[1]))/2), text, fill=fg, font=font_s)

def draw_header(draw, title):
    draw.rectangle((0, 0, WIDTH, 40), fill="#1A1A1A")
    draw.text((10, 10), title, fill="yellow", font=font_m)
    draw_button(draw, 250, 5, 65, 30, "BACK", bg="#8B0000")

# --- 4. LOGIC BLUETOOTH & BOOK ---

def scan_bluetooth():
    global bt_devices, current_state
    bt_devices = []
    draw_msg("Scanning...", "Please wait 5s") [cite: 4]
    try:
        subprocess.run(["bluetoothctl", "scan", "on"], timeout=5, stdout=subprocess.DEVNULL)
        out = subprocess.check_output(["bluetoothctl", "devices"]).decode("utf-8")
        for line in out.split('\n'):
            if "Device" in line:
                parts = line.split(' ', 2) [cite: 5]
                if len(parts) > 2:
                    bt_devices.append({"mac": parts[1], "name": parts[2]}) [cite: 5]
    except: pass
    current_state = "BT_LIST"
    refresh_ui()

def draw_msg(line1, line2=""):
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        draw.text((20, 100), line1, fill="yellow", font=font_m)
        draw.text((20, 130), line2, fill="white", font=font_s)
        device.display(img)

def read_book(filename):
    path = os.path.join(PATHS["BOOK"], filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read(500) # Đọc 500 ký tự đầu tiên
        with Image.new("RGB", (WIDTH, HEIGHT)) as img:
            draw = ImageDraw.Draw(img)
            draw_header(draw, "READER")
            # Hiển thị nội dung văn bản
            lines = [content[i:i+40] for i in range(0, len(content), 40)]
            for i, line in enumerate(lines[:8]):
                draw.text((10, 50 + i*20), line, fill="white", font=font_s)
            device.display(img)
    except:
        draw_msg("Error", "Could not read file")

# --- 5. XỬ LÝ CẢM ỨNG ---

def touch_handler(x, y):
    global current_state, current_index, files_list, last_touch_time, bt_devices
    
    if time.time() - last_touch_time < 0.4: return
    last_touch_time = time.time()

    if x > 240 and y < 45: # Nút BACK
        os.system("pkill -9 ffplay")
        pygame.mixer.music.stop()
        current_state = "MENU"
        refresh_ui()
        return

    if current_state == "MENU":
        if 40 <= x <= 280:
            idx = (y - 60) // 40
            if idx == 0: # Music
                current_state = "MUSIC"
                files_list = sorted([f for f in os.listdir(PATHS["MUSIC"]) if f.endswith(('.mp3', '.wav'))])
            elif idx == 1: # Video
                current_state = "VIDEO"
                files_list = sorted([f for f in os.listdir(PATHS["VIDEO"]) if f.endswith('.mp4')])
            elif idx == 2: # Photos
                current_state = "PHOTO"
                files_list = sorted([f for f in os.listdir(PATHS["PHOTO"]) if f.lower().endswith(('.jpg', '.png'))])
            elif idx == 3: # Bluetooth (Sửa lỗi ở đây)
                current_state = "BT_SCAN"
                threading.Thread(target=scan_bluetooth).start()
                return
            current_index = 0
            refresh_ui()

    elif current_state in ["MUSIC", "VIDEO", "PHOTO", "BT_LIST"]:
        items = bt_devices if current_state == "BT_LIST" else files_list
        if not items: return
        
        if y > 190:
            if 20 <= x <= 100: current_index = (current_index - 1) % len(items)
            elif 220 <= x <= 300: current_index = (current_index + 1) % len(items)
            elif 120 <= x <= 200: # SELECT
                if current_state == "MUSIC":
                    pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], files_list[current_index]))
                    pygame.mixer.music.play()
                elif current_state == "BT_LIST":
                    mac = bt_devices[current_index]['mac'] [cite: 7]
                    draw_msg("Connecting...", mac) [cite: 7]
                    subprocess.run(["bluetoothctl", "connect", mac]) [cite: 7]
                    draw_msg("Connected!", "Press BACK")
                    return
            refresh_ui()

def refresh_ui():
    if current_state == "MENU":
        with Image.new("RGB", (WIDTH, HEIGHT)) as img:
            draw = ImageDraw.Draw(img)
            draw.text((80, 15), "PI MEDIA BOX", fill="#00FF00", font=font_l)
            menu_items = ["🎵 Music", "🎬 Video", "🖼️ Photos", "📡 Bluetooth"]
            for i, item in enumerate(menu_items):
                draw_button(draw, 40, 60 + i*40, 240, 35, item)
            device.display(img)
    elif current_state == "BT_LIST":
        with Image.new("RGB", (WIDTH, HEIGHT)) as img:
            draw = ImageDraw.Draw(img)
            draw_header(draw, "BLUETOOTH")
            for i, dev in enumerate(bt_devices[0:4]):
                color = "cyan" if i == current_index else "white"
                draw.text((10, 50 + i*35), f"{dev['name'][:25]}", fill=color, font=font_s)
            draw_button(draw, 20, 200, 80, 35, "PREV")
            draw_button(draw, 220, 200, 80, 35, "NEXT")
            draw_button(draw, 120, 200, 80, 35, "CONN")
            device.display(img)
    else: # Các danh sách file khác
        ui_list_files(current_state)

def ui_list_files(title):
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        draw_header(draw, title)
        for i, f in enumerate(files_list[0:4]):
            color = "cyan" if i == current_index else "white"
            draw.text((10, 50 + i*35), f[:30], fill=color, font=font_s)
        draw_button(draw, 20, 200, 80, 35, "PREV")
        draw_button(draw, 120, 200, 80, 35, "SELECT")
        draw_button(draw, 220, 200, 80, 35, "NEXT")
        device.display(img)

if __name__ == "__main__":
    touch.set_handler(touch_handler)
    refresh_ui()
    while True:
        touch.poll()
        time.sleep(0.05)
