import utime
import urandom
from machine import I2C, Pin
from dfplayermini import DFPlayerMini
from DIYables_Pico_Keypad import Keypad

# Thiết lập bàn phím 
NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [13, 12, 11, 10] 
COLUMN_PINS = [9, 8, 7, 6] 
KEYMAP = ['1', '2', '3', '+',
          '4', '5', '6', '-',
          '7', '8', '9', 'x',
          'AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)
# Thiết lập mp3
player1 = DFPlayerMini(1, 4, 5) 
player1.select_source('sdcard')
# --- Khởi tạo các biến trạng thái ---
am_luong = 15
bai_hat = 1 # Bài hát mặc định ban đầu là bài số 1
MAX_BAI_HAT = 135
MIN_BAI_HAT = 1 # Bài hát tối thiểu
trang_thai_phat = False # False: Đang phát, True: Đã tạm dừng
che_do_ngau_nhien = False


# Khởi tạo giá trị hiển thị trước đó để so sánh (giúp màn hình ổn định)
prev_am_luong = -1
prev_bai_hat = -1
prev_trang_thai_phat = None
prev_che_do_ngau_nhien = None 
def update_lcd(lcd_obj, button_select_pin, lcd_cols, lcd_rows):	# hàm hỗ trợ cho phát nhạc 
    global prev_am_luong, prev_bai_hat, prev_trang_thai_phat, prev_che_do_ngau_nhien

    # Chỉ cập nhật nếu có bất kỳ giá trị nào thay đổi
    if (am_luong != prev_am_luong or bai_hat != prev_bai_hat or trang_thai_phat != prev_trang_thai_phat or che_do_ngau_nhien != prev_che_do_ngau_nhien):
        lcd_obj.clear() 
        lcd_obj.set_cursor(0, 0)
        lcd_obj.print(f"Volume: {am_luong:02d}") 
        lcd_obj.set_cursor(0, 1)
        lcd_obj.print(f"file: {bai_hat:03d}") 
        lcd_obj.set_cursor(0, 2)
        if not trang_thai_phat:
            lcd_obj.print("Status: Playing")
        else:
            lcd_obj.print("Status: Paused")
        lcd_obj.set_cursor(0, 3)
        mode_text = "Mode: Ngau nhien" if che_do_ngau_nhien else "Mode: Binh thuong"
        lcd_obj.print(mode_text)
        # Cập nhật giá trị "trước đó"
        prev_am_luong = am_luong
        prev_bai_hat = bai_hat
        prev_trang_thai_phat = trang_thai_phat
        prev_che_do_ngau_nhien = che_do_ngau_nhien
        
def run_music_player(lcd_obj, button_select_pin, lcd_cols, lcd_rows):

    global am_luong, bai_hat, trang_thai_phat, che_do_ngau_nhien

    # --- 1. Thiết lập ban đầu ---
    if not player1:
        lcd_obj.clear()
        lcd_obj.print("MP3 Player Error")
        return
    # Phát bài hát đầu tiên và cài đặt âm lượng
    player1.set_volume(am_luong)
    player1.play(bai_hat)
    trang_thai_phat = False # Trạng thái ban đầu là "đang phát"
    
    # Cập nhật màn hình LCD một lần với trạng thái ban đầu
    update_lcd(lcd_obj, button_select_pin, lcd_cols, lcd_rows)

    # --- 2. Vòng lặp chính ---
    Phat_Nhac = True
    while Phat_Nhac:
        # Kiểm tra nút bấm vật lý để thoát ứng dụng
        if button_select_pin.value() == 0:
            utime.sleep_ms(50) # Chống dội
            if button_select_pin.value() == 0:
                while button_select_pin.value() == 0: # Chờ nhả nút
                    utime.sleep_ms(50)
                player1.stop() # Dừng hẳn nhạc khi thoát
                Phat_Nhac = False
                continue 

        # Đọc phím từ keypad
        key = keypad.get_key()
        
        # Chỉ xử lý khi có phím được nhấn
        if key:
            should_update_lcd = False

            # --- Logic xử lý phím ---
            if key == '+': # Tăng âm lượng
                if am_luong < 30:
                    am_luong += 1
                    player1.set_volume(am_luong)
                    should_update_lcd = True
            
            elif key == '-': # Giảm âm lượng
                if am_luong > 0:
                    am_luong -= 1
                    player1.set_volume(am_luong)
                    should_update_lcd = True

            elif key == 'x': # Dừng/Tiếp tục phát (Play/Pause)
                if not trang_thai_phat:
                    player1.pause()
                    trang_thai_phat = True
                else:
                    player1.start()
                    trang_thai_phat = False
                should_update_lcd = True

            elif key == '=':  # Chuyển bài tiếp theo
                if che_do_ngau_nhien:
                    bai_hat = urandom.randint(MIN_BAI_HAT, MAX_BAI_HAT)
                else:
                    bai_hat = bai_hat + 1 if bai_hat < MAX_BAI_HAT else MIN_BAI_HAT

                player1.play(bai_hat)
                trang_thai_phat = False
                should_update_lcd = True

            elif key == 'AC':
                if che_do_ngau_nhien:
                    bai_hat = urandom.randint(MIN_BAI_HAT, MAX_BAI_HAT)
                else:
                    if bai_hat > MIN_BAI_HAT:
                        bai_hat -= 1
                player1.play(bai_hat)
                trang_thai_phat = False
                should_update_lcd = True
                    
            elif key == ':': # Bật/tắt chế độ ngẫu nhiên
                che_do_ngau_nhien = not che_do_ngau_nhien # Đảo ngược trạng thái
                should_update_lcd = True
                
            if should_update_lcd:
                update_lcd(lcd_obj, button_select_pin, lcd_cols, lcd_rows)
        utime.sleep(0.05) 

    # Thông báo khi thoát
    lcd_obj.clear()
    lcd_obj.print("Dang thoat...")
    utime.sleep(1)