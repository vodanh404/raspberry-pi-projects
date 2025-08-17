import utime, sdcard, os
from machine import SPI, Pin
from DIYables_Pico_Keypad import Keypad
from st7735 import TFT, sysfont, TFTColor

# Cấu hình bàn phím
NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [9, 8, 7, 6]
COLUMN_PINS = [5, 4, 3, 2]
KEYMAP = ['1', '2', '3', '+','4', '5', '6', '-','7', '8', '9', 'x','AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)

# Cấu hình thẻ nhớ SD
SD_MOUNT_PATH = '/sd'
IMAGE_SUBDIR = 'sd1' # Thư mục con chứa ảnh BMP
try:
    spi_sd = SPI(0, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    cs_sd = Pin(17, Pin.OUT)
    sd = sdcard.SDCard(spi_sd, cs_sd)
    os.mount(sd, SD_MOUNT_PATH)
    print("Thẻ nhớ SD đã được gắn thành công.")
except Exception as e:
    print('Lỗi khi gắn thẻ nhớ SD:', e)

# --- Các hàm chức năng ---

def get_image_list():
    """Kiểm tra và lấy danh sách tệp."""
    print("Danh sách tệp và thư mục trong SD_MOUNT_PATH:", os.listdir(SD_MOUNT_PATH))
    full_path = f"{SD_MOUNT_PATH}/{IMAGE_SUBDIR}"
    try:
        files = os.listdir(full_path)
        bmp_files = [f for f in files if f.lower().endswith('.bmp')]
        bmp_files.sort()
        print("Danh sách ảnh BMP trong thư mục đã chỉ định:", bmp_files)
        return bmp_files
    except OSError as e:
        print(f"Lỗi khi truy cập thư mục '{full_path}': {e}")
        return []
def draw_bmp(tft_obj, filename):
    """Vẽ ảnh BMP lên màn hình TFT."""
    filepath = f"{SD_MOUNT_PATH}/{IMAGE_SUBDIR}/{filename}"
    try:
        with open(filepath, "rb") as f:
            if f.read(2) == b"BM":
                dummy = f.read(8)
                offset = int.from_bytes(f.read(4), "little")
                hdrsize = int.from_bytes(f.read(4), "little")
                width = int.from_bytes(f.read(4), "little")
                height = int.from_bytes(f.read(4), "little")
                if int.from_bytes(f.read(2), "little") == 1:
                    depth = int.from_bytes(f.read(2), "little")
                    if (
                        depth == 24 and int.from_bytes(f.read(4), "little") == 0
                    ):
                        print("Image size:", width, "x", height)
                        rowsize = (width * 3 + 3) & ~3
                        if height < 0:
                            height = -height
                            flip = False
                        else:
                            flip = True
                        
                        w, h = width, height
                        if w > 128:
                            w = 128
                        if h > 160:
                            h = 160
                        
                        tft_obj._setwindowloc((0, 0), (w - 1, h - 1))
                        for row in range(h):
                            if flip:
                                pos = offset + (height - 1 - row) * rowsize
                            else:
                                pos = offset + row * rowsize
                            
                            if f.tell() != pos:
                                dummy = f.seek(pos)
                            for col in range(w):
                                bgr = f.read(3)
                                tft_obj._pushcolor(TFTColor(bgr[2], bgr[1], bgr[0]))
    except Exception as e:
        print(f"Lỗi khi vẽ ảnh {filename}: {e}")

def run_image_viewer(tft_obj, button_select_pin, bg_color, text_color,current_rotation):
    """Vòng lặp chính để hiển thị ảnh và xử lý phím bấm."""
    IMAGE_VIEWER = True
    if current_rotation == 0: a, b = 0, 0
    elif current_rotation == 1: a, b = 0, 1
    elif current_rotation == 2: a, b = 2, 2
    elif current_rotation == 3: a, b = 0, 3 

    tft_obj.rotation(a)
    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), "Doc danh sach anh...", text_color, sysfont.sysfont, 1)
    image_list = get_image_list()
    current_image_index = 0

    if not image_list:
        tft_obj.fill(bg_color)
        tft_obj.text((10, 10), "Khong tim thay anh BMP.", text_color, sysfont.sysfont, 1)
        utime.sleep(3)
        return

    draw_bmp(tft_obj, image_list[current_image_index])
    
    while IMAGE_VIEWER:
        
        if button_select_pin.value() == 0:
            tft_obj.rotation(b)
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            IMAGE_VIEWER = False
            continue
        
        key = keypad.get_key()
        if key:
            if key == '+':
                current_image_index = (current_image_index + 1) % len(image_list)
                tft_obj.fill(bg_color)
                draw_bmp(tft_obj, image_list[current_image_index])
                utime.sleep_ms(300) 
            elif key == '-':
                current_image_index = (current_image_index - 1 + len(image_list)) % len(image_list)
                tft_obj.fill(bg_color)
                draw_bmp(tft_obj, image_list[current_image_index])
                utime.sleep_ms(300)

