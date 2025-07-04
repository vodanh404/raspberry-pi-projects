import io
import logging
import socketserver
from threading import Condition
from http import server
import cv2 # Import OpenCV
import numpy as np # Import numpy for image array handling

PAGE="""\
<html>
<head>
<title>Raspberry Pi - Surveillance Camera (OpenCV)</title>
<style>
    body { font-family: 'Inter', sans-serif; background-color: #f0f0f0; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }
    h1 { color: #333; margin-bottom: 20px; }
    img { border: 5px solid #ccc; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 100%; height: auto; }
    center { text-align: center; }
</style>
</head>
<body>
<center><h1>Raspberry Pi - Surveillance Camera (OpenCV)</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

class StreamingOutput(object):
    """
    Lớp này xử lý việc lưu trữ các khung hình video và thông báo cho các client
    khi có khung hình mới.
    """
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        """
        Ghi dữ liệu khung hình vào bộ đệm.
        Khi một khung hình JPEG mới được phát hiện (bắt đầu bằng b'\xff\xd8'),
        nó sẽ sao chép nội dung bộ đệm hiện có, đặt nó làm khung hình hiện tại,
        và thông báo cho tất cả các client đang chờ.
        """
        if buf.startswith(b'\xff\xd8'):
            # Khung hình mới, sao chép nội dung của bộ đệm hiện có và thông báo
            # cho tất cả các client rằng nó đã có sẵn
            self.buffer.truncate() # Cắt bộ đệm về kích thước 0
            with self.condition:
                self.frame = self.buffer.getvalue() # Lấy giá trị của bộ đệm
                self.condition.notify_all() # Thông báo cho tất cả các client
            self.buffer.seek(0) # Đặt con trỏ về đầu bộ đệm
        return self.buffer.write(buf) # Ghi dữ liệu vào bộ đệm

class StreamingHandler(server.BaseHTTPRequestHandler):
    """
    Lớp này xử lý các yêu cầu HTTP từ client.
    Nó phục vụ trang HTML và luồng video MJPEG.
    """
    def do_GET(self):
        """
        Xử lý các yêu cầu GET.
        Chuyển hướng từ '/' sang '/index.html', phục vụ trang HTML,
        hoặc phục vụ luồng video MJPEG.
        """
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        # Chờ cho đến khi có khung hình mới
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    """
    Máy chủ truyền phát kế thừa từ ThreadingMixIn và HTTPServer
    để xử lý nhiều client đồng thời.
    """
    allow_reuse_address = True # Cho phép sử dụng lại địa chỉ
    daemon_threads = True # Cho phép các luồng daemon

# Khởi tạo OpenCV VideoCapture
# 0 là chỉ số mặc định cho camera tích hợp.
# Nếu bạn có nhiều camera hoặc camera USB, bạn có thể cần thay đổi chỉ số này (ví dụ: 1, 2, ...)
camera = cv2.VideoCapture(0)

# Đặt độ phân giải của camera (tùy chọn)
# Đảm bảo độ phân giải này khớp với độ phân giải trong HTML PAGE
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Kiểm tra xem camera đã được mở thành công chưa
if not camera.isOpened():
    print("Lỗi: Không thể mở camera.")
    exit()

output = StreamingOutput()

# Bắt đầu luồng ghi hình trong một luồng riêng biệt
import threading

def capture_frames():
    """
    Hàm này liên tục đọc khung hình từ camera OpenCV,
    mã hóa chúng thành JPEG và ghi vào StreamingOutput.
    """
    while True:
        ret, frame = camera.read() # Đọc một khung hình từ camera
        if not ret:
            print("Lỗi: Không thể đọc khung hình.")
            break

        # Mã hóa khung hình thành JPEG
        # Tham số thứ hai là chất lượng JPEG (0-100), 90 là giá trị tốt
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ret:
            print("Lỗi: Không thể mã hóa khung hình thành JPEG.")
            continue

        # Ghi khung hình JPEG vào bộ đệm đầu ra
        output.write(jpeg.tobytes())

# Bắt đầu luồng chụp khung hình
frame_capture_thread = threading.Thread(target=capture_frames)
frame_capture_thread.daemon = True # Đặt luồng là daemon để nó tự động thoát khi chương trình chính thoát
frame_capture_thread.start()

try:
    address = ('', 8160) # Địa chỉ máy chủ và cổng
    server = StreamingServer(address, StreamingHandler) # Khởi tạo máy chủ truyền phát
    print(f"Máy chủ đang chạy trên cổng {address[1]}...")
    server.serve_forever() # Bắt đầu máy chủ và phục vụ vô thời hạn
finally:
    camera.release() # Giải phóng camera khi kết thúc
    print("Camera đã được giải phóng.")
