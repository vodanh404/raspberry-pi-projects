import time
import board
import digitalio
# Thẻ NFC 
from mfrc522 import MFRC522
# Bàn phím 
import adafruit_matrixkeypad
# màn hình 
import busio
from lcd.lcd import LCD, CursorMode
from lcd.i2c_pcf8574_interface import I2CPCF8574Interface
# Chế độ bàn phím
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
# thiết lập kết nối
    # Thẻ NFC
sck = board.GP2
mosi = board.GP3
miso = board.GP4
cs = board.GP5
rst = board.GP28

rfid = MFRC522(sck, mosi, miso, cs, rst)
prev_data = None
    # Bàn phím
cols = [digitalio.DigitalInOut(board.GP9),
        digitalio.DigitalInOut(board.GP8),
        digitalio.DigitalInOut(board.GP7),
        digitalio.DigitalInOut(board.GP6)]

rows = [digitalio.DigitalInOut(board.GP13),
        digitalio.DigitalInOut(board.GP12),
        digitalio.DigitalInOut(board.GP11),
        digitalio.DigitalInOut(board.GP10)]

keys = ((1, 2, 3, '+'),
        (4, 5, 6, '-'),
        (7, 8, 9, 'x'),
        ('AC', 0, '=', ':'))

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
########################################################## Tính năng 1: Máy tính bỏ túi
bieu_thuc = ""

def may_tinh():
    pressed_keys = keypad.pressed_keys
    if pressed_keys:
        key = pressed_keys[0]
        if key == 'AC':
            bieu_thuc = ""
            lcd.clear()
        elif key == '=':
            try:
                bieu_thuc_to_eval = bieu_thuc.replace('x', '*').replace(':', '/')
                result = str(eval(bieu_thuc_to_eval))
                lcd.clear()
                lcd.print(result)
                bieu_thuc = result
            except Exception as e: # Bắt tất cả các loại lỗi
                lcd.clear()
                lcd.print("Loi phep tinh!") # Thông báo lỗi chung
                bieu_thuc = ""
        else:
            bieu_thuc += str(key)
            lcd.clear()
            lcd.print(bieu_thuc)
        time.sleep(0.3)    
########################################################## Tính năng 2: Bàn phím phụ
def Ban_phim():
    pressed_keys = keypad.pressed_keys
    kbd = Keyboard(usb_hid.devices)
    if pressed_keys:
        key = pressed_keys[0]
        if key == '1':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '2':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '3':
            kbd.send(Keycode.A)
            kbd.release_all()            
        elif key == '+':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '4':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '5':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '6':
            kbd.send(Keycode.A)
            kbd.release_all()            
        elif key == '-':
            kbd.send(Keycode.A)
            kbd.release_all()    
        elif key == '7':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '8':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '9':
            kbd.send(Keycode.A)
            kbd.release_all()            
        elif key == 'x':
            kbd.send(Keycode.A)
            kbd.release_all()    
        elif key == 'AC':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '0':
            kbd.send(Keycode.A)
            kbd.release_all()
        elif key == '=':
            kbd.send(Keycode.A)
            kbd.release_all()            
        elif key == ':':
            kbd.send(Keycode.A)
            kbd.release_all()   
        time.sleep(0.2)
