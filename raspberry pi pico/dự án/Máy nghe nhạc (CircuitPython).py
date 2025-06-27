import time
import board
import digitalio
import pwmio
import busio
import storage
import adafruit_sdcard
from lcd.lcd import LCD, CursorMode
from lcd.i2c_pcf8574_interface import I2CPCF8574Interface
import audiomp3
import audiopwmio

button1 = digitalio.DigitalInOut(board.GP3)
button2 = digitalio.DigitalInOut(board.GP7)
button3 = digitalio.DigitalInOut(board.GP8)
button4 = digitalio.DigitalInOut(board.GP12)

button1.switch_to_input(pull=digitalio.Pull.UP)
button2.switch_to_input(pull=digitalio.Pull.UP)
button3.switch_to_input(pull=digitalio.Pull.UP)
button4.switch_to_input(pull=digitalio.Pull.UP)

# Setup SD card
spi = busio.SPI(board.GP18, board.GP19, board.GP16)
cs = digitalio.DigitalInOut(board.GP17)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/music")
import os
print(os.listdir("/music"))
# Setup LCD display via I2C
i2c_scl = board.GP1
i2c_sda = board.GP0   # corrected: no extra whitespace
i2c_address = 0x27
cols = 20
rows = 4
i2c = busio.I2C(scl=i2c_scl, sda=i2c_sda)
interface = I2CPCF8574Interface(i2c, i2c_address)
lcd = LCD(interface, num_rows=rows, num_cols=cols)
lcd.set_cursor_mode(CursorMode.HIDE)

audio = audiopwmio.PWMAudioOut(board.GP14)
one = audiomp3.MP3Decoder (open("/music/United Breaks Guitars.mp3", "rb"))
two = audiomp3.MP3Decoder (open("/music/Vicetone - Way Back.mp3", "rb"))
three = audiomp3.MP3Decoder (open("/music/linga guli guli.mp3", "rb"))
while True:
    if not button1.value:
        audio.stop()
        lcd.clear()
        lcd.set_cursor_pos(0, 0)
        lcd.print("List of songs:")
        lcd.set_cursor_pos(1, 0)
        lcd.print("1.United Breaks Guitars")
        lcd.set_cursor_pos(2, 0)
        lcd.print("2.Vicetone-Way Back")
        lcd.set_cursor_pos(3, 0)
        lcd.print("3.Linga Guli Guli")
        time.sleep(0.1)
    if not button2.value:
        audio.stop()
        lcd.clear()
        lcd.set_cursor_pos(0, 0)
        lcd.print("1.United breaks guitars")
        lcd.set_cursor_pos(1, 0)
        lcd.print("playing... ")
        lcd.set_cursor_pos(2, 0)
        lcd.print("--------------------")
        time.sleep(0.1)
        audio.play(one)
    if not button3.value:
        audio.stop()
        lcd.clear()
        lcd.set_cursor_pos(0, 0)
        lcd.print("2.Vicetone-Way Back")
        lcd.set_cursor_pos(1, 0)
        lcd.print("playing... ")
        lcd.set_cursor_pos(2, 0)
        lcd.print("--------------------")
        time.sleep(0.1)
        audio.play(two)
    if not button4.value:
        audio.stop()
        lcd.clear()
        lcd.set_cursor_pos(0, 0)
        lcd.print("3.linga guli guli")
        lcd.set_cursor_pos(1, 0)
        lcd.print("playing... ")
        lcd.set_cursor_pos(2, 0)
        lcd.print("--------------------")
        audio.stop()
        time.sleep(0.1)
        audio.play(three)
