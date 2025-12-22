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
serial = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=40000000)
device = st7789(serial, width=320, height=240, rotate=0, framebuffer="full_frame")

try:
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=320, height=240, x_min=300, x_max=3800,
                    y_min=200, y_max=3800, baudrate=1000000)
except Exception as e:
    print(f"Lỗi cảm ứng: {e}")
    sys.exit(1)

# --- 2. BIẾN TOÀN CỤC ---
USER_PATH = "/home/dinhphuc"
PATHS = {
    "MUSIC": os.path.join(USER_PATH, "Music"),
    "VIDEO": os.path.join(USER_PATH, "Videos"),
    "PHOTO": os.path.join(USER_PATH, "Pictures"),
    "BOOK": os.path.join(USER_PATH, "Documents")
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

# Khởi tạo trạng thái
current_state = "MENU"
volume = 0.5
last_touch_time = 0
music_list, video_list, photo_list = [], [], []
current_index = 0
is_scanning_bt = False

# Khởi tạo Font
def get_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

font_s, font_m, font_l = get_font(14), get_font(18), get_font(24)

# Khởi tạo Audio
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

# --- 3. HÀM HỖ TRỢ ---

def draw_button(draw, x, y, w, h, text, bg="blue", fg="white"):
    draw.rectangle((x, y, x+w, y+h), outline="white", fill=bg)
    bbox = draw.textbbox((0, 0), text, font=font_s)
    draw.text((x + (w-(bbox[2]-bbox[0]))/2, y + (h-(bbox[3]-bbox[1]))/2), text, fill=fg, font=font_s)

def draw_header(draw, title):
    draw.rectangle((0, 0, 320, 30), fill="#1A1A1A")
    draw.text((10, 5), title, fill="yellow", font=font_m)
    draw_button(draw, 260, 2, 58, 26, "BACK", bg="#8B0000")

# --- 4. LOGIC XỬ LÝ ---

def ui_menu():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")
        draw.text((85, 10), "PI MEDIA", fill="#00FF00", font=font_l)
        items = ["Bluetooth", "Music", "Video", "Photos", "Books"]
        for i, item in enumerate(items):
            draw_button(draw, 40, 50 + i*35, 240, 30, item, bg="#262626")

def ui_refresh():
    global current_state  # QUAN TRỌNG: Khai báo global để tránh lỗi UnboundLocalError
    if current_state == "MENU": 
        ui_menu()
    elif current_state == "MUSIC": 
        with canvas(device) as draw:
            draw_header(draw, "MUSIC")
            if music_list:
                draw.text((10, 60), f"Playing: {music_list[current_index][:30]}", fill="cyan", font=font_s)
                is_p = pygame.mixer.music.get_busy()
                draw_button(draw, 115, 120, 90, 50, "PAUSE" if is_p else "PLAY", bg="green" if is_p else "orange")
            else:
                draw.text((80, 100), "No Music Files", fill="red", font=font_m)

def touch_callback(x, y):
    global current_state, current_index, last_touch_time, music_list, video_list
    
    if time.time() - last_touch_time < 0.4: return
    last_touch_time = time.time()

    # Nút BACK chung
    if x > 250 and y < 40 and current_state != "MENU":
        pygame.mixer.music.stop()
        current_state = "MENU"
        ui_refresh()
        return

    if current_state == "MENU":
        if 40 <= x <= 280:
            idx = (y - 50) // 35
            if idx == 0: current_state = "BLUETOOTH"
            elif idx == 1: 
                current_state = "MUSIC"
                music_list = sorted([f for f in os.listdir(PATHS["MUSIC"]) if f.endswith(('.mp3', '.wav'))])
            elif idx == 2: 
                current_state = "VIDEO"
                video_list = sorted([f for f in os.listdir(PATHS["VIDEO"]) if f.endswith(('.mp4'))])
            ui_refresh()
            
    elif current_state == "MUSIC":
        if 115 <= x <= 205 and 120 <= y <= 170:
            if pygame.mixer.music.get_busy(): pygame.mixer.music.pause()
            else:
                if not pygame.mixer.music.get_pos() or pygame.mixer.music.get_pos() == -1:
                    pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], music_list[current_index]))
                    pygame.mixer.music.play()
                else: pygame.mixer.music.unpause()
            ui_refresh()

# --- 5. MAIN ---
if __name__ == "__main__":
    try:
        touch.set_handler(touch_callback)
        ui_refresh()
        while True:
            touch.poll()
            time.sleep(0.05)
    except KeyboardInterrupt:
        pygame.mixer.quit()
        sys.exit(0)
