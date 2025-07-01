import RPi.GPIO as GPIO
import time
from AlphaBot import AlphaBot
import curses

def main(screen):
    """
    Hàm chính để khởi tạo curses và điều khiển AlphaBot.
    """
    Ab = AlphaBot()

    # Cấu hình curses
    curses.noecho()         # Không hiển thị phím gõ
    curses.cbreak()         # Phản hồi ngay lập tức cho các phím gõ (không cần Enter)
    screen.keypad(True)     # Cho phép xử lý các phím đặc biệt như mũi tên
    screen.halfdelay(3)     # Đặt timeout cho getch() là 3/10 giây (0.3 giây)

    screen.addstr("Sử dụng các phím mũi tên để di chuyển AlphaBot.\n")
    screen.addstr("Nhấn Enter để dừng.\n")
    screen.addstr("Nhấn 'q' để thoát.\n")
    screen.refresh()

    try:
        while True:
            char = screen.getch() # Lấy ký tự từ bàn phím

            if char == ord('q'):
                break # Thoát vòng lặp nếu nhấn 'q'
            elif char == curses.KEY_UP:
                Ab.forward()
                screen.addstr("Tiến\n")
            elif char == curses.KEY_DOWN:
                Ab.backward()
                screen.addstr("Lùi\n")
            elif char == curses.KEY_RIGHT:
                Ab.right()
                screen.addstr("Phải\n")
            elif char == curses.KEY_LEFT:
                Ab.left()
                screen.addstr("Trái\n")
            elif char == 10: # Mã ASCII cho phím Enter
                Ab.stop()
                screen.addstr("Dừng\n")
            screen.refresh()

    except Exception as e:
        # Xử lý các lỗi có thể xảy ra trong quá trình chạy
        screen.addstr(f"Đã xảy ra lỗi: {e}\n")
        screen.refresh()
        time.sleep(2) # Cho người dùng thấy thông báo lỗi
    finally:
        # Đảm bảo các thiết lập của curses và GPIO được khôi phục
        Ab.stop() # Đảm bảo robot dừng khi thoát
        GPIO.cleanup() # Giải phóng các chân GPIO
        curses.nocbreak()
        screen.keypad(False)
        curses.echo()
        curses.endwin()

if __name__ == '__main__':
    # Bắt đầu ứng dụng curses
    curses.wrapper(main)
