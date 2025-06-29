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

keys = ((1, 2, 3, 'A'),
        (4, 5, 6, 'B'),
        (7, 8, 9, 'C'),
        ('*', 0, '#', 'D'))

keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, keys)	# Khởi tạo đối tượng Matrix_Keypad
    # Màn hình
i2c_scl = board.GP1
i2c_sda = board.GP0   # corrected: no extra whitespace
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
    1: Keycode.ONE,
    2: Keycode.TWO,
    3: Keycode.THREE,
    'A': Keycode.A,
    4: Keycode.FOUR,
    5: Keycode.FIVE,
    6: Keycode.SIX,
    'B': Keycode.B,
    7: Keycode.SEVEN,
    8: Keycode.EIGHT,
    9: Keycode.NINE,
    'C': Keycode.C,
    '*': Keycode.A, # Hoặc Keycode.EIGHT + Keycode.SHIFT nếu bạn muốn shift+8
    0: Keycode.ZERO,
    '#': Keycode.POUND, # Hoặc Keycode.THREE + Keycode.SHIFT nếu bạn muốn shift+3
    'D': Keycode.D
}

lcd.clear()
lcd.set_cursor_pos(0, 0)
lcd.print("Ban phim san sang5")
# Thay đổi dòng này:
lcd.set_cursor_pos(1, 0)
lcd.print("Nhan phim...")

while True:
    keys_pressed = keypad.pressed_keys
    if keys_pressed:
        for key in keys_pressed:
            if key in key_map:
                keycode_to_send = key_map[key]
                kbd.press(keycode_to_send)
                lcd.clear()
                lcd.set_cursor_pos(0, 0)
                lcd.print(f"Da nhan: {key}")
                time.sleep(0.1) # Độ trễ ngắn để tránh nhấn kép
    else:
        # Nhả tất cả các phím khi không có phím nào được nhấn
        kbd.release_all()
    time.sleep(0.05) # Độ trễ nhỏ giữa các lần quét phím
