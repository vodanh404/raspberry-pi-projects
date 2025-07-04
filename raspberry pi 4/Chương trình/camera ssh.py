import socket
import cv2
import pickle
import struct

# Khởi tạo socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '192.168.0.106'  # Thay đổi thành IP của máy chủ
port = 9999
server_socket.bind((host_ip, port))

# Lắng nghe kết nối (tối đa 5 kết nối đang chờ)
server_socket.listen(5)
print(f"Máy chủ đang lắng nghe trên {host_ip}:{port}")

conn, addr = server_socket.accept()
print(f"Đã kết nối từ: {addr}")

data = b""
payload_size = struct.calcsize("L") # Kích thước của biến L (unsigned long)

while True:
    while len(data) < payload_size:
        packet = conn.recv(4*1024)  # Đọc một gói 4KB
        if not packet:
            break
        data += packet

    if not packet:
        break

    # Tách kích thước tin nhắn
    packed_msg_size = data[:payload_size]
    data = data[payload_size:]
    msg_size = struct.unpack("L", packed_msg_size)[0]

    # Đọc hết dữ liệu hình ảnh
    while len(data) < msg_size:
        data += conn.recv(4*1024)

    frame_data = data[:msg_size]
    data = data[msg_size:]

    # Giải nén dữ liệu hình ảnh
    frame_buffer = pickle.loads(frame_data)
    frame = cv2.imdecode(frame_buffer, cv2.IMREAD_COLOR)

    # Hiển thị khung hình
    cv2.imshow('Server Stream', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

print("Đang đóng kết nối server...")
conn.close()
server_socket.close()
cv2.destroyAllWindows()
