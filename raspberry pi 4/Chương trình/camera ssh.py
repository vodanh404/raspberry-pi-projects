import cv2
import socket
import pickle
import struct

# Initialize video capture from the default camera
video_capture = cv2.VideoCapture(0)

# Create a socket server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('192.168.1.100', 9999))  # Replace with the server's IP address
server_socket.listen(10)

# Accept a client connection
client_socket, client_address = server_socket.accept()
print(f"[*] Accepted connection from {client_address}")

while True:
    # Read a frame from the camera
    ret, frame = video_capture.read()

    # Serialize the frame to bytes
    serialized_frame = pickle.dumps(frame)

    # Pack the data size and frame data
    message_size = struct.pack("L", len(serialized_frame))
    client_socket.sendall(message_size + serialized_frame)

    # Display the frame on the server-side (optional)
    cv2.imshow('Server Video', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
video_capture.release()
cv2.destroyAllWindows()
