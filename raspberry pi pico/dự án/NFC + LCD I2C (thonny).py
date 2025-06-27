from mfrc522 import MFRC522
from machine import I2C, Pin
from DIYables_MicroPython_LCD_I2C import LCD_I2C
import utime

# Thiết lập kết nối giữa các chân
    # NFC
reader = MFRC522(spi_id=0, sck=Pin(2), miso=Pin(4), mosi=Pin(3), cs=Pin(1), rst=Pin(0))
print("Thẻ NFC hiện tại:\n")
PreviousCard = [0] # Khởi tạo PreviousCard
    # LCD I2C
I2C_ADDR = 0x27
LCD_COLS = 20
LCD_ROWS = 4
i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=400000)
lcd = LCD_I2C(i2c, I2C_ADDR, LCD_ROWS, LCD_COLS)
lcd.backlight_on()
lcd.clear()

# Hàm hiển thị thông báo trên LCD
def display_lcd_message(message_line1, message_line2):
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.print("xin chao")
    lcd.set_cursor(0, 1)
    lcd.print(message_line1)
    lcd.set_cursor(0, 2)
    lcd.print(message_line2)
    lcd.set_cursor(0, 3)
    lcd.print("--------------------")
    utime.sleep(2)

while True:
    reader.init()
    (stat, tag_type) = reader.request(reader.REQIDL)

    if stat == reader.OK:
        (stat, uid) = reader.SelectTagSN()

        if stat == reader.OK: # Chuyển UID sang chuỗi hex để so sánh dễ dàng
            card = reader.tohexstring(uid)
            if uid != PreviousCard:
                print("Chi tiết thẻ như sau:")
                print(card)

                if card == "[0x6D, 0x62, 0xD1, 0x05]":
                    print("Đã lưu trong hệ thống")
                    display_lcd_message("The NFC chinh xac", "test thanh cong")
                else:
                    print("Chưa lưu trong hệ thống")
                    display_lcd_message("The NFC sai", "test thanh cong")
                
                PreviousCard = uid # Cập nhật thẻ trước đó
            else:
                pass 
    else:
        PreviousCard = [0] 
        lcd.clear()
    utime.sleep_ms(50) # Giảm thời gian chờ để tăng tốc độ phản hồi
