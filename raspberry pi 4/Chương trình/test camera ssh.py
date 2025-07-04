# Sender Code
import cv2
import socket
import pickle
import struct

# Sender Code
def send_video():
    # Initialize the camera
    cap = cv2.VideoCapture(0)

    # Create a socket connection
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('192.168.0.106', 8080))  # Replace with your server's IP and port

    while True:
        # Read a frame from the camera
        ret, frame = cap.read()

        # Serialize the frame
        data = pickle.dumps(frame)

        # Pack the frame size (as a 4-byte integer) and frame data
        message = struct.pack("Q", len(data)) + data

        # Send the frame to the server
        client_socket.sendall(message)

        # Display the frame locally (optional)
        cv2.imshow('Sender', frame)
        cv2.waitKey(1)

    cap.release()
