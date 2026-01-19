import os
import time
import numpy as np
from mss import mss
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
import RPi.GPIO as GPIO
import pyautogui

# 1. Force X11 Display context
os.environ["DISPLAY"] = ":0"
os.system("xhost +local:$(whoami) > /dev/null 2>&1")
GPIO.setwarnings(False)

def main():
    try:
        # 2. Hardware Interface
        # DC on GPIO 24, RST on GPIO 25. 
        serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=24000000)
        
        # Initialize device
        device = st7789(serial, width=320, height=240, rotate=0)
        
        print("--- Future-Proof Hard-Fix Mirroring Started ---")

        with mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            lcd_size = (device.width, device.height)

            while True:
                # A. Capture Screen
                sct_img = sct.grab(monitor)
                
                # B. Convert to NumPy Array and drop Alpha channel
                frame = np.array(sct_img)[..., :3]

                m_x, m_y = pyautogui.position()
                
                # Giới hạn tọa độ chuột trong phạm vi màn hình để tránh lỗi index
                m_x = max(0, min(m_x, monitor["width"] - 1))
                m_y = max(0, min(m_y, monitor["height"] - 1))

                # Vẽ một điểm sáng (cursor) trực tiếp vào mảng frame
                # Tạo một hình vuông nhỏ 10x10 tại vị trí chuột
                ptr_size = 5 
                frame[m_y-ptr_size:m_y+ptr_size, m_x-ptr_size:m_x+ptr_size] = [255, 255, 255]

                # C. THE HARD COLOR CORRECTION
                # Fix 1: Bitwise Inversion (Flips White/Black)
                frame = 255 - frame

                # Fix 2: Manual Channel Swap (Fixes Red/Blue)
                # We swap Blue (index 0) with Red (index 2)
                b_chan = frame[..., 0].copy()
                r_chan = frame[..., 2].copy()
                frame[..., 0] = r_chan
                frame[..., 2] = b_chan

                # D. Convert to Image and Push
                # Updated to use direct array-to-image conversion without deprecated 'mode'
                img = Image.fromarray(frame)
                
                # Use Resampling.NEAREST to avoid the Pillow 13 wBILINEARarning
                img = img.resize(lcd_size, Image.Resampling.BILINEAR)
                
                device.display(img)

    except KeyboardInterrupt:
        print("\nMirroring stopped.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()

