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
    print(f"Lỗi cảm ứng: {e}"); sys.exit(1)

# --- 2. BIẾN HỆ THỐNG ---
USER_PATH = "/home/dinhphuc"
PATHS = {
    "MUSIC": os.path.join(USER_PATH, "Music"),
    "VIDEO": os.path.join(USER_PATH, "Videos"),
    "PHOTO": os.path.join(USER_PATH, "Pictures"),
    "BOOK": os.path.join(USER_PATH, "Documents")
}
current_state = "MENU"
current_index = 0
files_list = []
volume = 0.7 # Âm lượng mặc định 70%
last_touch_time = 0
video_process = None

def get_font(size):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

font_s, font_m, font_l = get_font(14), get_font(18), get_font(22)
pygame.mixer.init()

# --- 3. HÀM XỬ LÝ MEDIA ---

def cleanup_media():
    """Dừng tất cả các tiến trình media đang chạy"""
    global video_process
    os.system("pkill -9 ffplay")
    os.system("pkill -9 ffmpeg")
    pygame.mixer.music.stop()

def play_video_task(filename):
    """Luồng phát video (Hình qua FFmpeg, Tiếng qua FFplay)"""
    global current_state
    path = os.path.join(PATHS["VIDEO"], filename)
    frame_size = WIDTH * HEIGHT * 3
    
    # Phát âm thanh ngầm
    subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', path])
    
    # Phát hình ảnh
    cmd = ['ffmpeg', '-re', '-i', path, '-vf', f'scale={WIDTH}:{HEIGHT}', 
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=frame_size)
    
    while current_state == "VIDEO_PLAYING":
        raw_frame = proc.stdout.read(frame_size)
        if not raw_frame or len(raw_frame) != frame_size: break
        img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw_frame)
        device.display(img)
    
    proc.terminate()
    current_state = "VIDEO"
    ui_refresh()

# --- 4. GIAO DIỆN ĐỒ HỌA ---

def draw_button(draw, x, y, w, h, text, bg="#262626", fg="white"):
    draw.rounded_rectangle((x, y, x+w, y+h), radius=4, outline="white", fill=bg)
    bbox = draw.textbbox((0, 0), text, font=font_s)
    draw.text((x + (w-(bbox[2]-bbox[0]))/2, y + (h-(bbox[3]-bbox[1]))/2), text, fill=fg, font=font_s)

def ui_refresh():
    with Image.new("RGB", (WIDTH, HEIGHT)) as img:
        draw = ImageDraw.Draw(img)
        
        if current_state == "MENU":
            draw.text((70, 10), "PI MEDIA CENTER", fill="#00FF00", font=font_l)
            menu_items = ["Bluetooth", "Music Player", "Video Player", "Photo Gallery", "Books"]
            for i, item in enumerate(menu_items):
                draw_button(draw, 40, 50 + i*36, 240, 32, item)

        elif current_state in ["MUSIC", "VIDEO", "PHOTO", "BOOK"]:
            draw.rectangle((0, 0, WIDTH, 40), fill="#1A1A1A")
            draw.text((10, 10), current_state, fill="yellow", font=font_m)
            draw_button(draw, 250, 5, 65, 30, "BACK", bg="#8B0000")
            
            for i, name in enumerate(files_list[0:4]):
                color = "cyan" if i == current_index else "white"
                draw.text((15, 55 + i*35), f"{'>' if i==current_index else ' '} {name[:28]}", fill=color, font=font_s)
            
            # Footer navigation
            draw_button(draw, 10, 200, 90, 35, "LÊN")
            draw_button(draw, 115, 200, 90, 35, "CHỌN")
            draw_button(draw, 220, 200, 90, 35, "XUỐNG")

        elif current_state == "MUSIC_PLAYING":
            draw.rectangle((0, 0, WIDTH, 40), fill="#1A1A1A")
            draw_button(draw, 250, 5, 65, 30, "BACK", bg="#8B0000")
            draw.text((15, 60), f"Đang phát: {files_list[current_index][:25]}", fill="cyan", font=font_s)
            
            # Thanh âm lượng
            draw.text((15, 110), "Âm lượng:", fill="white", font=font_s)
            draw.rectangle((100, 115, 250, 125), outline="white")
            draw.rectangle((100, 115, 100 + int(volume * 150), 125), fill="green")
            
            draw_button(draw, 50, 150, 60, 40, "VOL-")
            draw_button(draw, 130, 150, 60, 40, "STOP")
            draw_button(draw, 210, 150, 60, 40, "VOL+")

        elif current_state == "PHOTO_VIEW":
            try:
                img_p = Image.open(os.path.join(PATHS["PHOTO"], files_list[current_index]))
                img_p = img_p.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
                device.display(img_p)
                return # Thoát hàm để không vẽ đè
            except: 
                current_state = "PHOTO"; ui_refresh()

        device.display(img)

# --- 5. XỬ LÝ CẢM ỨNG ---

def touch_callback(x, y):
    global current_state, current_index, files_list, last_touch_time, volume
    if time.time() - last_touch_time < 0.4: return
    last_touch_time = time.time()

    # Nút BACK chung
    if x > 240 and y < 45 and current_state != "MENU":
        cleanup_media()
        current_state = "MENU"; ui_refresh(); return

    if current_state == "MENU":
        if 40 <= x <= 280:
            idx = (y - 50) // 36
            if idx == 1: current_state = "MUSIC"; files_list = sorted([f for f in os.listdir(PATHS["MUSIC"]) if f.endswith(('.mp3', '.wav'))])
            elif idx == 2: current_state = "VIDEO"; files_list = sorted([f for f in os.listdir(PATHS["VIDEO"]) if f.endswith('.mp4')])
            elif idx == 3: current_state = "PHOTO"; files_list = sorted([f for f in os.listdir(PATHS["PHOTO"]) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
            current_index = 0; ui_refresh()

    elif current_state == "MUSIC_PLAYING":
        if 150 <= y <= 190:
            if 50 <= x <= 110: volume = max(0.0, volume - 0.1); pygame.mixer.music.set_volume(volume)
            elif 130 <= x <= 190: cleanup_media(); current_state = "MUSIC"
            elif 210 <= x <= 270: volume = min(1.0, volume + 0.1); pygame.mixer.music.set_volume(volume)
            ui_refresh()

    elif current_state in ["MUSIC", "VIDEO", "PHOTO"]:
        if y > 190:
            if x < 100: current_index = (current_index - 1) % len(files_list)
            elif x > 220: current_index = (current_index + 1) % len(files_list)
            elif 110 <= x <= 210:
                if current_state == "MUSIC":
                    pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], files_list[current_index]))
                    pygame.mixer.music.play()
                    current_state = "MUSIC_PLAYING"
                elif current_state == "VIDEO":
                    current_state = "VIDEO_PLAYING"
                    threading.Thread(target=play_video_task, args=(files_list[current_index],), daemon=True).start()
                    return
                elif current_state == "PHOTO":
                    current_state = "PHOTO_VIEW"
            ui_refresh()
    
    elif current_state == "PHOTO_VIEW":
        current_state = "PHOTO"; ui_refresh()

if __name__ == "__main__":
    touch.set_handler(touch_callback)
    ui_refresh()
    while True:
        touch.poll(); time.sleep(0.05)
