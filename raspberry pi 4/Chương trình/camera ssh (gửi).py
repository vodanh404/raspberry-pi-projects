import socket
import cv2
import pickle
import struct

# Khởi tạo socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '192.168.0.106'  # Thay đổi thành IP của máy chủ nếu không phải localhost
port = 9999
client_socket.connect((host_ip, port))
print(f"Đã kết nối tới máy chủ {host_ip}:{port}")

# Khởi tạo webcam
cap = cv2.VideoCapture(0)  # 0 cho webcam mặc định

if not cap.isOpened():
    print("Không thể mở webcam")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Không thể đọc khung hình từ webcam.")
        break

    # Mã hóa khung hình sang định dạng JPEG
    # Tham số thứ hai là chất lượng JPEG (0-100), ví dụ 80
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    
    # Chuyển đổi buffer thành bytes
    data = pickle.dumps(buffer)

    # Đóng gói kích thước dữ liệu và gửi
    message_size = struct.pack("L", len(data))
    client_socket.sendall(message_size + data)

    # Hiển thị khung hình gốc (tùy chọn)
    cv2.imshow('Client Camera', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

print("Đang đóng kết nối client...")
client_socket.close()
cap.release()
cv2.destroyAllWindows()
