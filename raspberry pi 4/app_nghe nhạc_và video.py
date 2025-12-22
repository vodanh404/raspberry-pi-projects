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
from luma.core.render import canvas
from luma.lcd.device import st7789
from xpt2046 import XPT2046

# --- 1. CẤU HÌNH PHẦN CỨNG ---
# Màn hình ST7789 (SPI0)
serial = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=40000000)
device = st7789(serial, width=320, height=240, rotate=0, framebuffer="full_frame")

# Cảm ứng XPT2046 (SPI1)
# Đảm bảo các chân SCLK, MOSI, MISO của SPI1 được kết nối đúng trên Header 40-pin
try:
    # Khởi tạo lại bus SPI cho cảm ứng
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=320, height=240, x_min=300, x_max=3800,
                    y_min=200, y_max=3800, baudrate=1000000)
    print("Khởi tạo cảm ứng thành công!")
except Exception as e:
    print(f"Lỗi khởi tạo cảm ứng: {e}")
    sys.exit(1)

# --- 2. BIẾN TOÀN CỤC ---
current_state = "MENU"
last_touch_time = 0

# Font & Audio (Giữ nguyên như cũ)
def get_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except: return ImageFont.load_default()
font_m = get_font(18)
font_l = get_font(24)

# --- 3. HÀM GIAO DIỆN ---
def draw_button(draw, x, y, w, h, text, bg="blue"):
    draw.rectangle((x, y, x+w, y+h), outline="white", fill=bg)
    draw.text((x + 10, y + 5), text, fill="white", font=get_font(14))

def ui_refresh():
    global current_state
    with canvas(device) as draw:
        if current_state == "MENU":
            draw.rectangle(device.bounding_box, fill="black")
            draw.text((85, 10), "MAIN MENU", fill="cyan", font=font_l)
            menu_items = ["Bluetooth", "Music", "Video", "Photos", "Books"]
            for i, item in enumerate(menu_items):
                draw_button(draw, 40, 50 + i*35, 240, 30, item, bg="#262626")
        else:
            draw.rectangle(device.bounding_box, fill="darkblue")
            draw.text((20, 100), f"Trạng thái: {current_state}", fill="white", font=font_m)
            draw_button(draw, 260, 2, 58, 26, "BACK", bg="red")

# --- 4. XỬ LÝ CẢM ỨNG ---
def touch_handler(x, y):
    global current_state, last_touch_time
    
    # Chống rung (Debounce)
    if time.time() - last_touch_time < 0.4:
        return
    last_touch_time = time.time()
    
    print(f"Đã chạm tại: X={x}, Y={y}") # Kiểm tra trong console xem có in ra dòng này không

    if current_state == "MENU":
        if 40 <= x <= 280:
            idx = (y - 50) // 35
            if 0 <= idx < 5:
                states = ["BLUETOOTH", "MUSIC", "VIDEO", "PHOTO_LIST", "BOOK_LIST"]
                current_state = states[idx]
                ui_refresh()
    else:
        # Nút Back
        if x > 250 and y < 40:
            current_state = "MENU"
            ui_refresh()

# --- 5. VÒNG LẶP CHÍNH ---
if __name__ == "__main__":
    try:
        # Gán hàm xử lý khi có sự kiện chạm
        touch.set_handler(touch_handler)
        
        ui_refresh()
        print("Đang đợi cảm ứng...")
        
        while True:
            # Quan trọng: Luôn gọi poll() để thư viện kiểm tra chân IRQ
            touch.poll()
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("Thoát chương trình.")
