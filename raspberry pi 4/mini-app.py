import os
import time
import subprocess
import threading
import pygame
import board
import busio
import sys
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
    print(f"Lỗi cảm ứng: {e}"); sys.exit(1)

# --- 2. BIẾN HỆ THỐNG ---
USER_PATH = "/home/dinhphuc"
PATHS = {"MUSIC": f"{USER_PATH}/Music", "VIDEO": f"{USER_PATH}/Videos", 
         "PHOTO": f"{USER_PATH}/Pictures", "BOOK": f"{USER_PATH}/Documents"}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

current_state = "MENU"
current_index = 0
files_list = []
bt_devices = []
last_touch_time = 0

# Biến riêng cho tính năng đọc sách
book_pages = []
current_page_idx = 0

def get_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

font_s, font_m, font_l = get_font(14), get_font(18), get_font(24)
pygame.mixer.init()

# --- 3. LOGIC PHÂN TRANG CHO BOOK ---

def paginate_book(filename):
    """Chia nội dung file thành các trang vừa màn hình"""
    global book_pages, current_page_idx
    path = os.path.join(PATHS["BOOK"], filename)
    book_pages = []
    current_page_idx = 0
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Mỗi trang khoảng 400 ký tự (tùy chỉnh để vừa màn hình 320x240)
            chars_per_page = 350 
            book_pages = [content[i:i+chars_per_page] for i in range(0, len(content), chars_per_page)]
    except Exception as e:
        book_pages = [f"Lỗi đọc file: {e}"]

# --- 4. GIAO DIỆN (UI) ---

def draw_button(draw, x, y, w, h, text, bg="#262626", fg="white"):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=5, outline="white", fill=bg)
    bbox = draw.textbbox((0, 0), text, font=font_s)
    draw.text((x + (w-(bbox[2]-bbox[0]))/2, y + (h-(bbox[3]-bbox[1]))/2), text, fill=fg, font=font_s)

def draw_header(draw, title):
    draw.rectangle((0, 0, WIDTH, 40), fill="#1A1A1A")
    draw.text((10, 10), title, fill="yellow", font=font_m)
    draw_button(draw, 250, 5, 65, 30, "BACK", bg="#8B0000")

def ui_refresh():
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        
        if current_state == "MENU":
            draw.text((70, 10), "PI MEDIA CENTER", fill="#00FF00", font=font_l)
            menu_items = ["Bluetooth", "Music", "Video", "Photos", "Books"]
            for i, item in enumerate(menu_items):
                draw_button(draw, 40, 50 + i*35, 240, 30, item)
        
        elif current_state in ["MUSIC", "VIDEO", "PHOTO", "BOOK", "BT_LIST"]:
            draw_header(draw, current_state)
            items = bt_devices if current_state == "BT_LIST" else files_list
            for i, item in enumerate(items[0:4]):
                name = item['name'] if isinstance(item, dict) else item
                color = "cyan" if i == current_index else "white"
                draw.text((10, 50 + i*35), f"{'>' if i==current_index else ' '} {name[:28]}", fill=color, font=font_s)
            
            draw_button(draw, 20, 200, 80, 35, "LÊN")
            draw_button(draw, 120, 200, 80, 35, "CHỌN")
            draw_button(draw, 220, 200, 80, 35, "XUỐNG")

        elif current_state == "READING":
            draw_header(draw, "READER")
            if book_pages:
                text = book_pages[current_page_idx]
                # Tách dòng tự động để không bị tràn màn hình
                lines = [text[i:i+35] for i in range(0, len(text), 35)]
                for i, line in enumerate(lines[:8]):
                    draw.text((10, 50 + i*20), line.strip(), fill="white", font=font_s)
                
                # Hiển thị số trang
                draw.text((130, 210), f"{current_page_idx + 1}/{len(book_pages)}", fill="yellow", font=font_s)
                draw_button(draw, 20, 200, 80, 35, "TRƯỚC")
                draw_button(draw, 220, 200, 80, 35, "SAU")

        device.display(img)

# --- 5. XỬ LÝ CẢM ỨNG ---

def touch_callback(x, y):
    global current_state, current_index, files_list, last_touch_time, current_page_idx
    if time.time() - last_touch_time < 0.4: return
    last_touch_time = time.time()

    if x > 240 and y < 45 and current_state != "MENU":
        current_state = "MENU"; ui_refresh(); return

    if current_state == "MENU":
        if 40 <= x <= 280:
            idx = (y - 50) // 35
            if idx == 0: # Bluetooth
                current_state = "BT_LIST"
                threading.Thread(target=lambda: (subprocess.run(["bluetoothctl", "scan", "on"], timeout=5), ui_refresh())).start()
            elif idx == 1: current_state = "MUSIC"; files_list = sorted([f for f in os.listdir(PATHS["MUSIC"]) if f.endswith(('.mp3', '.wav'))])
            elif idx == 2: current_state = "VIDEO"; files_list = sorted([f for f in os.listdir(PATHS["VIDEO"]) if f.endswith('.mp4')])
            elif idx == 3: current_state = "PHOTO"; files_list = sorted([f for f in os.listdir(PATHS["PHOTO"]) if f.lower().endswith(('.jpg', '.png'))])
            elif idx == 4: current_state = "BOOK"; files_list = sorted([f for f in os.listdir(PATHS["BOOK"]) if f.endswith('.txt')])
            current_index = 0; ui_refresh()

    elif current_state == "READING":
        if y > 190:
            if x < 100: # TRƯỚC
                current_page_idx = max(0, current_page_idx - 1)
            elif x > 220: # SAU
                current_page_idx = min(len(book_pages) - 1, current_page_idx + 1)
            ui_refresh()

    elif current_state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]:
        if y > 190:
            if x < 100: current_index = (current_index - 1) % len(files_list)
            elif x > 220: current_index = (current_index + 1) % len(files_list)
            elif 100 <= x <= 200:
                if current_state == "BOOK":
                    paginate_book(files_list[current_index])
                    current_state = "READING"
                # Thêm logic play nhạc/video ở đây nếu cần
            ui_refresh()

if __name__ == "__main__":
    touch.set_handler(touch_callback)
    ui_refresh()
    while True:
        touch.poll(); time.sleep(0.05)
