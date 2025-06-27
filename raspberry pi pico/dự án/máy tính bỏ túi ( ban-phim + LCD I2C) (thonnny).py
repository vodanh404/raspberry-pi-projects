# Khai báo thư viện 
from machine import I2C, Pin
from DIYables_MicroPython_LCD_I2C import LCD_I2C
from DIYables_Pico_Keypad import Keypad
import utime
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
keypad.set_debounce_time(400)
#  Thiết lập màn hình
I2C_ADDR = 0x27
LCD_COLS = 20
LCD_ROWS = 4
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
lcd = LCD_I2C(i2c, I2C_ADDR, LCD_ROWS, LCD_COLS)
lcd.backlight_on()
lcd.clear()
# Thiết lập vài thông số 
bieu_thuc = ""
# làm tí giới thiệu 
lcd.print("May tinh bo tui")
utime.sleep(2)
lcd.clear()
# Chương trình chính
while True:
    key = keypad.get_key()
    if key:
        if key == 'AC':  # xóa biểu thức 
            bieu_thuc = ""
            lcd.clear()
        elif key == '=': # tính biểu thức
            try:
                bieu_thuc_to_eval = bieu_thuc.replace('x', '*').replace(':', '/') # Thay thế 'x' bằng '*' và ':' bằng '/' trước khi tính toán
                result = str(eval(bieu_thuc_to_eval))
                lcd.clear()
                lcd.print(result)
                bieu_thuc = result
            except Exception as e: # Bắt lỗi cụ thể hơn để dễ debug
                lcd.clear()
                lcd.print("Loi phep tinh!")
                print(f"Lỗi: {e}") # In lỗi ra console để debug
                bieu_thuc = ""
        else: 
            bieu_thuc += key
            lcd.clear() 
            lcd.print(bieu_thuc) 
        utime.sleep(0.3)
