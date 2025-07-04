import os
import asyncio
import fractions
import subprocess
import numpy as np
import cv2
import pyaudio
import logging
from datetime import datetime
from av import VideoFrame, AudioFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, AudioStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("webrtc")

# Cấu hình từ biến môi trường hoặc mặc định
VIDEO_DEVICE = os.getenv("VIDEO_DEVICE", "/dev/video0")
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", 640))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", 480))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", 15))
SIGNALING_IP = os.getenv("SIGNALING_IP", "192.168.0.106")
SIGNALING_PORT = int(os.getenv("SIGNALING_PORT", 9999))

# Track video từ FFmpeg
class FFmpegVideoStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT
        self.fps = VIDEO_FPS
        self.time_base = fractions.Fraction(1, self.fps)
        self.frame_count = 0
        self.process = None # Khởi tạo process là None

        try:
            self.process = subprocess.Popen(
                [
                    'ffmpeg',
                    '-f', 'v4l2',
                    '-framerate', str(self.fps),
                    '-video_size', f'{self.width}x{self.height}',
                    '-i', VIDEO_DEVICE,
                    '-f', 'rawvideo',
                    '-pix_fmt', 'rgb24',
                    'pipe:1'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except FileNotFoundError:
            logger.exception("FFmpeg không được tìm thấy. Hãy đảm bảo FFmpeg đã được cài đặt và có trong PATH.")
            raise FileNotFoundError("FFmpeg không được tìm thấy.")
        except Exception as e:
            logger.exception(f"Lỗi khi khởi động FFmpeg: {e}")
            raise RuntimeError(f"Lỗi khi khởi động FFmpeg: {e}")

    async def recv(self):
        # Kiểm tra trạng thái của tiến trình FFmpeg
        if self.process.poll() is not None:
            error_output = self.process.stderr.read().decode().strip()
            if error_output:
                logger.error(f"FFmpeg process exited with error: {error_output}")
            else:
                logger.error("FFmpeg process exited unexpectedly without error output.")
            raise RuntimeError("FFmpeg process exited unexpectedly.")

        raw_frame = None
        for _ in range(5): # Thử đọc 5 lần trước khi báo lỗi
            raw_frame = self.process.stdout.read(self.width * self.height * 3)
            if raw_frame:
                break
            logger.warning("Không nhận được dữ liệu khung hình từ FFmpeg. Đang đợi và thử lại...")
            await asyncio.sleep(0.05)
            
        if not raw_frame:
            logger.error("Không thể đọc khung hình từ FFmpeg sau nhiều lần thử.")
            raise RuntimeError("Không thể đọc khung hình từ FFmpeg.")

        frame = np.frombuffer(raw_frame, np.uint8).reshape((self.height, self.width, 3))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Thêm timestamp vào khung hình
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.putText(frame_bgr, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = self.time_base
        self.frame_count += 1
        return video_frame

    def __del__(self):
        if hasattr(self, 'process') and self.process is not None and self.process.poll() is None:
            logger.info("Đang chấm dứt FFmpeg process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg process không kết thúc. Đang kill...")
                self.process.kill()
            logger.info("FFmpeg process đã được chấm dứt.")

# Track âm thanh từ micro
class MicrophoneAudioTrack(AudioStreamTrack):
    def __init__(self):
        super().__init__()
        self.p = None # Khởi tạo p là None
        self.stream = None # Khởi tạo stream là None
        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=pyaudio.paInt16,
                                     channels=1,
                                     rate=48000,
                                     input=True,
                                     frames_per_buffer=960)
            logger.info("Đã khởi tạo MicrophoneAudioTrack.")
        except Exception as e:
            logger.exception(f"Lỗi khi khởi tạo PyAudio: {e}")
            # Đảm bảo đóng nếu đã mở một phần
            if self.stream:
                self.stream.close()
            if self.p:
                self.p.terminate()
            raise RuntimeError(f"Lỗi khi khởi tạo PyAudio: {e}")

    async def recv(self):
        try:
            # PyAudio có thể gây tràn bộ đệm nếu không đọc đủ nhanh.
            # exception_on_overflow=False tránh lỗi, nhưng có thể bỏ qua dữ liệu.
            data = self.stream.read(960, exception_on_overflow=False)
            audio_frame = AudioFrame.from_ndarray(np.frombuffer(data, dtype=np.int16), format="s16", layout="mono")
            audio_frame.sample_rate = 48000
            return audio_frame
        except IOError as e:
            # PyAudio có thể ném IOError nếu thiết bị không khả dụng nữa
            logger.error(f"Lỗi I/O âm thanh (thiết bị có thể đã bị ngắt kết nối): {e}")
            raise # Ném lỗi để báo hiệu luồng âm thanh đã mất
        except Exception as e:
            logger.error(f"Lỗi khi đọc dữ liệu âm thanh: {e}")
            return None # Trả về None để AIORTC biết không có khung hình

    def __del__(self):
        if hasattr(self, 'stream') and self.stream is not None and self.stream.is_active():
            logger.info("Đang dừng stream micro...")
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'p') and self.p is not None:
            logger.info("Đang chấm dứt PyAudio...")
            self.p.terminate()
        logger.info("Microphone stream đã được đóng.")

# Thiết lập WebRTC
async def setup_webrtc_and_run(ip_address, port):
    signaling = TcpSocketSignaling(ip_address, port)
    
    # Cấu hình ICE servers để hỗ trợ kết nối NAT/firewall
    pc = RTCPeerConnection(
        iceServers=[
            {"urls": "stun:stun.l.google.com:19302"},
            # Thêm các máy chủ TURN nếu cần để giải quyết các trường hợp NAT phức tạp hơn
            # {"urls": "turn:your_turn_server.com:3478", "username": "user", "credential": "password"}
        ]
    )

    video_track = None
    audio_track = None

    try:
        video_track = FFmpegVideoStreamTrack()
        audio_track = MicrophoneAudioTrack()

        pc.addTrack(video_track)
        pc.addTrack(audio_track)

        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate:
                logger.info(f"Đã tạo ICE candidate: {candidate.sdpMid} {candidate.sdpMLineIndex} {candidate.candidate}")
                await signaling.send(candidate)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Trạng thái kết nối WebRTC: {pc.connectionState}")
            if pc.connectionState in ["failed", "disconnected", "closed"]:
                logger.warning("Kết nối WebRTC bị lỗi, ngắt hoặc đóng. Đang chấm dứt...")
                # Gọi close cho pc và signaling sẽ kích hoạt finaly block
                await pc.close()
                await signaling.close()

        logger.info(f"Đang kết nối đến máy chủ tín hiệu {ip_address}:{port}...")
        await signaling.connect()
        logger.info("Đã kết nối Signaling thành công.")

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await signaling.send(pc.localDescription)
        logger.info("Đã gửi Offer.")

        while True:
            obj = await signaling.receive()
            if isinstance(obj, RTCSessionDescription):
                logger.info(f"Đã nhận RemoteDescription: {obj.type}")
                await pc.setRemoteDescription(obj)
                if obj.type == "offer":
                    logger.info("Đã nhận Offer, đang tạo Answer...")
                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)
                    await signaling.send(pc.localDescription)
                    logger.info("Đã gửi Answer.")
            elif isinstance(obj, type(pc.iceGatheringState)): # Đây là cách nhận diện RTCIceCandidate từ signaling
                logger.info(f"Đã nhận ICE candidate từ remote: {obj.candidate}")
                await pc.addIceCandidate(obj)
            elif obj is None:
                logger.info("Máy chủ báo hiệu đã đóng kết nối.")
                break
            
            # Thoát vòng lặp nếu kết nối WebRTC đã bị đóng
            if pc.connectionState == "closed":
                break

            await asyncio.sleep(0.1) # Ngăn chặn vòng lặp chạy quá nhanh

    except Exception as e:
        logger.exception(f"Lỗi nghiêm trọng trong quá trình WebRTC: {e}")
    finally:
        logger.info("Đang thực hiện clean-up cuối cùng...")
        if video_track:
            video_track.__del__() # Gọi tường minh để đảm bảo đóng tiến trình
        if audio_track:
            audio_track.__del__() # Gọi tường minh để đảm bảo đóng luồng
        
        # Đảm bảo PC và signaling được đóng an toàn
        if pc.connectionState != "closed":
            await pc.close()
        if signaling.connected: # Kiểm tra thuộc tính .connected để tránh lỗi khi đã đóng
            await signaling.close()
        logger.info("Tất cả kết nối đã được đóng.")

# Chạy chương trình
async def main():
    try:
        await setup_webrtc_and_run(SIGNALING_IP, SIGNALING_PORT)
    except Exception as e:
        logger.critical(f"Ứng dụng gặp lỗi nghiêm trọng và sẽ thoát: {e}")
    finally:
        logger.info("Ứng dụng đã kết thúc.")

if __name__ == "__main__":
    asyncio.run(main())
