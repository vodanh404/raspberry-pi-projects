import time
import urtc
from machine import I2C, Pin
from DIYables_MicroPython_LCD_I2C import LCD_I2C

days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
i2c = I2C(1, scl=Pin(3), sda=Pin(2))
rtc = urtc.DS1307(i2c)
initial_time_tuple = time.localtime() 
initial_time_seconds = time.mktime(initial_time_tuple)
initial_time = urtc.seconds2tuple(initial_time_seconds)
rtc.datetime(initial_time)

I2C_ADDR = 0x27  
LCD_COLS = 20
LCD_ROWS = 4
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
lcd = LCD_I2C(i2c, I2C_ADDR, LCD_ROWS, LCD_COLS)
lcd.backlight_on()
lcd.clear()

while True:
    current_datetime = rtc.datetime()
    lcd.clear()
    lcd.set_cursor(0, 0);            
    lcd.print(f"{current_datetime.day:02d}/{current_datetime.month:02d}/{current_datetime.year}");     
    lcd.set_cursor(12, 0);            
    lcd.print(f"{current_datetime.hour:02d}/{current_datetime.minute:02d}/{current_datetime.second}");
    time.sleep(1)
