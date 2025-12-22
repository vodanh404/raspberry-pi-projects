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
from luma.core.render import canvas
from luma.lcd.device import st7789
from xpt2046 import XPT2046

# --- 1. CẤU HÌNH PHẦN CỨNG ---
# Màn hình ST7789 (SPI0)
serial = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=40000000)
device = st7789(serial, width=320, height=240, rotate=0, framebuffer="full_frame")

# Cảm ứng XPT2046 (SPI1)
try:
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=320, height=240, x_min=300, x_max=3800,
                    y_min=200, y_max=3800, baudrate=1000000)
except Exception as e:
    print(f"Lỗi khởi tạo cảm ứng: {e}")
    sys.exit(1)

# --- 2. CẤU HÌNH HỆ THỐNG & FONT ---
USER_PATH = "/home/dinhphuc"
PATHS = {
    "MUSIC": os.path.join(USER_PATH, "Music"),
    "VIDEO": os.path.join(USER_PATH, "Videos"),
    "PHOTO": os.path.join(USER_PATH, "Pictures"),
    "BOOK": os.path.join(USER_PATH, "Documents")
}

for p in PATHS.values():
    os.makedirs(p, exist_ok=True)

def get_font(size, bold=False):
    try:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

font_s = get_font(14)
font_m = get_font(18, True)
font_l = get_font(24, True)

# Audio Init
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

# Biến trạng thái
current_state = "MENU"
volume = 0.5
last_touch_time = 0
bt_devices = []
music_list = []
video_list = []
photo_list = []
book_list = []
current_index = 0
is_scanning_bt = False

# --- 3. CÁC HÀM GIAO DIỆN ---

def draw_button(draw, x, y, w, h, text, bg="blue", fg="white"):
    draw.rectangle((x, y, x+w, y+h), outline="white", fill=bg)
    bbox = draw.textbbox((0, 0), text, font=font_s)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((x + (w-tw)/2, y + (h-th)/2), text, fill=fg, font=font_s)

def draw_header(draw, title):
    draw.rectangle((0, 0, 320, 30), fill="#1A1A1A")
    draw.text((10, 5), title, fill="yellow", font=font_m)
    draw_button(draw, 260, 2, 58, 26, "BACK", bg="#8B0000")

def show_message(line1, line2=""):
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        draw.text((20, 80), line1, fill="yellow", font=font_m)
        draw.text((20, 110), line2, fill="white", font=font_s)
    time.sleep(1.5)

# --- 4. LOGIC MODULES ---

# MENU
menu_items = ["Bluetooth", "Music", "Video", "Photos", "Books"]

def ui_menu():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")
        draw.text((85, 10), "PI MEDIA", fill="#00FF00", font=font_l)
        for i, item in enumerate(menu_items):
            y_pos = 50 + i * 35
            draw_button(draw, 40, y_pos, 240, 30, item, bg="#262626")

def handle_menu_touch(x, y):
    global current_state, current_index
    for i in range(len(menu_items)):
        y_pos = 50 + i * 35
        if 40 <= x <= 280 and y_pos <= y <= y_pos + 30:
            if i == 0: 
                current_state = "BLUETOOTH"
                threading.Thread(target=scan_bt_task, daemon=True).start()
            elif i == 1:
                current_state = "MUSIC"
                load_files("MUSIC", ('.mp3', '.wav'))
            elif i == 2:
                current_state = "VIDEO"
                load_files("VIDEO", ('.mp4', '.avi', '.mkv'))
            elif i == 3:
                current_state = "PHOTO_LIST"
                load_files("PHOTO", ('.jpg', '.png'))
            elif i == 4:
                current_state = "BOOK_LIST"
                load_files("BOOK", ('.txt'))
            ui_refresh()

def load_files(key, extensions):
    global music_list, video_list, photo_list, book_list, current_index
    files = sorted([f for f in os.listdir(PATHS[key]) if f.lower().endswith(extensions)])
    current_index = 0
    if key == "MUSIC": music_list = files
    elif key == "VIDEO": video_list = files
    elif key == "PHOTO": photo_list = files
    elif key == "BOOK": book_list = files
    
    if not files and key != "BLUETOOTH":
        show_message(f"No {key} files found")
        global current_state
        current_state = "MENU"

# BLUETOOTH
def scan_bt_task():
    global bt_devices, is_scanning_bt
    is_scanning_bt = True
    ui_refresh()
    bt_devices = []
    try:
        subprocess.run(["bluetoothctl", "scan", "on"], timeout=5, stdout=subprocess.DEVNULL)
        out = subprocess.check_output(["bluetoothctl", "devices"], timeout=5).decode("utf-8")
        for line in out.split('\n'):
            if "Device" in line:
                parts = line.split(' ', 2)
                if len(parts) > 2: bt_devices.append({"mac": parts[1], "name": parts[2]})
    except: pass
    is_scanning_bt = False
    ui_refresh()

def ui_bluetooth():
    with canvas(device) as draw:
        draw_header(draw, "BLUETOOTH")
        if is_scanning_bt:
            draw.text((10, 50), "Scanning devices...", fill="gray", font=font_s)
        elif not bt_devices:
            draw.text((10, 50), "No devices found.", fill="white", font=font_s)
            draw_button(draw, 100, 200, 120, 30, "RE-SCAN", bg="green")
        else:
            for i, dev in enumerate(bt_devices[:5]):
                draw_button(draw, 10, 40 + i*35, 300, 30, dev['name'][:25], bg="#333333")

# MUSIC
def ui_music():
    with canvas(device) as draw:
        draw_header(draw, "MUSIC PLAYER")
        if music_list:
            song = music_list[current_index]
            draw.text((10, 50), f"Playing: {song[:30]}", fill="cyan", font=font_s)
            is_playing = pygame.mixer.music.get_busy()
            draw_button(draw, 10, 120, 90, 50, "<<", bg="#444")
            draw_button(draw, 115, 120, 90, 50, "PAUSE" if is_playing else "PLAY", bg="#228B22" if is_playing else "#FF8C00")
            draw_button(draw, 220, 120, 90, 50, ">>", bg="#444")
            draw.text((10, 190), f"Vol: {int(volume*100)}%", fill="white", font=font_s)
            draw_button(draw, 100, 185, 40, 30, "-", bg="gray")
            draw_button(draw, 150, 185, 40, 30, "+", bg="gray")

# VIDEO (FFMPEG TO LCD)
def play_video_native(filepath):
    pygame.mixer.music.stop()
    show_message("Loading Video...", "Touch to Stop")
    
    # ffplay cho audio
    audio_proc = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', filepath])
    
    # ffmpeg pipe cho hình ảnh
    cmd = ['ffmpeg', '-re', '-i', filepath, '-vf', 'scale=320:240', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**6)
    
    frame_size = 320 * 240 * 3
    try:
        while True:
            if touch.is_touched(): break
            raw_image = pipe.stdout.read(frame_size)
            if not raw_image or len(raw_image) != frame_size: break
            image = Image.frombytes('RGB', (320, 240), raw_image)
            device.display(image)
    finally:
        pipe.terminate()
        audio_proc.terminate()
        subprocess.run(["pkill", "-9", "ffplay"])
        ui_refresh()

# --- 5. ĐIỀU PHỐI CẢM ỨNG ---

def ui_refresh():
    if current_state == "MENU": ui_menu()
    elif current_state == "BLUETOOTH": ui_bluetooth()
    elif current_state == "MUSIC": ui_music()
    elif current_state == "VIDEO":
        with canvas(device) as draw:
            draw_header(draw, "VIDEOS")
            for i, v in enumerate(video_list[:5]):
                draw_button(draw, 10, 40+i*35, 300, 30, v[:25], bg="#222")
    elif current_state == "PHOTO_LIST":
        if photo_list:
            img = Image.open(os.path.join(PATHS["PHOTO"], photo_list[current_index])).resize((320, 240))
            device.display(img)
    elif current_state == "BOOK_LIST":
         with canvas(device) as draw:
            draw_header(draw, "BOOKS")
            for i, b in enumerate(book_list[:5]):
                draw_button(draw, 10, 40+i*35, 300, 30, b[:25], bg="#222")

def touch_callback(x, y):
    global current_state, current_index, volume, last_touch_time
    if time.time() - last_touch_time < 0.3: return
    last_touch_time = time.time()

    # Nút Back chung
    if x > 250 and y < 40 and current_state != "MENU":
        if current_state == "MUSIC": pygame.mixer.music.stop()
        current_state = "MENU"
        ui_refresh()
        return

    if current_state == "MENU": handle_menu_touch(x, y)
    elif current_state == "MUSIC":
        if 115 <= x <= 205 and 120 <= y <= 170: # Play/Pause
            if pygame.mixer.music.get_busy(): pygame.mixer.music.pause()
            else:
                if not pygame.mixer.music.get_pos() or pygame.mixer.music.get_pos() == -1:
                    pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], music_list[current_index]))
                    pygame.mixer.music.play()
                else: pygame.mixer.music.unpause()
        elif 10 <= x <= 100 and 120 <= y <= 170: # Prev
            current_index = (current_index - 1) % len(music_list)
            pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], music_list[current_index]))
            pygame.mixer.music.play()
        elif 220 <= x <= 310 and 120 <= y <= 170: # Next
            current_index = (current_index + 1) % len(music_list)
            pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], music_list[current_index]))
            pygame.mixer.music.play()
        elif 100 <= x <= 140 and 185 <= y <= 215: # Vol -
            volume = max(0, volume - 0.1); pygame.mixer.music.set_volume(volume)
        elif 150 <= x <= 190 and 185 <= y <= 215: # Vol +
            volume = min(1, volume + 0.1); pygame.mixer.music.set_volume(volume)
        ui_refresh()
    elif current_state == "VIDEO":
        for i in range(len(video_list[:5])):
            if 10 <= x <= 310 and 40+i*35 <= y <= 70+i*35:
                play_video_native(os.path.join(PATHS["VIDEO"], video_list[i]))
    elif current_state == "PHOTO_LIST":
        if x < 100: current_index = (current_index - 1) % len(photo_list)
        elif x > 220: current_index = (current_index + 1) % len(photo_list)
        else: current_state = "MENU"
        ui_refresh()

# --- 6. MAIN LOOP ---
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
