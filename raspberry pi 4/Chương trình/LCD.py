cd my_project
python3 -m venv library
source library/bin/activate
pip install --upgrade pip
pip install RPLCD smbus2
import time
from datetime import datetime
from RPLCD.i2c import CharLCD

# Khởi tạo màn hình LCD 1602 (2 dòng, 16 cột) với địa chỉ 0x27
# Sử dụng chip giao tiếp PCF8574
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=20, rows=4)

try:
    print("Đang hiển thị thời gian lên LCD... Bấm Ctrl+C để dừng.")
    lcd.clear()
    
    while True:
        # Lấy thời gian hiện tại từ hệ thống
        now = datetime.now()
        
        # Định dạng chuỗi hiển thị
        time_str = now.strftime("%H:%M:%S")    # Dòng 1: Giờ: HH:MM:SS
        date_str = now.strftime("%d/%m/%Y")  # Dòng 2: Ngày: DD/MM/YYYY
        
        # Ghi dòng 1
        lcd.cursor_pos = (0, 0)
        lcd.write_string("-------------------")
        lcd.cursor_pos = (1, 6)
        lcd.write_string(time_str)
        
        # Ghi dòng 2
        lcd.cursor_pos = (2, 5)
        lcd.write_string(date_str)
        lcd.cursor_pos = (3, 0)
        lcd.write_string("-------------------")
        # Cập nhật mỗi giây
        time.sleep(1)

except KeyboardInterrupt:
    print("\nĐã dừng chương trình.")

finally:
    # Tắt đèn nền và xóa màn hình khi thoát
    lcd.clear()
    lcd.backlight_enabled = False
    lcd.close()
