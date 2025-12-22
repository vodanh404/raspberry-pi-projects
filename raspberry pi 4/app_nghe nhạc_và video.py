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
# Cấu hình LCD ST7789
serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=40000000)
device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")

# Cấu hình Cảm ứng XPT2046 (SPI1)
try:
    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                   width=WIDTH, height=HEIGHT, x_min=100, x_max=1962,
                   y_min=100, y_max=1900, baudrate=1000000)
except Exception as e:
    print(f"Lỗi khởi tạo cảm ứng: {e}")
    sys.exit(1)

# --- 2. BIẾN HỆ THỐNG ---
USER_PATH = "/home/dinhphuc"
PATHS = {
    "MUSIC": os.path.join(USER_PATH, "Music"),
    "VIDEO": os.path.join(USER_PATH, "Videos"),
    "PHOTO": os.path.join(USER_PATH, "Pictures"),
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

current_state = "MENU"
current_index = 0
files_list = []
last_touch_time = 0
volume = 0.5

# Khởi tạo Font
def get_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

font_s, font_m, font_l = get_font(14), get_font(18), get_font(24)

# Khởi tạo Audio
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

# --- 3. HÀM TIỆN ÍCH ---

def cleanup_processes():
    os.system("pkill -9 ffplay")
    os.system("pkill -9 ffmpeg")

def draw_button(draw, x, y, w, h, text, bg="#262626", fg="white", radius=5):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=radius, outline="white", fill=bg)
    bbox = draw.textbbox((0, 0), text, font=font_s)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((x + (w-tw)/2, y + (h-th)/2), text, fill=fg, font=font_s)

def draw_header(draw, title):
    draw.rectangle((0, 0, WIDTH, 40), fill="#1A1A1A")
    draw.text((10, 10), title, fill="yellow", font=font_m)
    draw_button(draw, 250, 5, 65, 30, "BACK", bg="#8B0000")

# --- 4. CÁC GIAO DIỆN CHỨC NĂNG ---

def ui_menu():
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        draw.text((80, 15), "PI MEDIA BOX", fill="#00FF00", font=font_l)
        menu_items = ["🎵 Music", "🎬 Video", "🖼️ Photos", "📡 Bluetooth"]
        for i, item in enumerate(menu_items):
            draw_button(draw, 40, 60 + i*40, 240, 35, item)
        device.display(img)

def ui_list(title):
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        draw_header(draw, title)
        if not files_list:
            draw.text((80, 100), "No Files Found", fill="red", font=font_m)
        else:
            # Hiển thị tối đa 4 file
            for i, f in enumerate(files_list[0:4]):
                color = "cyan" if i == current_index else "white"
                draw.text((10, 50 + i*35), f"{'>' if i==current_index else ' '} {f[:28]}", fill=color, font=font_s)
            
            draw_button(draw, 20, 200, 80, 35, "PREV")
            draw_button(draw, 120, 200, 80, 35, "SELECT")
            draw_button(draw, 220, 200, 80, 35, "NEXT")
        device.display(img)

def ui_photo_viewer():
    if not files_list: return
    try:
        img = Image.open(os.path.join(PATHS["PHOTO"], files_list[current_index]))
        img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        # Vẽ nút Back đè lên ảnh
        draw = ImageDraw.Draw(img)
        draw_button(draw, 250, 5, 65, 30, "CLOSE", bg="#8B0000")
        device.display(img)
    except: pass

# --- 5. LOGIC XỬ LÝ PHÁT MEDIA ---

def play_video(filename):
    video_path = os.path.join(PATHS["VIDEO"], filename)
    cleanup_processes()
    
    def video_thread():
        frame_size = WIDTH * HEIGHT * 3
        # Chạy âm thanh qua ffplay
        subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', video_path])
        # Chạy video qua ffmpeg pipe
        cmd = ['ffmpeg', '-re', '-i', video_path, '-vf', f'scale={WIDTH}:{HEIGHT}', 
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=frame_size)
        
        while current_state == "VIDEO_PLAYING":
            raw_frame = proc.stdout.read(frame_size)
            if not raw_frame or len(raw_frame) != frame_size: break
            image = Image.frombytes('RGB', (WIDTH, HEIGHT), raw_frame)
            device.display(image)
        proc.terminate()
        cleanup_processes()

    threading.Thread(target=video_thread, daemon=True).start()

# --- 6. XỬ LÝ CẢM ỨNG ---

def touch_handler(x, y):
    global current_state, current_index, files_list, last_touch_time
    
    if time.time() - last_touch_time < 0.3: return
    last_touch_time = time.time()

    # Nút BACK/CLOSE
    if x > 240 and y < 45:
        if current_state == "VIDEO_PLAYING": cleanup_processes()
        pygame.mixer.music.stop()
        current_state = "MENU"
        ui_menu()
        return

    if current_state == "MENU":
        if 40 <= x <= 280:
            idx = (y - 60) // 40
            if idx == 0: 
                current_state = "MUSIC"
                files_list = sorted([f for f in os.listdir(PATHS["MUSIC"]) if f.endswith(('.mp3', '.wav'))])
            elif idx == 1:
                current_state = "VIDEO"
                files_list = sorted([f for f in os.listdir(PATHS["VIDEO"]) if f.endswith('.mp4')])
            elif idx == 2:
                current_state = "PHOTO"
                files_list = sorted([f for f in os.listdir(PATHS["PHOTO"]) if f.lower().endswith(('.jpg', '.png'))])
            current_index = 0
            refresh_ui()

    elif current_state in ["MUSIC", "VIDEO", "PHOTO"]:
        # Xử lý PREV / NEXT / SELECT
        if y > 190:
            if 20 <= x <= 100: # PREV
                current_index = (current_index - 1) % len(files_list)
            elif 220 <= x <= 300: # NEXT
                current_index = (current_index + 1) % len(files_list)
            elif 120 <= x <= 200: # SELECT
                if current_state == "MUSIC":
                    pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], files_list[current_index]))
                    pygame.mixer.music.play()
                elif current_state == "VIDEO":
                    current_state = "VIDEO_PLAYING"
                    play_video(files_list[current_index])
                    return # Không vẽ lại UI list
                elif current_state == "PHOTO":
                    current_state = "PHOTO_VIEW"
                    ui_photo_viewer()
                    return
            refresh_ui()
            
    elif current_state == "PHOTO_VIEW":
        # Chạm vào màn hình để thoát xem ảnh
        current_state = "PHOTO"
        refresh_ui()

def refresh_ui():
    if current_state == "MENU": ui_menu()
    elif current_state in ["MUSIC", "VIDEO", "PHOTO"]: ui_list(current_state)

# --- 7. VÒNG LẶP CHÍNH ---

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda x,y: sys.exit(0))
    cleanup_processes()
    touch.set_handler(touch_handler)
    ui_menu()
    
    try:
        while True:
            touch.poll()
            time.sleep(0.05)
    except KeyboardInterrupt:
        cleanup_processes()
        pygame.mixer.quit()
