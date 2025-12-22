import os
import sys
import time
import subprocess
import threading
import signal
import datetime
import pygame
import board
import busio
import math
from PIL import Image, ImageFont, ImageDraw, ImageOps
from luma.core.interface.serial import spi as luma_spi
from luma.lcd.device import st7789
from xpt2046 import XPT2046

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & ĐƯỜNG DẪN
# ==========================================
WIDTH, HEIGHT = 320, 240
BG_COLOR = "#1e1e2e" 
ACCENT_COLOR = "#89b4fa"
TEXT_COLOR = "#cdd6f4"
WARN_COLOR = "#f38ba8"

USER_HOME = "/home/dinhphuc"
DIRS = {
    "MUSIC": os.path.join(USER_HOME, "Music"),
    "VIDEO": os.path.join(USER_HOME, "Videos"),
    "PHOTO": os.path.join(USER_HOME, "Pictures"),
    "BOOK":  os.path.join(USER_HOME, "Documents")
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

font_icon, font_lg, font_md, font_sm = load_font(24), load_font(18), load_font(14), load_font(10)

def emergency_cleanup():
    """Dọn dẹp các tiến trình đa phương tiện"""
    subprocess.run(["pkill", "-9", "ffplay"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "ffmpeg"], stderr=subprocess.DEVNULL)
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()

# ==========================================
# 2. KHỞI TẠO PHẦN CỨNG (LCD & TOUCH)
# ==========================================
try:
    serial_lcd = luma_spi(port=0, device=0, gpio_DC=24, gpio_RST=25, baudrate=60000000)
    # SỬA LỖI ÂM BẢN: inversion=True (Nếu vẫn bị thì đổi thành False)
    device = st7789(serial_lcd, width=WIDTH, height=HEIGHT, rotate=0, inversion=True)
    device.backlight(True)

    spi_touch = busio.SPI(board.SCLK_1, board.MOSI_1, board.MISO_1)
    touch = XPT2046(spi_touch, cs_pin=board.D17, irq_pin=board.D26,
                    width=WIDTH, height=HEIGHT, 
                    x_min=100, x_max=1962, y_min=100, y_max=1900, 
                    baudrate=2000000)
except Exception as e:
    print(f"Hardware Error: {e}"); sys.exit(1)

pygame.mixer.init()

# ==========================================
# 3. CLASS CHÍNH: PI MEDIA CENTER
# ==========================================
class PiMediaCenter:
    def __init__(self):
        self.state = "MENU"
        self.running = True
        self.files = []
        self.selected_idx = 0
        self.scroll_offset = 0
        self.last_touch = 0
        self.volume = 0.5
        self.bt_scanning = False

    def draw_status_bar(self, draw):
        draw.rectangle((0, 0, WIDTH, 24), fill="#313244")
        time_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((WIDTH - 45, 5), time_str, fill="white", font=font_sm)
        draw.text((10, 5), f"Vol: {int(self.volume*100)}%", fill="white", font=font_sm)

    def draw_button(self, draw, x, y, w, h, text, bg_color="#45475a", text_color="white"):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=5, fill=bg_color)
        bbox = draw.textbbox((0, 0), text, font=font_md)
        draw.text((x + (w-(bbox[2]-bbox[0]))/2, y + (h-(bbox[3]-bbox[1]))/2 - 2), text, fill=text_color, font=font_md)

    def draw_menu(self, draw):
        self.draw_status_bar(draw)
        draw.text((WIDTH//2 - 65, 35), "PI MEDIA CENTER", fill=ACCENT_COLOR, font=font_lg)
        items = [("Nhạc", "♫", "#f9e2af"), ("Video", "►", "#f38ba8"), ("Ảnh", "🖼", "#a6e3a1"), ("Sách", "📖", "#89b4fa"), ("BT", "ᛒ", "#cba6f7")]
        start_x, start_y, btn_w, btn_h, gap = 25, 75, 85, 65, 12
        for i, (label, icon, color) in enumerate(items):
            row, col = i // 3, i % 3
            x, y = start_x + col*(btn_w+gap), start_y + row*(btn_h+gap)
            draw.rounded_rectangle((x, y, x+btn_w, y+btn_h), radius=8, fill="#313244", outline=color, width=2)
            draw.text((x + 32, y + 10), icon, fill=color, font=font_icon)
            draw.text((x + (btn_w - font_sm.getlength(label))/2, y + 42), label, fill="white", font=font_sm)

    def draw_list(self, draw, title):
        self.draw_status_bar(draw)
        draw.rectangle((0, 24, WIDTH, 50), fill="#45475a")
        draw.text((10, 28), title, fill="yellow", font=font_md)
        self.draw_button(draw, WIDTH-60, 26, 50, 22, "BACK", bg_color=WARN_COLOR)
        
        if self.bt_scanning:
            draw.text((WIDTH//2 - 50, 110), "Scanning BT...", fill="lime", font=font_md)
        elif not self.files:
            draw.text((WIDTH//2 - 40, 110), "Trống", fill="grey", font=font_md)
        else:
            list_y, item_h = 55, 28
            display_list = self.files[self.scroll_offset : self.scroll_offset + 5]
            for i, item in enumerate(display_list):
                idx = self.scroll_offset + i
                is_sel = (idx == self.selected_idx)
                name = item['name'] if isinstance(item, dict) else item
                draw.rectangle((5, list_y + i*item_h, WIDTH-5, list_y + (i+1)*item_h - 2), fill="#585b70" if is_sel else BG_COLOR)
                draw.text((15, list_y + i*item_h + 5), f"{'>' if is_sel else ' '} {name[:25]}", fill="cyan" if is_sel else "white", font=font_md)

        self.draw_button(draw, 10, 205, 90, 30, "LÊN")
        self.draw_button(draw, 115, 205, 90, 30, "CHỌN", bg_color="#a6e3a1", text_color="black")
        self.draw_button(draw, 220, 205, 90, 30, "XUỐNG")

    def draw_playing_music(self, draw):
        self.draw_status_bar(draw)
        song = self.files[self.selected_idx] if self.files else "Unknown"
        draw.text((20, 60), f"Đang phát:\n{song[:25]}", fill="yellow", font=font_md)
        
        # Sóng nhạc giả lập
        for i in range(10):
            h = math.sin(time.time()*5 + i) * 20 + 25
            draw.rectangle((60 + i*20, 150-h, 75 + i*20, 150), fill=ACCENT_COLOR)

        # NÚT ĐIỀU KHIỂN ĐẦY ĐỦ
        self.draw_button(draw, 10, 185, 70, 40, "VOL -")
        self.draw_button(draw, 85, 185, 70, 40, "PAUSE")
        self.draw_button(draw, 160, 185, 70, 40, "VOL +")
        self.draw_button(draw, 235, 185, 75, 40, "EXIT", bg_color=WARN_COLOR)

    def play_video_stream(self, filepath):
        self.state = "PLAYING_VIDEO"
        emergency_cleanup()
        # Chạy âm thanh
        audio_proc = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-volume', str(int(self.volume*100)), filepath], stdout=subprocess.DEVNULL)
        # Chạy hình ảnh (FFmpeg scale về 320x240)
        video_cmd = ['ffmpeg', '-re', '-i', filepath, '-vf', f'scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-loglevel', 'quiet', '-']
        video_proc = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, bufsize=WIDTH*HEIGHT*3)
        
        try:
            while True:
                raw = video_proc.stdout.read(WIDTH * HEIGHT * 3)
                if not raw or touch.is_touched(): break
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw)
                device.display(img)
        finally:
            audio_proc.terminate(); video_proc.terminate(); emergency_cleanup()
            self.state = "VIDEO"; self.render()

    def scan_bt(self):
        self.bt_scanning = True; self.render()
        try:
            subprocess.run(["bluetoothctl", "scan", "on"], timeout=3, stdout=subprocess.DEVNULL)
            out = subprocess.check_output(["bluetoothctl", "devices"]).decode("utf-8")
            self.files = [{"mac": l.split(' ')[1], "name": l.split(' ', 2)[2]} for l in out.strip().split('\n') if "Device" in l]
        except: self.files = []
        self.bt_scanning = False; self.render()

    def handle_touch(self, x, y):
        now = time.time()
        if now - self.last_touch < 0.3: return
        self.last_touch = now

        if self.state == "MENU":
            if 75 <= y <= 210:
                col, row = (x - 25) // 97, (y - 75) // 77
                idx = int(row * 3 + col)
                if idx == 0: self.state = "MUSIC"; self.load_files("MUSIC", ".mp3")
                elif idx == 1: self.state = "VIDEO"; self.load_files("VIDEO", ".mp4")
                elif idx == 2: self.state = "PHOTO"; self.load_files("PHOTO", ".jpg")
                elif idx == 4: self.state = "BT"; threading.Thread(target=self.scan_bt, daemon=True).start()

        elif self.state == "PLAYING_MUSIC":
            if y > 180:
                if x < 80: # VOL -
                    self.volume = max(0, self.volume - 0.1); pygame.mixer.music.set_volume(self.volume)
                elif 85 < x < 155: # PAUSE
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.pause()
                    else: pygame.mixer.music.unpause()
                elif 160 < x < 230: # VOL +
                    self.volume = min(1.0, self.volume + 0.1); pygame.mixer.music.set_volume(self.volume)
                elif x > 235: # EXIT
                    pygame.mixer.music.stop(); self.state = "MUSIC"

        elif self.state in ["MUSIC", "VIDEO", "PHOTO", "BT"]:
            if x > WIDTH-60 and y < 50: self.state = "MENU"
            elif y > 200:
                if x < 100: self.selected_idx = max(0, self.selected_idx - 1)
                elif x > 220: self.selected_idx = min(len(self.files)-1, self.selected_idx + 1)
                elif 115 < x < 205 and self.files:
                    path = os.path.join(DIRS.get(self.state, ""), self.files[self.selected_idx])
                    if self.state == "MUSIC":
                        pygame.mixer.music.load(path); pygame.mixer.music.play(); self.state = "PLAYING_MUSIC"
                    elif self.state == "VIDEO":
                        threading.Thread(target=self.play_video_stream, args=(path,), daemon=True).start()
        self.render()

    def load_files(self, key, ext):
        try: self.files = sorted([f for f in os.listdir(DIRS[key]) if f.lower().endswith(ext)])
        except: self.files = []
        self.selected_idx = 0

    def render(self):
        if self.state == "PLAYING_VIDEO": return
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        if self.state == "MENU": self.draw_menu(draw)
        elif self.state == "PLAYING_MUSIC": self.draw_playing_music(draw)
        else: self.draw_list(draw, self.state)
        device.display(img)

    def run(self):
        self.render()
        while self.running:
            p = touch.get_touch()
            if p: self.handle_touch(p[0], p[1])
            if self.state == "PLAYING_MUSIC": self.render()
            time.sleep(0.1)

if __name__ == "__main__":
    PiMediaCenter().run()
