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
from xpt2046 import XPT2046  # Đảm bảo file xpt2046.py nằm cùng thư mục

# --- 1. CẤU HÌNH PHẦN CỨNG ---
# Màn hình ST7789
serial = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=40000000)
device = st7789(serial, width=320, height=240, rotate=0, framebuffer="full_frame")

# Cảm ứng XPT2046 (SPI1)
spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                width=320, height=240, x_min=300, x_max=3800, # Cần calibrate lại nếu bị lệch
                y_min=200, y_max=3800, baudrate=1000000)

# --- 2. CẤU HÌNH HỆ THỐNG & FONT ---
USER_PATH = "/home/dinhphuc"
PATHS = {
    "MUSIC": os.path.join(USER_PATH, "Music"),
    "VIDEO": os.path.join(USER_PATH, "Videos"),
    "PHOTO": os.path.join(USER_PATH, "Pictures"),
    "BOOK": os.path.join(USER_PATH, "Documents")
}

# Tạo thư mục nếu chưa có
for p in PATHS.values():
    os.makedirs(p, exist_ok=True)

try:
    font_s = ImageFont.truetype("DejaVuSans.ttf", 14)
    font_m = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    font_l = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
except:
    font_s = ImageFont.load_default()
    font_m = ImageFont.load_default()
    font_l = ImageFont.load_default()

# Audio Init
pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()

# Biến trạng thái toàn cục
current_state = "MENU"
volume = 0.5
is_running = True
last_touch_time = 0

# Biến chức năng
bt_devices = []
music_list = []
video_list = []
photo_list = []
current_index = 0
is_scanning_bt = False

# --- 3. CÁC HÀM HỖ TRỢ GIAO DIỆN ---

def draw_button(draw, x, y, w, h, text, bg="blue", fg="white"):
    """Vẽ nút bấm giao diện"""
    draw.rectangle((x, y, x+w, y+h), outline="white", fill=bg)
    # Căn giữa text
    txt_bbox = draw.textbbox((0, 0), text, font=font_s)
    txt_w = txt_bbox[2] - txt_bbox[0]
    txt_h = txt_bbox[3] - txt_bbox[1]
    draw.text((x + (w-txt_w)/2, y + (h-txt_h)/2), text, fill=fg, font=font_s)

def draw_header(draw, title):
    """Vẽ tiêu đề và nút Back"""
    draw.rectangle((0, 0, 320, 30), fill="darkblue")
    draw.text((10, 5), title, fill="yellow", font=font_m)
    # Nút Back ở góc phải trên
    draw_button(draw, 260, 2, 58, 26, "BACK", bg="red")

def show_message(line1, line2=""):
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        draw.text((20, 80), line1, fill="yellow", font=font_m)
        draw.text((20, 110), line2, fill="white", font=font_s)
    time.sleep(1)

# --- 4. LOGIC XỬ LÝ TỪNG MODULE ---

# === MENU CHÍNH ===
menu_items = ["Bluetooth", "Music", "Video", "Photos", "Books"]

def ui_menu():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")
        draw.text((90, 10), "MAIN MENU", fill="cyan", font=font_l)
        
        # Vẽ lưới 2 cột hoặc danh sách
        for i, item in enumerate(menu_items):
            y_pos = 50 + i * 35
            draw_button(draw, 40, y_pos, 240, 30, item, bg="#222222")

def handle_menu_touch(x, y):
    global current_state, current_index
    # Kiểm tra chạm vào các mục menu
    for i in range(len(menu_items)):
        y_pos = 50 + i * 35
        if 40 <= x <= 280 and y_pos <= y <= y_pos + 30:
            if i == 0: 
                current_state = "BLUETOOTH"
                threading.Thread(target=scan_bt_task).start()
            elif i == 1: 
                current_state = "MUSIC"
                load_music_files()
            elif i == 2:
                current_state = "VIDEO"
                load_video_files()
            elif i == 3:
                current_state = "PHOTO_LIST"
                load_photo_files()
            elif i == 4:
                current_state = "BOOK_LIST"
            
            ui_refresh()
            return

# === BLUETOOTH ===
def scan_bt_task():
    global bt_devices, is_scanning_bt
    is_scanning_bt = True
    show_message("Scanning BT...")
    bt_devices = []
    try:
        subprocess.run(["bluetoothctl", "scan", "on"], timeout=5, stdout=subprocess.DEVNULL)
        out = subprocess.check_output(["bluetoothctl", "devices"], timeout=5).decode("utf-8")
        for line in out.split('\n'):
            if "Device" in line:
                parts = line.split(' ', 2)
                if len(parts) > 2:
                    bt_devices.append({"mac": parts[1], "name": parts[2]})
    except: pass
    is_scanning_bt = False
    ui_refresh()

def ui_bluetooth():
    with canvas(device) as draw:
        draw_header(draw, "BLUETOOTH")
        if is_scanning_bt:
            draw.text((10, 50), "Scanning...", fill="gray", font=font_s)
        elif not bt_devices:
            draw.text((10, 50), "No devices found.", fill="white", font=font_s)
            draw_button(draw, 100, 200, 120, 30, "RE-SCAN", bg="green")
        else:
            for i, dev in enumerate(bt_devices[:5]): # Hiện max 5 thiết bị
                y_pos = 40 + i * 35
                name = dev['name'][:25]
                draw_button(draw, 10, y_pos, 300, 30, name, bg="#333333")

def connect_bt(mac):
    show_message("Connecting...")
    try:
        subprocess.run(["bluetoothctl", "trust", mac], stdout=subprocess.DEVNULL)
        subprocess.run(["bluetoothctl", "connect", mac], timeout=8)
        # Audio routing logic (PulseAudio)
        time.sleep(1)
        sink_out = subprocess.check_output(["pactl", "list", "short", "sinks"]).decode("utf-8")
        for line in sink_out.split('\n'):
            if "bluez" in line:
                sink_name = line.split('\t')[1]
                subprocess.run(["pactl", "set-default-sink", sink_name])
                break
        pygame.mixer.quit()
        pygame.mixer.init()
        show_message("Connected!", "Audio Routed")
    except Exception as e:
        show_message("Failed", str(e)[:15])

def handle_bt_touch(x, y):
    global current_state
    # Nút Back
    if 260 <= x <= 318 and 2 <= y <= 28:
        current_state = "MENU"
        ui_refresh()
        return
    
    # Nút Rescan
    if not bt_devices and 100 <= x <= 220 and 200 <= y <= 230:
        threading.Thread(target=scan_bt_task).start()
        return

    # Chọn thiết bị
    for i, dev in enumerate(bt_devices[:5]):
        y_pos = 40 + i * 35
        if 10 <= x <= 310 and y_pos <= y <= y_pos + 30:
            connect_bt(dev['mac'])
            return

# === MUSIC PLAYER ===
def load_music_files():
    global music_list, current_index
    music_list = [f for f in os.listdir(PATHS["MUSIC"]) if f.endswith(('.mp3', '.wav'))]
    current_index = 0
    if music_list:
        play_music_file()

def play_music_file():
    if not music_list: return
    try:
        pygame.mixer.music.load(os.path.join(PATHS["MUSIC"], music_list[current_index]))
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Music Error: {e}")

def ui_music():
    with canvas(device) as draw:
        draw_header(draw, "MUSIC PLAYER")
        
        if not music_list:
            draw.text((80, 100), "No Music Files", fill="red", font=font_m)
            return

        # Tên bài hát
        song_name = music_list[current_index]
        draw.text((10, 50), song_name[:30], fill="cyan", font=font_s)
        draw.text((10, 70), song_name[30:60], fill="cyan", font=font_s)

        # Controls
        # [PREV] [PLAY/PAUSE] [NEXT]
        btn_y = 120
        draw_button(draw, 10, btn_y, 90, 50, "|<", bg="#444")
        
        is_playing = pygame.mixer.music.get_busy()
        lbl = "PAUSE" if is_playing else "PLAY"
        draw_button(draw, 115, btn_y, 90, 50, lbl, bg="green" if is_playing else "orange")
        
        draw_button(draw, 220, btn_y, 90, 50, ">|", bg="#444")

        # Volume
        draw.text((10, 190), f"VOL: {int(volume*100)}%", fill="white", font=font_s)
        draw_button(draw, 100, 185, 40, 30, "-", bg="gray")
        draw_button(draw, 150, 185, 40, 30, "+", bg="gray")

def handle_music_touch(x, y):
    global current_state, current_index, volume
    
    # Back button
    if 260 <= x <= 318 and 2 <= y <= 28:
        pygame.mixer.music.stop()
        current_state = "MENU"
        ui_refresh()
        return

    if not music_list: return

    # Controls Logic
    btn_y = 120
    # Prev
    if 10 <= x <= 100 and btn_y <= y <= btn_y+50:
        current_index = (current_index - 1) % len(music_list)
        play_music_file()
    # Play/Pause
    elif 115 <= x <= 205 and btn_y <= y <= btn_y+50:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
            if not pygame.mixer.music.get_pos(): # Nếu chưa play
                pygame.mixer.music.play()
    # Next
    elif 220 <= x <= 310 and btn_y <= y <= btn_y+50:
        current_index = (current_index + 1) % len(music_list)
        play_music_file()
    # Vol -
    elif 100 <= x <= 140 and 185 <= y <= 215:
        volume = max(0.0, volume - 0.1)
        pygame.mixer.music.set_volume(volume)
    # Vol +
    elif 150 <= x <= 190 and 185 <= y <= 215:
        volume = min(1.0, volume + 0.1)
        pygame.mixer.music.set_volume(volume)
    
    ui_refresh()

# === VIDEO PLAYER ===
def load_video_files():
    global video_list, current_index
    video_list = [f for f in os.listdir(PATHS["VIDEO"]) if f.endswith(('.mp4', '.avi', '.mkv'))]
    current_index = 0
    if not video_list:
        show_message("No Video Files")
        global current_state
        current_state = "MENU"

def ui_video_list():
    with canvas(device) as draw:
        draw_header(draw, "SELECT VIDEO")
        for i, vid in enumerate(video_list[:5]):
            y_pos = 40 + i * 35
            draw_button(draw, 10, y_pos, 300, 30, vid[:25], bg="#222")

def play_video_native(filepath):
    """Phát video dùng FFmpeg pipe thẳng vào LCD"""
    global current_state
    
    # Kill audio cũ
    pygame.mixer.quit()
    
    # 1. Chạy Audio nền
    audio_proc = subprocess.Popen(
        ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', filepath],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    # 2. Chạy Video Pipe
    cmd = [
        'ffmpeg', '-re', '-i', filepath,
        '-vf', 'scale=320:240',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24',
        '-loglevel', 'quiet', '-'
    ]
    
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**6)
    
    # Loop đọc frame
    frame_size = 320 * 240 * 3
    running = True
    
    try:
        while running:
            # Check touch để thoát (Poll trực tiếp vì đang block main loop)
            if touch.is_touched():
                raw = touch.get_touch()
                if raw:
                    # Chạm bất kỳ để thoát
                    running = False
            
            raw_image = pipe.stdout.read(frame_size)
            if len(raw_image) != frame_size:
                break
                
            image = Image.frombytes('RGB', (320, 240), raw_image)
            device.display(image)
            
    except Exception as e:
        print(e)
    finally:
        pipe.kill()
        audio_proc.kill()
        os.system("pkill -9 ffplay")
        os.system("pkill -9 ffmpeg")
        pygame.mixer.init() # Khôi phục audio hệ thống
        current_state = "VIDEO"
        ui_refresh()

def handle_video_touch(x, y):
    global current_state, current_index
    # Back
    if 260 <= x <= 318 and 2 <= y <= 28:
        current_state = "MENU"
        ui_refresh()
        return

    # Chọn video để play
    for i, vid in enumerate(video_list[:5]):
        y_pos = 40 + i * 35
        if 10 <= x <= 310 and y_pos <= y <= y_pos + 30:
            full_path = os.path.join(PATHS["VIDEO"], vid)
            play_video_native(full_path)
            return

# === PHOTO VIEWER (Cơ bản) ===
def load_photo_files():
    global photo_list, current_index
    photo_list = [f for f in os.listdir(PATHS["PHOTO"]) if f.lower().endswith(('.jpg', '.png'))]
    current_index = 0
    if photo_list:
        show_photo()
    else:
        show_message("No Photos")
        global current_state
        current_state = "MENU"

def show_photo():
    if not photo_list: return
    path = os.path.join(PATHS["PHOTO"], photo_list[current_index])
    img = Image.open(path)
    img = img.resize((320, 240))
    device.display(img)

def handle_photo_touch(x, y):
    global current_state, current_index
    # Chạm bên trái -> Ảnh trước
    if x < 100:
        current_index = (current_index - 1) % len(photo_list)
        show_photo()
    # Chạm bên phải -> Ảnh sau
    elif x > 220:
        current_index = (current_index + 1) % len(photo_list)
        show_photo()
    # Chạm giữa -> Thoát
    else:
        current_state = "MENU"
        ui_refresh()

# --- 5. ĐIỀU PHỐI CHÍNH (MAIN DISPATCHER) ---

def ui_refresh():
    """Vẽ lại giao diện dựa trên trạng thái hiện tại"""
    if current_state == "MENU": ui_menu()
    elif current_state == "BLUETOOTH": ui_bluetooth()
    elif current_state == "MUSIC": ui_music()
    elif current_state == "VIDEO": ui_video_list()
    # PHOTO tự vẽ trực tiếp không qua loop vẽ này
    elif current_state == "BOOK_LIST": 
        show_message("Coming Soon", "Book Reader")
        time.sleep(1)
        global current_state_menu
        current_state = "MENU" # Placeholder
        ui_refresh()

def touch_callback(x, y):
    """Hàm này được gọi khi phát hiện chạm"""
    global last_touch_time
    # Debounce đơn giản
    if time.time() - last_touch_time < 0.3: return
    last_touch_time = time.time()
    
    print(f"Touched at: {x}, {y} | State: {current_state}")
    
    if current_state == "MENU": handle_menu_touch(x, y)
    elif current_state == "BLUETOOTH": handle_bt_touch(x, y)
    elif current_state == "MUSIC": handle_music_touch(x, y)
    elif current_state == "VIDEO": handle_video_touch(x, y)
    elif current_state == "PHOTO_LIST": handle_photo_touch(x, y)

# --- 6. VÒNG LẶP CHÍNH ---

if __name__ == "__main__":
    try:
        # Cài đặt callback cho cảm ứng
        touch.set_handler(touch_callback)
        
        # Vẽ menu đầu tiên
        ui_refresh()
        
        while True:
            # Poll cảm ứng liên tục
            touch.poll()
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("Exiting...")
        pygame.mixer.quit()
        os.system("pkill -9 ffplay")
        os.system("pkill -9 ffmpeg")
