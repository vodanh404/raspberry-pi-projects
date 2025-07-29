import utime
import urtc
import ntptime
from machine import I2C, Pin
from DIYables_Pico_Keypad import Keypad
from ket_noi_wifi import do_connect_wifi

days_of_week = ['Mon', 'Tue', 'Wednes', 'Thur', 'Fri', 'Sat', 'Sun']

rtc = urtc.DS1307(I2C(1, scl=Pin(3), sda=Pin(2)))

NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [13, 12, 11, 10]
COLUMN_PINS = [9, 8, 7, 6]
KEYMAP = ['1', '2', '3', '+', '4', '5', '6', '-', '7', '8', '9', 'x', 'AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)

# Đồng bộ t
if do_connect_wifi():
    try:
        ntptime.host = "time.google.com"
        ntptime.settime()
        local_seconds = utime.time() + (7 * 3600)
        tm = utime.localtime(local_seconds)
        rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
        print('Đồng bộ thời gian NTP và cập nhật RTC thành công!')
    except Exception as e:
        print(f'Lỗi khi đồng bộ NTP: {e}')
        print('Sử dụng thời gian hiện có từ RTC.')
else:
    print('Không có kết nối mạng. Sử dụng thời gian hiện có từ RTC.')
    
def run_clock(lcd_obj, button_select_pin, lcd_cols, lcd_rows): 
    Dong_Ho = True 
    lcd_obj.clear()
    
    while Dong_Ho:
        current_datetime = rtc.datetime()
        if button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            Dong_Ho = False 
            continue 
        
        lcd_obj.clear()
        lcd_obj.set_cursor(0, 0);
        lcd_obj.print("--------------------");
        lcd_obj.set_cursor(5, 1);            
        lcd_obj.print(f"{current_datetime.day:02d}/{current_datetime.month:02d}/{current_datetime.year}");     
        lcd_obj.set_cursor(6, 2);            
        lcd_obj.print(f"{current_datetime.hour:02d}:{current_datetime.minute:02d}:{current_datetime.second}");
        lcd_obj.set_cursor(0, 3);
        lcd_obj.print("--------------------");
        utime.sleep(1)

