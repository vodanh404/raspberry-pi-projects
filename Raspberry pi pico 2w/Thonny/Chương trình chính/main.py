import time
from machine import I2C, Pin
from menu_lcd import LCDMenu

# Thiết lập I2C cho LCD
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
i2c_addr = 0x27  # Địa chỉ I2C LCD của bạn

# Thiết lập thông số LCD
lcd_rows = 4
lcd_cols = 20

# Khởi tạo các nút điều khiển
button_up = Pin(16, Pin.IN, Pin.PULL_UP)
button_down = Pin(17, Pin.IN, Pin.PULL_UP)
button_select = Pin(18, Pin.IN, Pin.PULL_UP)

# Khởi tạo đối tượng menu
menu = LCDMenu(i2c, i2c_addr, lcd_rows, lcd_cols, button_up, button_down, button_select)

# Chạy vòng lặp menu
menu.run_menu()
