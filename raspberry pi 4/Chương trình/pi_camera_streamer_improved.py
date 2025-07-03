import cv2
import socket
import struct
import pickle
import time

SERVER_IP = '0.0.0.0'
SERVER_PORT = 8000
CAMERA_INDEX = 0
RESOLUTION_WIDTH = 640
RESOLUTION_HEIGHT = 480
JPEG_QUALITY = 85

def start_stream():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((SERVER_IP, SERVER_PORT))
        server_socket.listen(1)
        print(f"[{time.strftime('%H:%M:%S')}] Đang chờ client kết nối trên {SERVER_IP}:{SERVER_PORT}...")
        conn, addr = server_socket.accept()
        print(f"[{time.strftime('%H:%M:%S')}] Client đã kết nối từ: {addr}")

        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            print(f"[{time.strftime('%H:%M:%S')}] Lỗi: Không thể mở camera với chỉ số {CAMERA_INDEX}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION_HEIGHT)
        print(f"[{time.strftime('%H:%M:%S')}] Bắt đầu streaming camera ({RESOLUTION_WIDTH}x{RESOLUTION_HEIGHT})...")

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"[{time.strftime('%H:%M:%S')}] Không thể đọc frame từ camera.")
                time.sleep(0.1)
                continue

            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            data = pickle.dumps(buffer)
            size = struct.pack("!L", len(data))

            try:
                conn.sendall(size + data)
            except (BrokenPipeError, ConnectionResetError) as e:
                print(f"[{time.strftime('%H:%M:%S')}] Client đã ngắt kết nối: {e}")
                break
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Lỗi khi gửi dữ liệu: {e}")
                break

    except socket.error as e:
        print(f"[{time.strftime('%H:%M:%S')}] Lỗi socket: {e}. Đảm bảo cổng {SERVER_PORT} không bị sử dụng.")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Đã xảy ra lỗi không xác định: {e}")
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
            print(f"[{time.strftime('%H:%M:%S')}] Camera đã được giải phóng.")
        if 'conn' in locals():
            conn.close()
            print(f"[{time.strftime('%H:%M:%S')}] Kết nối client đã đóng.")
        server_socket.close()
        print(f"[{time.strftime('%H:%M:%S')}] Socket server đã đóng.")
        print(f"[{time.strftime('%H:%M:%S')}] Streaming đã dừng.")

if __name__ == '__main__':
    start_stream()
