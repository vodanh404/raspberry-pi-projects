import os
import time
import subprocess
import signal
import sys
import threading
import pygame
import board
import busio
import digitalio
from PIL import Image, ImageFont
from luma.core.interface.serial import spi as luma_spi
from luma.lcd.device import st7789
from xpt2046 import XPT2046

# --- Cấu hình Hardware ---
WIDTH = 320
HEIGHT = 240
SERIAL_SPEED = 40000000
CS_TOUCH = board.D7  # Kiểm tra chân CS của XPT2046 trên board của bạn
IRQ_TOUCH = board.D17 # Chân IRQ của XPT2046

class MultiMediaPlayer:
    def __init__(self):
        # 1. Khởi tạo Hiển thị ST7789
        self.serial = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=SERIAL_SPEED)
        self.device = st7789(self.serial, width=WIDTH, height=HEIGHT, rotate=0, framebuffer="full_frame")
        
        # 2. Khởi tạo Cảm ứng XPT2046
        self.spi_bus = busio.SPI(board.SCK, board.MOSI, board.MISO)
        self.touch = XPT2046(self.spi_bus, CS_TOUCH, IRQ_TOUCH, width=WIDTH, height=HEIGHT)
        self.touch.set_handler(self.handle_touch)

        # 3. Đường dẫn Media
        self.video_path = "/home/dinhphuc/Videos/test.mp4"
        self.music_dir = "/home/dinhphuc/Music"
        self.music_files = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')] if os.path.exists(self.music_dir) else []
        
        # 4. Trạng thái ứng dụng
        self.mode = "MENU" # MENU, MUSIC, VIDEO
        self.is_running = True
        self.video_proc = None
        self.audio_proc = None
        
        # Font
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        self.font = ImageFont.truetype(font_path, 20)

        pygame.mixer.init()

    def emergency_cleanup(self):
        """Dừng tất cả các tiến trình FFmpeg và FFplay."""
        os.system("pkill -9 ffplay")
        os.system("pkill -9 ffmpeg")
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    def handle_touch(self, x, y):
        """Xử lý chạm dựa trên chế độ hiện tại."""
        if self.mode == "MENU":
            if y < 120: 
                self.mode = "MUSIC"
                self.start_music()
            else:
                self.mode = "VIDEO"
                self.start_video()
        
        elif self.mode == "VIDEO" or self.mode == "MUSIC":
            # Chạm vào góc trên cùng bên trái để quay lại Menu
            if x < 50 and y < 50:
                self.stop_all()
                self.mode = "MENU"
                self.draw_menu()

    def stop_all(self):
        self.emergency_cleanup()
        self.is_playing_video = False

    def draw_menu(self):
        with canvas(self.device) as draw:
            draw.rectangle((0, 0, 320, 120), fill="blue", outline="white")
            draw.text((100, 45), "NGHE NHẠC", font=self.font, fill="white")
            
            draw.rectangle((0, 120, 320, 240), fill="red", outline="white")
            draw.text((100, 165), "XEM VIDEO", font=self.font, fill="white")

    def start_music(self):
        if self.music_files:
            track = os.path.join(self.music_dir, self.music_files[0])
            pygame.mixer.music.load(track)
            pygame.mixer.music.play()
            with canvas(self.device) as draw:
                draw.text((10, 100), f"Playing: {self.music_files[0]}", font=self.font, fill="green")
                draw.text((10, 200), "<-- Back to Menu", font=self.font, fill="white")

    def start_video(self):
        # Chạy video trong một luồng riêng để không làm treo cảm ứng
        video_thread = threading.Thread(target=self.play_video_logic)
        video_thread.start()

    def play_video_logic(self):
        self.is_playing_video = True
        frame_size = WIDTH * HEIGHT * 3
        
        video_command = [
            'ffmpeg', '-re', '-i', self.video_path,
            '-vf', f'scale={WIDTH}:{HEIGHT}', '-f', 'rawvideo',
            '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-'
        ]
        
        self.video_proc = subprocess.Popen(video_command, stdout=subprocess.PIPE, bufsize=frame_size * 2)
        self.audio_proc = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', self.video_path])

        try:
            while self.mode == "VIDEO" and self.is_running:
                raw_frame = self.video_proc.stdout.read(frame_size)
                if len(raw_frame) != frame_size:
                    break
                
                image = Image.frombytes('RGB', (WIDTH, HEIGHT), raw_frame)
                self.device.display(image)
        finally:
            self.stop_all()

    def run(self):
        self.draw_menu()
        try:
            while self.is_running:
                self.touch.poll()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_all()
            sys.exit(0)

if __name__ == "__main__":
    player = MultiMediaPlayer()
    player.run()
