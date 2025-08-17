# phat_nhac.py 
import utime 
import urandom 
from machine import I2C, Pin, SPI 
from dfplayermini import DFPlayerMini 
from DIYables_Pico_Keypad import Keypad 
from st7735 import sysfont 

 # Thiết lập bàn phím 
NUM_ROWS = 4 
NUM_COLS = 4 
ROW_PINS = [9, 8, 7, 6] 
COLUMN_PINS = [5, 4, 3, 2] 
KEYMAP = ['1', '2', '3', '+','4', '5', '6', '-','7', '8', '9', 'x','AC', '0', '=', ':'] 
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS) 
keypad.set_debounce_time(200) 

 # Khởi tạo các biến trạng thái ở mức toàn cục 
am_luong = 15 
bai_hat = 1 
MAX_BAI_HAT = 135 
MIN_BAI_HAT = 1 
trang_thai_phat = False # False: Đang phát, True: Đã tạm dừng 
che_do_ngau_nhien = False 

 # Khởi tạo giá trị hiển thị trước đó để so sánh (giúp màn hình ổn định) 
prev_am_luong = -1 
prev_bai_hat = -1 
prev_trang_thai_phat = None 
prev_che_do_ngau_nhien = None 

def update_tft(tft_obj, bg_color, text_color): 
    """Cập nhật thông tin máy nghe nhạc lên màn hình TFT.""" 
    global prev_am_luong, prev_bai_hat, prev_trang_thai_phat, prev_che_do_ngau_nhien 
     
    if (am_luong != prev_am_luong or bai_hat != prev_bai_hat or trang_thai_phat != prev_trang_thai_phat or che_do_ngau_nhien != prev_che_do_ngau_nhien): 
         
        tft_obj.fill(bg_color) 
         
        tft_obj.text((10, 10), f"Vol: {am_luong:02d}", text_color, sysfont.sysfont, 1) 
        tft_obj.text((10, 30), f"Bai: {bai_hat:03d}", text_color, sysfont.sysfont, 1) 
         
        if not trang_thai_phat: 
            tft_obj.text((10, 50), "Trang thai: Playing", text_color, sysfont.sysfont, 1) 
        else: 
            tft_obj.text((10, 50), "Trang thai: Paused", text_color, sysfont.sysfont, 1) 

        mode_text = "Mode: Ngau nhien" if che_do_ngau_nhien else "Mode: Binh thuong" 
        tft_obj.text((10, 70), mode_text, text_color, sysfont.sysfont, 1) 
         
         # Cập nhật giá trị "trước đó" 
        prev_am_luong = am_luong 
        prev_bai_hat = bai_hat 
        prev_trang_thai_phat = trang_thai_phat 
        prev_che_do_ngau_nhien = che_do_ngau_nhien 
def run_music_player(tft_obj, button_select_pin, bg_color, text_color): 
    """Vòng lặp chính để điều khiển máy nghe nhạc.""" 
    global am_luong, bai_hat, trang_thai_phat, che_do_ngau_nhien 

     # --- 1. Thiết lập ban đầu và RESET các biến --- 
     # Reset các biến trạng thái về mặc định 
    am_luong = 15 
    bai_hat = 1 
    trang_thai_phat = False # Đang phát 
    che_do_ngau_nhien = False 
     
     # Reset các biến so sánh 
    global prev_am_luong, prev_bai_hat, prev_trang_thai_phat, prev_che_do_ngau_nhien 
    prev_am_luong = -1 
    prev_bai_hat = -1 
    prev_trang_thai_phat = None 
    prev_che_do_ngau_nhien = None 

     # Khởi tạo và kiểm tra DFPlayerMini bên trong hàm để đảm bảo hoạt động 
    player1 = DFPlayerMini(0, 12, 13)  
    if not player1.select_source('sdcard'): 
        tft_obj.fill(bg_color) 
        tft_obj.text((10, 10), "MP3 Player Error", text_color, sysfont.sysfont, 1) 
        utime.sleep(2) 
        return 
      
     # Cài đặt âm lượng và phát bài hát đầu tiên 
    player1.set_volume(am_luong) 
    player1.play(bai_hat) 
      
     # Cập nhật màn hình một lần với trạng thái ban đầu 
     # Gọi hàm update_tft sau khi đã reset các biến prev và thiết lập lại các biến chính 
    update_tft(tft_obj, bg_color, text_color) 

    while True: 
         # Kiểm tra nút bấm vật lý để thoát ứng dụng 
        if button_select_pin.value() == 0: 
            utime.sleep_ms(50) # Chống dội 
            if button_select_pin.value() == 0: 
                while button_select_pin.value() == 0: # Chờ nhả nút 
                    utime.sleep_ms(50) 
                player1.stop() # Dừng hẳn nhạc khi thoát 
                break # Thoát khỏi vòng lặp 

         # Đọc phím từ keypad 
        key = keypad.get_key() 
          
         # Chỉ xử lý khi có phím được nhấn 
        if key: 
            should_update_tft = False 
              
            if key == '+': # Tăng âm lượng 
                if am_luong < 30: 
                    am_luong += 1 
                    player1.set_volume(am_luong) 
                    should_update_tft = True 
              
            elif key == '-': # Giảm âm lượng 
                if am_luong > 0: 
                    am_luong -= 1 
                    player1.set_volume(am_luong) 
                    should_update_tft = True 
              
            elif key == 'x': # Dừng/Tiếp tục phát (Play/Pause) 
                trang_thai_phat = not trang_thai_phat 
                if not trang_thai_phat: # Nếu trạng thái là "đang phát" 
                    player1.start() 
                else: # Nếu trạng thái là "tạm dừng" 
                    player1.pause() 
                should_update_tft = True 
              
            elif key == '=': # Chuyển bài tiếp theo 
                if che_do_ngau_nhien: 
                    bai_hat = urandom.randint(MIN_BAI_HAT, MAX_BAI_HAT) 
                else: 
                    bai_hat = bai_hat + 1 if bai_hat < MAX_BAI_HAT else MIN_BAI_HAT 
                  
                player1.play(bai_hat) 
                trang_thai_phat = False 
                should_update_tft = True 

            elif key == 'AC': # Quay lại bài trước 
                if che_do_ngau_nhien: 
                    bai_hat = urandom.randint(MIN_BAI_HAT, MAX_BAI_HAT) 
                else: 
                    bai_hat = bai_hat - 1 if bai_hat > MIN_BAI_HAT else MAX_BAI_HAT 
                  
                player1.play(bai_hat) 
                trang_thai_phat = False 
                should_update_tft = True 
                      
            elif key == ':': # Bật/tắt chế độ ngẫu nhiên 
                che_do_ngau_nhien = not che_do_ngau_nhien # Đảo ngược trạng thái 
                if che_do_ngau_nhien: 
                    bai_hat = urandom.randint(MIN_BAI_HAT, MAX_BAI_HAT) 
                    player1.play(bai_hat) 
                    trang_thai_phat = False 
                should_update_tft = True 
              
            if should_update_tft: 
                update_tft(tft_obj, bg_color, text_color) 
         
        utime.sleep(0.05) 
      
     # Thông báo khi thoát 
    tft_obj.fill(bg_color) 
    tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1) 
    utime.sleep(1)