import utime
import random
from machine import I2C, Pin
from DIYables_Pico_Keypad import Keypad

NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [13, 12, 11, 10]
COLUMN_PINS = [9, 8, 7, 6]
KEYMAP = ['1', '2', '3', '+', '4', '5', '6', '-', '7', '8', '9', 'x', 'AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)

# Biến trạng thái game 1
target_number = 0
current_guess = 0
game_started = False

def start_game_1(lcd_obj, lcd_cols, lcd_rows):
    global game_started, target_number, current_guess
    game_started = True
    target_number = random.randint(0, 99) # Tạo số ngẫu nhiên từ 0 đến 99
    current_guess = 0 # Đặt lại số đoán ban đầu

    lcd_obj.clear()
    lcd_obj.set_cursor(0, 0) # Hàng 0, cột 0
    lcd_obj.print("Doan so tu 0-99")
    lcd_obj.set_cursor(0, 1) # Hàng 1, cột 0
    lcd_obj.print("So ban doan: ")
    update_guess_display(lcd_obj, lcd_cols, lcd_rows) # Gọi hàm để cập nhật hiển thị số đoán

def update_guess_display(lcd_obj, lcd_cols, lcd_rows):
    """Cập nhật số đoán hiện tại trên màn hình LCD."""
    lcd_obj.set_cursor(13, 1)
    lcd_obj.print("  ")
    lcd_obj.set_cursor(13, 1)
    if current_guess < 10:
        lcd_obj.print("0" + str(current_guess))
    else:
        lcd_obj.print(str(current_guess))

def check_guess(lcd_obj, lcd_cols, lcd_rows):
    """Kiểm tra số đoán của người chơi và hiển thị kết quả."""
    global game_started
    lcd_obj.clear()
    lcd_obj.set_cursor(0, 0)
    if current_guess == target_number:
        lcd_obj.print("CHUC MUNG!")
        lcd_obj.set_cursor(0, 1) 
        lcd_obj.print("BAN DA THANG!")
        game_started = False # Kết thúc game
    elif current_guess < target_number:
        lcd_obj.print("SO CUA BAN NHO HON")
        lcd_obj.set_cursor(0, 1) 
        lcd_obj.print("Hay thu lai...")
    else: 
        lcd_obj.print("SO CUA BAN LON HON")
        lcd_obj.set_cursor(0, 1)
        lcd_obj.print("Hay thu lai...")
    utime.sleep(2) 
    # Sau khi hiển thị kết quả, nếu game chưa kết thúc (chưa thắng), thì chuẩn bị cho lượt đoán tiếp theo
    if game_started: 
        lcd_obj.clear()
        lcd_obj.set_cursor(0, 0)
        lcd_obj.print("Doan so tu 0-99")
        lcd_obj.set_cursor(0, 1)
        lcd_obj.print("So ban doan: ")
        update_guess_display(lcd_obj, lcd_cols, lcd_rows)
    else: # Nếu game kết thúc (thắng)
        lcd_obj.clear()
        lcd_obj.set_cursor(0, 0)
        lcd_obj.print("Ket thuc game.")
        lcd_obj.set_cursor(0, 1)
        lcd_obj.print("Nhan 'C' de choi lai")

def run_game_1(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    RUN_GAME_1 = True
    # Hiển thị thông báo ban đầu khi vào game
    lcd_obj.clear()
    lcd_obj.set_cursor(0, 0)
    lcd_obj.print("Game doan so")
    lcd_obj.set_cursor(0, 1)
    lcd_obj.print("Nhan 'C' de bat dau")

    while RUN_GAME_1:
        key = keypad.get_key()

        # Kiểm tra nút thoát
        if button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0: 
                utime.sleep(0.05)
            RUN_GAME_1 = False  
            continue        

        if not game_started:
            if key == 'x':
                start_game_1(lcd_obj, lcd_cols, lcd_rows)
                utime.sleep(0.2) 
        else: # Game đã bắt đầu
            if key == '+':
                global current_guess
                current_guess += 1
                if current_guess > 99:
                    current_guess = 0
                update_guess_display(lcd_obj, lcd_cols, lcd_rows)
                utime.sleep(0.15) 
            elif key == '-':
                current_guess -= 1
                if current_guess < 0:
                    current_guess = 99  
                update_guess_display(lcd_obj, lcd_cols, lcd_rows)
                utime.sleep(0.15) 
            elif key == ':': 
                check_guess(lcd_obj, lcd_cols, lcd_rows)
                utime.sleep(0.5)
        utime.sleep(0.01)

# Biến trạng thái game 2
score = 0
game_time_limit = 45
game_start_time = 0
game_active = False
current_mole_key = None

MOLE_POSITIONS = {'1': (1, 0), '2': (1, 4), '3': (1, 8), '4': (1, 12), '5': (1, 16),
                  '6': (2, 0), '7': (2, 4), '8': (2, 8), '9': (2, 12), '0': (2, 16)}

def run_game_2(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    global score, game_start_time, game_active, current_mole_key
    RUN_GAME_2 = True
    # Màn hình chào
    lcd_obj.clear()
    lcd_obj.set_cursor(0, 0)
    lcd_obj.print("Game DAP CHUOT CHUI")
    lcd_obj.set_cursor(0, 1)
    lcd_obj.print("Nhan '#' bat dau")
    lcd_obj.set_cursor(0, 3)
    lcd_obj.print("Chuc may man!")
    utime.sleep(2)

    while RUN_GAME_2:
        key = keypad.get_key()

                # Kiểm tra nút thoát
        if button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0: 
                utime.sleep(0.05)
            RUN_GAME_2 = False  
            continue        

        if not game_active:
            if key == '=':
                score = 0
                game_start_time = utime.time()
                game_active = True
                lcd_obj.clear()
                for k, (r, c) in MOLE_POSITIONS.items():
                    lcd_obj.set_cursor(c, r)
                    lcd_obj.print("_")
                utime.sleep(1)
            utime.sleep(0.01)
            continue
        
        time_left = max(0, game_time_limit - (utime.time() - game_start_time))
        lcd_obj.set_cursor(0, 0)
        lcd_obj.print(f"Diem: {score:<4} TG: {time_left:<3}s")

        if time_left == 0:
            game_active = False
            if current_mole_key:
                r, c = MOLE_POSITIONS[current_mole_key]
                lcd_obj.set_cursor(c, r)
                lcd_obj.print(" ")
                current_mole_key = None
            lcd_obj.clear()
            lcd_obj.set_cursor(0, 0)
            lcd_obj.print("HET GIO!")
            lcd_obj.set_cursor(0, 1)
            lcd_obj.print(f"Diem: {score} diem")
            lcd_obj.set_cursor(0, 2)
            lcd_obj.print("Tuyet voi!")
            lcd_obj.set_cursor(0, 3)
            lcd_obj.print("Nhan '#' choi lai")
            utime.sleep(3)
            continue

        if current_mole_key is None or utime.ticks_diff(utime.ticks_ms(), mole_spawn_time) > mole_display_duration:
            if current_mole_key:
                r, c = MOLE_POSITIONS[current_mole_key]
                lcd_obj.set_cursor(c, r)
                lcd_obj.print(" ")
            current_mole_key = random.choice(list(MOLE_POSITIONS.keys()))
            r, c = MOLE_POSITIONS[current_mole_key]
            lcd_obj.set_cursor(c, r)
            lcd_obj.print("O")
            mole_spawn_time = utime.ticks_ms()
            mole_display_duration = random.randint(700, 2000)

        if key:
            if key in MOLE_POSITIONS:
                if key == current_mole_key:
                    score += 1
                    r, c = MOLE_POSITIONS[current_mole_key]
                    lcd_obj.set_cursor(c, r)
                    lcd_obj.print(" ")
                    current_mole_key = None
                else:
                    score = max(0, score - 1)
            utime.sleep(0.15)
        
        utime.sleep(0.05)



