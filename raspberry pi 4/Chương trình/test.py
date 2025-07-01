import RPi.GPIO as GPIO
import RPi.GPIO as GPIO
import time
from Dong_co import Dong_co
import time
import sys
import tty
import termios
def main():
    Ab = Dong_co()

    print("Sử dụng các phím 'w' (tiến), 's' (lùi), 'a' (trái), 'd' (phải) để di chuyển AlphaBot.")
    print("Nhấn 'x' để dừng.")
    print("Nhấn 'q' để thoát.")

    try:
        while True:
            char = getch() # Lấy ký tự từ bàn phím

            if char == 'q':
                break # Thoát vòng lặp nếu nhấn 'q'
            elif char == 'w':
                Ab.forward()
            elif char == 's':
                Ab.backward()
            elif char == 'd':
                Ab.right()
            elif char == 'a':
                Ab.left()
            elif char == 'x': # Sử dụng 'x' để dừng
                Ab.stop()
            time.sleep(0.1) # Độ trễ nhỏ để tránh đọc quá nhanh

    except Exception as e:
        # Xử lý các lỗi có thể xảy ra trong quá trình chạy
        print(f"Đã xảy ra lỗi: {e}")
    finally:
        # Đảm bảo robot dừng và các chân GPIO được giải phóng
        Ab.stop()
        GPIO.cleanup() # Giải phóng các chân GPIO
        print("Chương trình kết thúc.")

if __name__ == '__main__':
    main()
