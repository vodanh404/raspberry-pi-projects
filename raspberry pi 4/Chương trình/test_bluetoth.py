from bluedot import BlueDot
import cv2, threading, time

bd = BlueDot()
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

recording, frame_counter, last_frame = False, 0, None

def handle_dot_pressed(pos):
    global recording, frame_counter, last_frame
    recording = not recording
    print("Bắt đầu ghi hình..." if recording else "Dừng ghi hình.")
    if last_frame is not None:
        filename = f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, last_frame)
        print(f"Đã lưu ảnh: {filename}")

def handle_dot_released(): print("Nút thả.")
def handle_dot_moved(pos): print(f"Di chuyển: {pos.x}, {pos.y}")

bd.when_pressed = handle_dot_pressed
bd.when_released = handle_dot_released
bd.when_moved = handle_dot_moved

def camera_loop():
    global recording, frame_counter, last_frame
    while True:
        ret, frame = cap.read()
        if not ret: break
        last_frame = frame.copy()
        cv2.imshow('Camera', frame)
        if recording: frame_counter += 1
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()

threading.Thread(target=camera_loop, daemon=True).start()

try:
    print("Chờ sự kiện từ Blue Dot...")
    while True: time.sleep(1)
except KeyboardInterrupt:
    print("Ngắt bởi người dùng.")
    cap.release()
    cv2.destroyAllWindows()
