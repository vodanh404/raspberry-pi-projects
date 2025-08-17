import time
from machine import SPI,Pin
from menu_tft import TFTMenu

spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(26), mosi=Pin(27), miso=None)
dc = 21
rst = 20
cs = 22

button_up = Pin(10, Pin.IN, Pin.PULL_UP)
button_down = Pin(11, Pin.IN, Pin.PULL_UP)
button_select = Pin(14, Pin.IN, Pin.PULL_UP)

menu = TFTMenu(spi, dc, rst, cs, button_up, button_down, button_select)



# Chạy vòng lặp menu
menu.run_menu()
