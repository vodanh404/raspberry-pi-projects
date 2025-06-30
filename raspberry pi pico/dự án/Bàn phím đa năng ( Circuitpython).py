import board
import digitalio
import time
# Bàn phím
import adafruit_matrixkeypad
# Màn hình
import busio
from lcd.lcd import LCD, CursorMode
from lcd.i2c_pcf8574_interface import I2CPCF8574Interface

# Thêm thư viện adafruit_hid
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Khai báo tình trạng kết nối
    # Bàn phím
cols = [digitalio.DigitalInOut(board.GP9),
        digitalio.DigitalInOut(board.GP8),
        digitalio.DigitalInOut(board.GP7),
        digitalio.DigitalInOut(board.GP6)]

rows = [digitalio.DigitalInOut(board.GP13),
        digitalio.DigitalInOut(board.GP12),
        digitalio.DigitalInOut(board.GP11),
        digitalio.DigitalInOut(board.GP10)]

keys = (('1', '2', '3', 'A'),
        ('4', '5', '6', 'B'),
        ('7', '8', '9', 'C'),
        ('*', '0', '#', 'D')) # Đảm bảo tất cả các khóa ở đây là chuỗi nếu key_map dùng chuỗi

keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, keys)	# Khởi tạo đối tượng Matrix_Keypad
    # Màn hình
i2c_scl = board.GP1
i2c_sda = board.GP0
i2c_address = 0x27
lcd_cols = 20
lcd_rows = 4
i2c = busio.I2C(scl=i2c_scl, sda=i2c_sda)
interface = I2CPCF8574Interface(i2c, i2c_address)
lcd = LCD(interface, num_rows=lcd_rows, num_cols=lcd_cols)
lcd.set_cursor_mode(CursorMode.HIDE)

# Khởi tạo đối tượng bàn phím HID
kbd = Keyboard(usb_hid.devices)

# Ánh xạ các phím với Keycode
# Bạn cần định nghĩa các Keycode phù hợp với nhu cầu của mình
# Ví dụ:
key_map = {
    '1': (Keycode.WINDOWS, Keycode.ONE),	# Mở ứng dụng ở vị trí đầu tiên 
    '2': (Keycode.WINDOWS, Keycode.TWO),	# Mở ứng dụng ở vị trí thứ 2 
    '3': (Keycode.WINDOWS, Keycode.THREE),	# Mở ứng dụng ở vị trí thứ 3 
    'A': (Keycode.WINDOWS, Keycode.ALT, Keycode.R), # Quay/dừng màn hình
    '4': (Keycode.WINDOWS, Keycode.TAB), 
    '5': Keycode.F11,	# Toàn màn hình
    '6': (Keycode.CONTROL, Keycode.SHIFT, Keycode.T), # Khôi phục cửa sổ trước
    'B': (Keycode.WINDOWS, Keycode.L),	# Khóa màn hình 
    '7': (Keycode.CONTROL, Keycode.EQUALS),	# Phóng to
    '8': (Keycode.CONTROL, Keycode.MINUS),	# Thu nhỏ
    '9': (Keycode.WINDOWS, Keycode.PERIOD),	# Mở bảng emoiji
    'C': (Keycode.WINDOWS, Keycode.SHIFT, Keycode.S),	# Chụp 1 phần màn hình
    '*': (Keycode.WINDOWS, Keycode.CONTROL, Keycode.D),
    '0': (Keycode.WINDOWS, Keycode.CONTROL, Keycode.LEFT_ARROW),
    '#': (Keycode.WINDOWS, Keycode.CONTROL, Keycode.RIGHT_ARROW),
    'D': Keycode.F5
}

lcd.clear()
lcd.set_cursor_pos(0, 0)
lcd.print("Ban phim san sang")
while True:
    keys_pressed = keypad.pressed_keys
    if keys_pressed:
        for key in keys_pressed:
            if key in key_map:
                keycode_to_send = key_map[key]
                
                # Xử lý trường hợp tổ hợp phím (ví dụ: '1')
                if isinstance(keycode_to_send, tuple):
                    kbd.press(*keycode_to_send) # Giải nén tuple để nhấn nhiều phím cùng lúc
                    time.sleep(0.05) # Độ trễ nhỏ giữa nhấn và nhả tổ hợp phím
                    kbd.release_all() # Nhả tất cả các phím trong tổ hợp
                else:
                    kbd.press(keycode_to_send) # Nhấn một phím đơn
                    time.sleep(0.05) # Độ trễ nhỏ giữa nhấn và nhả một phím

                lcd.clear()
                lcd.print(f"Da nhan: {key}") # Hiển thị phím đã nhấn thay vì thông báo chung
                time.sleep(0.1) # Độ trễ ngắn để tránh nhấn kép
    else:
        # Nhả tất cả các phím khi không có phím nào được nhấn
        kbd.release_all()
    time.sleep(0.05) # Độ trễ nhỏ giữa các lần quét phím

