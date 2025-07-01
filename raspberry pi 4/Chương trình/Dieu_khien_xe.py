# Khai báo thư viện
import sys
import time
import os
from Dong_co import Dong_co 
# Lệnh kiểm tra 
try:
    if os.geteuid() != 0: # Kiểm tra xem có đang chạy với quyền root không
        print("Lỗi: Script cần được chạy với quyền root (sudo) để truy cập GPIO.")
        sys.exit(1) # Thoát nếu không có quyền root

    motor = Dong_co() # Tạo một đối tượng động cơ
    print("Đã khởi tạo động cơ.")
except Exception as e:
    print(f"Lỗi khi khởi tạo động cơ: {e}. Đảm bảo các chân GPIO chính xác và bạn đang chạy với quyền root.")
    sys.exit(1) # Thoát nếu khởi tạo lỗi
# Hàm điều khiển
def dieu_khien():
# Phần thiết lập điều khiển động cơ
    if len(sys.argv) > 1:
        command = sys.argv[1] # Lấy đối số đầu tiên làm lệnh
        if command == "forward":    # Lệnh tiến
            motor.forward()
        elif command == "backward":  # Lệnh lùi
            motor.backward()
        elif command == "left":  # Lệnh rẽ trái
            motor.left()
        elif command == "right":  # Lệnh rẽ phải
            motor.right()
        elif command == "set_speed":  # Lệnh đặt tốc độ
            if len(sys.argv) > 3:
                left_speed = int(sys.argv[2])   # Lấy tốc độ cho động cơ trái (số thứ nhất)
                right_speed = int(sys.argv[3])  # Lấy tốc độ cho động cơ phải (số thứ hai)
                print(f"Đặt tốc độ: Trái={left_speed}%, Phải={right_speed}%")   # In ra tốc độ đã đặt
                motor.setMotor(left_speed, right_speed) # Cho động cơ chạy với tốc độ đã đặt
            else:
                print("Lỗi: Cần cung cấp tốc độ cho cả hai động cơ (trái và phải).")  # Thông báo lỗi nếu không đủ đối số
    else:
        motor.stop()  # Nếu không có lệnh, dừng động cơ
# Phần thiết lập điều khiển camera
