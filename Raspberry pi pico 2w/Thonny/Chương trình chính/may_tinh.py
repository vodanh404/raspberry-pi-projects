import utime
from machine import I2C, Pin
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

def run_calculator(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    bieu_thuc = ""
    is_calculator_running = True 
    
    lcd_obj.clear()
    lcd_obj.print("May tinh da san sang")
    utime.sleep(1)
    lcd_obj.clear()
    
    while is_calculator_running:
        key = keypad.get_key()

        # Kiểm tra nút thoát
        if button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            is_calculator_running = False 
            continue 

        if key:
            if key == 'AC':
                if bieu_thuc != "":
                    bieu_thuc = bieu_thuc[:-1]  # Xoá 1 ký tự cuối cùng
                    lcd_obj.clear()
                    lines = [bieu_thuc[i:i+lcd_cols] for i in range(0, len(bieu_thuc), lcd_cols)]
                    for i in range(min(2, len(lines))):
                        lcd_obj.set_cursor(0, i)
                        lcd_obj.print(lines[i])
                else:
                    lcd_obj.clear()
                    utime.sleep(0.5)

            elif key == '=':
                try:
                    bieu_thuc_to_eval = bieu_thuc.replace('x', '*').replace(':', '/')
                    result = str(eval(bieu_thuc_to_eval))
                    lcd_obj.clear()

                    # Hiển thị biểu thức trên 2 dòng đầu
                    lines = [bieu_thuc[i:i+lcd_cols] for i in range(0, len(bieu_thuc), lcd_cols)]
                    for i in range(min(2, len(lines))):
                        lcd_obj.set_cursor(0, i)
                        lcd_obj.print(lines[i])

                    # Hiển thị kết quả ở dòng cuối
                    lcd_obj.set_cursor(0, 2)
                    lcd_obj.print(result[:lcd_cols])

                    bieu_thuc = ""

                except Exception as e:
                    lcd_obj.clear()
                    lcd_obj.set_cursor(0, 0)
                    lcd_obj.print("Loi phep tinh!")
                    bieu_thuc = ""

            else:
                bieu_thuc += key
                lcd_obj.clear()

                # Hiển thị biểu thức mới nhất trên 2 dòng đầu
                lines = [bieu_thuc[i:i+lcd_cols] for i in range(0, len(bieu_thuc), lcd_cols)]
                for i in range(min(2, len(lines))):
                    lcd_obj.set_cursor(0, i)
                    lcd_obj.print(lines[i])

            utime.sleep(0.3)
        utime.sleep(0.05)
