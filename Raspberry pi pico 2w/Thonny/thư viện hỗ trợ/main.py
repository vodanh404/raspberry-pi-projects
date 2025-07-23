# Khai báo thư viện
import network
import time
import urequests 
import json
import urtc
import umail
import ntptime
from machine import I2C, Pin
from DIYables_MicroPython_LCD_I2C import LCD_I2C
from DIYables_Pico_Keypad import Keypad
from dfplayermini import DFPlayerMini
# --- Cấu hình LCD ---
I2C_ADDR = 0x27
LCD_COLS = 20
LCD_ROWS = 4
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
lcd = LCD_I2C(i2c, I2C_ADDR, LCD_ROWS, LCD_COLS)
lcd.backlight_on()
lcd.clear()
# Thiết lập bàn phím 
NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [13, 12, 11, 10] 
COLUMN_PINS = [9, 8, 7, 6] 
KEYMAP = ['1', '2', '3', '+',
          '4', '5', '6', '-',
          '7', '8', '9', 'x',
          'AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)
# Thiết lập tính năng bàn phím nhắn tin
Tinh_nang_nut= [
    ['1', ['1']],
    ['2', ['A', 'B', 'C', '2']],
    ['3', ['D', 'E', 'F', '3']],
    ['4', ['G', 'H', 'I', '4']],
    ['5', ['J', 'K', 'L', '5']],
    ['6', ['M', 'N', 'O', '6']],
    ['7', ['P', 'Q', 'R', 'S', '7']],
    ['8', ['T', 'U', 'V', '8']],
    ['9', ['W', 'X', 'Y', 'Z', '9']],
    ['AC', ['*']], # Phím '*'
    ['0', [' ', '0']], # Phím '0'
    ['=', ['#', '.']], # Phím '#'
    ['+', ['send']],    # Phím 'A' -> Chức năng 'send' (Gửi)
    ['-', ['back']],    # Phím 'B' -> Chức năng 'back' (Quay lại)
    ['x', ['del']],      # Phím 'C' -> Chức năng 'del' (Xóa)
    [':', ['space']]    # Phím 'D' -> Chức năng 'space' (hoặc các chức năng đặc biệt khác)
]

# thiết lập thời gian
days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
i2c_1 = I2C(1, scl=Pin(3), sda=Pin(2))
rtc = urtc.DS1307(i2c_1)
# Thiết lập mp3
player1 = DFPlayerMini(1, 4, 5) 
player1.select_source('sdcard')
# --- Khởi tạo các biến trạng thái ---
am_luong = 15
bai_hat = 1 # Bài hát mặc định ban đầu là bài số 1
MAX_BAI_HAT = 200 # Giả định số bài hát tối đa trên thẻ SD của bạn
MIN_BAI_HAT = 1 # Bài hát tối thiểu
trang_thai_phat = False # False: Đang phát, True: Đã tạm dừng
# thiết lập thông số nhắn tin
# Email gửi
sender_email = "ungdungthu3@gmail.com"
sender_name = 'Myphone'
sender_app_password = "dvmq ponq gplj awdq"
# Email nhận 
recipient_email = ['dinhphuchd2008@gmail.com', "anhkhoangovan20008@gmail.com"]
current_email_index = 0 
# Các biến toàn cục cho tính năng nhắn tin
current_message_text = ""
last_physical_key_multi_tap = None
multi_tap_press_count = 0
last_multi_tap_time = 0
MULTI_TAP_TIMEOUT_MS_MSG = 700 # Thời gian chờ giữa các lần nhấn phím để xác định multi-tap (ms)
email_subject = "Tin nhan tu Myphone" # Chủ đề email mặc định
# --- Cấu hình Menu ---
menu_chinh = [
    "--- MENU CHINH ---", 
    "1. May tinh",
    "2. Thoi tiet",
    "3. Dong ho",
    "4. May phat nhac",
    "5. Nhan tin",
    "--- EXIT ---"]
# --- Cấu hình Nút Điều Hướng ---
BUTTON_PIN = Pin(16, Pin.IN, Pin.PULL_UP)
BUTTON_PIN_1 = Pin(17, Pin.IN, Pin.PULL_UP)
BUTTON_PIN_2 = Pin(18, Pin.IN, Pin.PULL_UP)
# --- Biến trạng thái Menu ---
current_selection_index = 1 # Bắt đầu từ mục "1. May tinh" (index 1)
display_offset = 0          # Bắt đầu hiển thị từ mục đầu tiên của menu_chinh
# --- Biến trạng thái ứng dụng ---
app_state = "MENU"
selected_feature_name = "" # Tên của tính năng đang chạy
# Địa chỉ và mật khẩu wifi
WIFI_CREDENTIALS = [
    ("TP-Link_8A5C", "84493378"),
    ("Phuc Dat", "anhtuan00"),
    ("Trang Tuan", "12345678"),
    ("Mywifi", "codefunny"),]
# API thời tiết
API_KEYS = [
    "383c5c635c88590b37c698bc100f6377",
    "fe8d8c65cf345889139d8e545f57819a",
    "68c51539817878022c5315a3b403165c",]
current_key_index = 0
MAX_KEY_INDEX = len(API_KEYS) - 1
CITY_NAME = "Hanoi"   
UNITS = "metric" 
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
# Thiết lập biểu thức cho máy tính
bieu_thuc = ""
def run_calculator():
    global app_state, bieu_thuc
    app_state = "CALCULATOR"
    lcd.clear()
    last_button_1_state_calc = BUTTON_PIN_1.value() 

    while app_state == "CALCULATOR":
        key = keypad.get_key()
        current_button_1_state_calc = BUTTON_PIN_1.value() # Đọc trạng thái nút EXIT

        if current_button_1_state_calc == 0 and last_button_1_state_calc == 1:
            # Nút CHỌN/EXIT được nhấn: Thoát khỏi máy tính
            app_state = "MENU"
            bieu_thuc = "" # Reset biểu thức khi thoát
            display_menu()
            time.sleep(0.3) # Chống rung nút
            return # Thoát khỏi hàm run_calculator

        if key:
            if key == 'AC':  # Dùng '*' để xóa biểu thức
                bieu_thuc = ""
                lcd.clear()
            elif key == '=': # Tính biểu thức
                try:
                    bieu_thuc_to_eval = bieu_thuc.replace('x', '*').replace(':', '/') # Thay thế 'x' bằng '*' và ':' bằng '/' trước khi tính toán
                    result = str(eval(bieu_thuc_to_eval))
                    lcd.clear()
                    lcd.print(result)
                    bieu_thuc = result
                except Exception as e: # Bắt lỗi cụ thể hơn để dễ debug
                    lcd.clear()
                    lcd.print("Loi phep tinh!")
                    bieu_thuc = ""
            else: 
                bieu_thuc += key
                lcd.clear() 
                lcd.print(bieu_thuc) 
            time.sleep(0.3)
        
        last_button_1_state_calc = current_button_1_state_calc 
        time.sleep(0.01) 

def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    for ssid, password in WIFI_CREDENTIALS:
        wlan.connect(ssid, password)
        wait = 15
        while wait > 0 and wlan.status() != network.STAT_GOT_IP:
            time.sleep(1)
            wait -= 1
        if wlan.status() == network.STAT_GOT_IP:
            return True # Trả về True nếu kết nối thành công
    return False # Trả về False nếu kết nối thất bại
    
def get_weather_data():	# Hàm thời tiết    
    global current_key_index
    # Lấy API Key hiện tại
    api_key_to_use = API_KEYS[current_key_index]
    request_url = f"{BASE_URL}?q={CITY_NAME}&appid={api_key_to_use}&units={UNITS}"
    # Số lần thử lại với các API Key khác nhau
    retries = len(API_KEYS) # Thử mỗi key một lần   

    for _ in range(retries):
        try:
            response = urequests.get(request_url)
            if response.status_code == 200:
                weather_data = json.loads(response.text)
                
                # Trích xuất và in dữ liệu
                temperature = weather_data['main']['temp']
                humidity = weather_data['main']['humidity']
                wind_speed = weather_data['wind']['speed']

                if lcd:
                    lcd.clear()
                    lcd.set_cursor(0, 0)
                    lcd.print(f"City: {weather_data['name']}")
                    lcd.set_cursor(0, 1)
                    lcd.print(f"Temp: {temperature:.1f}C")
                    lcd.set_cursor(0, 2)
                    lcd.print(f"Humid: {humidity}%")
                    lcd.set_cursor(0, 3)
                    lcd.print(f"Wind: {wind_speed:.1f} m/s")
                time.sleep(1)
                return True # Lấy thành công

            elif response.status_code == 429: # Too Many Requests
                response.close()
                # Chuyển sang key tiếp theo ngay trong hàm này
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                time.sleep(5) # Chờ một chút trước khi thử lại với key mới
            else:
                response.close()
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                time.sleep(2) # Chờ một chút trước khi thử key tiếp theo
        except Exception as e:
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            time.sleep(2) # Chờ một chút trước khi thử key tiếp theo
    return False # Không lấy được dữ liệu sau khi thử hết các key

def run_weather(): # Hàm chạy tính năng thời tiết
    global app_state, selected_feature_name
    app_state = "WEATHER"
    selected_feature_name = "Thoi tiet"
    lcd.clear()
    
    # Kiểm tra lại kết nối Wifi ngay tại đây
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected(): # Nếu chưa kết nối, thử kết nối lại
        lcd.print("Dang ket noi WiFi...")
        connect_to_wifi()
        time.sleep(1) # Đợi một chút để kết nối ổn định hơn

    if wlan.isconnected(): # Kiểm tra lại sau khi đã cố gắng kết nối
        get_weather_data()
    else:
        lcd.clear()
        lcd.print("Khong co mang!")
        time.sleep(2)
    last_button_1_state_weather = BUTTON_PIN_1.value()
    while app_state == "WEATHER":
        current_button_1_state_weather = BUTTON_PIN_1.value() # Đọc trạng thái nút EXIT
        if current_button_1_state_weather == 0 and last_button_1_state_weather == 1:
            # Nút CHỌN/EXIT được nhấn: Thoát khỏi thời tiết
            app_state = "MENU"
            display_menu()
            time.sleep(0.3)
            return
        last_button_1_state_weather = current_button_1_state_weather
        time.sleep(0.01)
def synchronize_time_ntp_simple():
    ntptime.host = "pool.ntp.org"
    try:
        ntptime.settime()
        current_time_system_utc = time.localtime()

        time_vn_seconds = time.mktime(current_time_system_utc) + 7 * 3600
        time_vn_tuple = time.localtime(time_vn_seconds)

        rtc.datetime((time_vn_tuple[0], time_vn_tuple[1], time_vn_tuple[2], time_vn_tuple[6],
                      time_vn_tuple[3], time_vn_tuple[4], time_vn_tuple[5], 0))
        print("Đồng bộ thời gian thành công (GMT+7).")
    except Exception as e:
        print(f"Lỗi khi đồng bộ thời gian: {e}")
        print("Đảm bảo Pico đã kết nối WiFi và có internet.")
    time.sleep(1.5)
        
def run_clock(): # Hàm chạy tính năng đồng hồ
    global app_state, selected_feature_name
    app_state = "CLOCK"
    selected_feature_name = "Dong ho"
    lcd.clear()
    last_button_1_state_clock = BUTTON_PIN_1.value()
    while app_state == "CLOCK":
        current_button_1_state_clock = BUTTON_PIN_1.value() # Đọc trạng thái nút EXIT
        if current_button_1_state_clock == 0 and last_button_1_state_clock == 1:
            app_state = "MENU"
            display_menu()
            time.sleep(0.3)
            return
        current_datetime = rtc.datetime()
        lcd.clear()
        lcd.set_cursor(0, 0);
        lcd.print("--------------------");
        lcd.set_cursor(5, 1);            
        lcd.print(f"{current_datetime.day:02d}/{current_datetime.month:02d}/{current_datetime.year}");     
        lcd.set_cursor(6, 2);            
        lcd.print(f"{current_datetime.hour:02d}:{current_datetime.minute:02d}:{current_datetime.second}");
        lcd.set_cursor(0, 3);
        lcd.print("--------------------");
        time.sleep(1)
        last_button_1_state_clock = current_button_1_state_clock
        time.sleep(0.01) 

# Khởi tạo giá trị hiển thị trước đó để so sánh (giúp màn hình ổn định)
prev_am_luong = -1
prev_bai_hat = -1
prev_trang_thai_phat = None

def update_lcd():	# hàm hỗ trợ cho phát nhạc 
    global prev_am_luong, prev_bai_hat, prev_trang_thai_phat

    # Chỉ cập nhật nếu có bất kỳ giá trị nào thay đổi
    if am_luong != prev_am_luong or bai_hat != prev_bai_hat or trang_thai_phat != prev_trang_thai_phat:
        lcd.clear() 
        lcd.set_cursor(0, 0)
        lcd.print(f"Volume: {am_luong:02d}") 
        lcd.set_cursor(0, 1)
        lcd.print(f"file: {bai_hat:03d}") 
        lcd.set_cursor(0, 2)
        if not trang_thai_phat:
            lcd.print("Status: Playing")
        else:
            lcd.print("Status: Paused")
        # Cập nhật giá trị "trước đó"
        prev_am_luong = am_luong
        prev_bai_hat = bai_hat
        prev_trang_thai_phat = trang_thai_phat
def run_mp3():
    global am_luong, bai_hat, trang_thai_phat
    key = keypad.get_key()
    if key: # Chỉ xử lý khi có phím được nhấn
        should_update_lcd = False # Đặt lại cờ cập nhật LCD
        if key == '+': # Tăng âm lượng
            if am_luong < 30:
                am_luong += 1
                if player1: player1.set_volume(am_luong)
                should_update_lcd = True
        elif key == '-': # Giảm âm lượng
            if am_luong > 0:
                am_luong -= 1
                if player1: player1.set_volume(am_luong)
                should_update_lcd = True
        elif key == 'x': # Dừng/Tiếp tục phát
            if player1:
                if not trang_thai_phat:
                    player1.pause()
                    trang_thai_phat = True
                else:
                    player1.start()
                    trang_thai_phat = False
                should_update_lcd = True
        elif key == '=': # Chuyển bài tiếp theo
            if player1:
                if bai_hat < MAX_BAI_HAT:
                    bai_hat += 1
                else:
                    bai_hat = MIN_BAI_HAT # Quay lại bài đầu tiên nếu đã ở bài cuối
                player1.play(bai_hat)
                trang_thai_phat = False # Đặt lại trạng thái là đang phát
                should_update_lcd = True
        elif key == 'AC': # Chuyển bài trước đó (KHÔNG cuộn về bài cuối)
            if player1:
                if bai_hat > MIN_BAI_HAT: # Chỉ lùi bài nếu không phải là bài đầu tiên
                    bai_hat -= 1
                    player1.play(bai_hat)
                    trang_thai_phat = False # Đặt lại trạng thái là đang phát
        elif key in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
            pass 
        if should_update_lcd:
            update_lcd()

def run_music_player():
    global am_luong, bai_hat, trang_thai_phat, app_state, selected_feature_name
    app_state = "MUSIC_PLAYER"
    selected_feature_name = "May phat nhac"
    lcd.clear()
    update_lcd()

    if player1: # Chỉ thực hiện nếu DFPlayer được khởi tạo thành công
        player1.set_volume(am_luong) # Thiết lập âm lượng ban đầu
        player1.play(bai_hat) # Bắt đầu phát bài hát ban đầu
        trang_thai_phat = False # Đảm bảo trạng thái ban đầu là "Đang phát"
        update_lcd()

    last_button_1_state_music_play = BUTTON_PIN_1.value() # Lưu trạng thái nút EXIT

    while app_state == "MUSIC_PLAYER":
        key = keypad.get_key()
        current_button_1_state_music_play = BUTTON_PIN_1.value() # Đọc trạng thái nút EXIT

        if current_button_1_state_music_play == 0 and last_button_1_state_music_play == 1:
            if player1:
                if not trang_thai_phat: # Nếu đang phát (False) thì tạm dừng
                    player1.pause()
                    trang_thai_phat = True
                else: # Nếu đang tạm dừng (True) thì phát tiếp
                    player1.start()
                    trang_thai_phat = False
            app_state = "MENU"
            display_menu()
            time.sleep(0.1)
            return

        should_update_lcd = False # Cờ để quyết định có cập nhật LCD hay không

        if key: # Chỉ xử lý khi có phím được nhấn
            if key == '+': # Tăng âm lượng
                if am_luong < 30:
                    am_luong += 1
                    if player1: player1.set_volume(am_luong)
                    should_update_lcd = True
            elif key == '-': # Giảm âm lượng
                if am_luong > 0:
                    am_luong -= 1
                    if player1: player1.set_volume(am_luong)
                    should_update_lcd = True
            elif key == 'x': # Dừng/Tiếp tục phát (Play/Pause)
                if player1:
                    if not trang_thai_phat: # Nếu đang phát (False) thì tạm dừng
                        player1.pause()
                        trang_thai_phat = True
                    else: # Nếu đang tạm dừng (True) thì phát tiếp
                        player1.start()
                        trang_thai_phat = False
                    should_update_lcd = True
            elif key == '=': # Chuyển bài tiếp theo
                if player1:
                    if bai_hat < MAX_BAI_HAT:
                        bai_hat += 1
                    else:
                        bai_hat = MIN_BAI_HAT # Quay lại bài đầu tiên nếu đã ở bài cuối
                    player1.play(bai_hat)
                    trang_thai_phat = False # Đặt lại trạng thái là đang phát
                    should_update_lcd = True
            elif key == 'AC': # Chuyển bài trước đó (KHÔNG cuộn về bài cuối)
                if player1:
                    if bai_hat > MIN_BAI_HAT: # Chỉ lùi bài nếu không phải là bài đầu tiên
                        bai_hat -= 1
                    else:
                        bai_hat = MAX_BAI_HAT # Về bài cuối nếu đang ở bài đầu
                    player1.play(bai_hat)
                    trang_thai_phat = False # Đặt lại trạng thái là đang phát
                    should_update_lcd = True
            # Các phím số không có chức năng trong máy nghe nhạc
            elif key in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', ':']:
                pass # Không làm gì với các phím này

        if should_update_lcd:
            update_lcd()

        last_button_1_state_music_play = current_button_1_state_music_play
        time.sleep(0.01)

# --- Hàm hỗ trợ hiển thị màn hình Gmail ---
def update_gmail_display():
    global current_message_text, current_email_index
    lcd.clear() # Xóa toàn bộ màn hình
    lcd.set_cursor(0, 0)
    lcd.print("Tin nhan:")
    lcd.set_cursor(10, 0) # Đặt "Gui den:" trên cùng một dòng với "Tin nhan:"
    lcd.print(f"Gui den:{current_email_index}")

    # In tin nhắn, ngắt dòng tự động qua các dòng 1, 2, 3
    display_text = current_message_text
    current_char_index = 0
    # Lặp qua các dòng 1, 2, 3 (chỉ số 1, 2, 3)
    for row in range(1, LCD_ROWS):
        if current_char_index < len(display_text):
            line_to_print = display_text[current_char_index : current_char_index + LCD_COLS]
            lcd.set_cursor(0, row)
            lcd.print(line_to_print)
            current_char_index += LCD_COLS
        else:
            # Nếu không còn văn bản để in, đảm bảo các dòng còn lại được xóa
            lcd.set_cursor(0, row)
            lcd.print(" " * LCD_COLS)
def run_Gmail():
    global app_state, selected_feature_name, current_message_text
    global last_physical_key_multi_tap, multi_tap_press_count, last_multi_tap_time
    global current_email_index, recipient_email

    app_state = "Gmail"
    selected_feature_name = "Nhan tin"
    update_gmail_display() # Hiển thị ban đầu

    last_button_2_state_gmail = BUTTON_PIN_2.value() # Trạng thái ban đầu của BUTTON_PIN_2
    last_button_1_state_gmail = BUTTON_PIN_1.value() # Trạng thái ban đầu của BUTTON_PIN_1 (thoát)

    DEBOUNCE_DELAY_BTN2 = 200 # Độ trễ cho nút BUTTON_PIN_2

    while app_state == "Gmail":
        current_time_ms = time.ticks_ms()

        # Xử lý nút EXIT (BUTTON_PIN_1)
        current_button_1_state_gmail = BUTTON_PIN_1.value()
        if current_button_1_state_gmail == 0 and last_button_1_state_gmail == 1:
            app_state = "MENU"
            current_message_text = "" # Xóa tin nhắn khi thoát
            last_physical_key_multi_tap = None
            multi_tap_press_count = 0
            last_multi_tap_time = 0
            display_menu() # Hiển thị menu chính
            time.sleep(0.3)
            return

        # Xử lý nút chuyển người nhận (BUTTON_PIN_2)
        current_button_2_state_gmail = BUTTON_PIN_2.value()
        if current_button_2_state_gmail == 0 and last_button_2_state_gmail == 1: # Nút được nhấn (từ HIGH xuống LOW)
            # Kiểm tra chống rung nút
            if (current_time_ms - last_multi_tap_time) > DEBOUNCE_DELAY_BTN2: # Sử dụng last_multi_tap_time để chung debouncing
                current_email_index = (current_email_index + 1) % len(recipient_email)
                update_gmail_display() # Cập nhật hiển thị sau khi thay đổi người nhận

        last_button_2_state_gmail = current_button_2_state_gmail # Cập nhật trạng thái nút 2

        key = keypad.get_key()
        if key:
            # Kiểm tra thời gian multi-tap
            if key != last_physical_key_multi_tap or (current_time_ms - last_multi_tap_time) > MULTI_TAP_TIMEOUT_MS_MSG:
                last_physical_key_multi_tap = key
                multi_tap_press_count = 0
            else:
                multi_tap_press_count += 1

            key_data = None
            for item in Tinh_nang_nut:
                if item[0] == key:
                    key_data = item[1]
                    break

            if key_data:
                action = key_data[multi_tap_press_count % len(key_data)] # Lấy ký tự hoặc chức năng tương ứng

                if action == 'send':
                    if current_message_text:
                        # Xóa vùng tin nhắn và hiển thị "Đang gửi..."
                        for i in range(1, LCD_ROWS): # Xóa các dòng 1, 2, 3
                            lcd.set_cursor(0, i)
                            lcd.print(" " * LCD_COLS)
                        lcd.set_cursor(0, 1)
                        lcd.print("Dang gui tin nhan...")

                        if connect_to_wifi():
                            smtp = None
                            try:
                                smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)
                                smtp.login(sender_email, sender_app_password)
                                smtp.to([recipient_email[current_email_index]])
                                smtp.write("From:" + sender_name + "<"+ sender_email+">\n")
                                smtp.write("Subject:" + email_subject + "\n")
                                smtp.send(current_message_text) # Sử dụng smtp.send() đúng cách
                                # Xóa vùng tin nhắn và hiển thị thành công
                                for i in range(1, LCD_ROWS):
                                    lcd.set_cursor(0, i)
                                    lcd.print(" " * LCD_COLS)
                                lcd.set_cursor(3, 1)
                                lcd.print("Gui thanh cong!")
                                current_message_text = "" # Xóa tin nhắn sau khi gửi thành công
                            except Exception as e:
                                # Xóa vùng tin nhắn và hiển thị thất bại
                                for i in range(1, LCD_ROWS):
                                    lcd.set_cursor(0, i)
                                    lcd.print(" " * LCD_COLS)
                                lcd.set_cursor(4, 1)
                                lcd.print("Gui that bai!")
                                lcd.set_cursor(0,2)
                                lcd.print(f"Error: {e}") # Debugging
                            finally:
                                if smtp:
                                    smtp.quit()
                        else:
                            # Xóa vùng tin nhắn và hiển thị không có WiFi
                            for i in range(1, LCD_ROWS):
                                lcd.set_cursor(0, i)
                                lcd.print(" " * LCD_COLS)
                            lcd.set_cursor(3, 1)
                            lcd.print("Khong co WiFi!")
                            lcd.set_cursor(4, 2)
                            lcd.print("Gui that bai!")
                        time.sleep(2) # Giữ thông báo trên màn hình
                        update_gmail_display() # Cập nhật lại màn hình về chế độ nhập tin nhắn

                    else: # Không có tin nhắn để gửi
                        for i in range(1, LCD_ROWS):
                            lcd.set_cursor(0, i)
                            lcd.print(" " * LCD_COLS)
                        lcd.set_cursor(2, 1)
                        lcd.print("Khong co tin nhan")
                        lcd.set_cursor(7, 2)
                        lcd.print("de gui")
                        time.sleep(1)
                        update_gmail_display() # Cập nhật lại màn hình về chế độ nhập tin nhắn

                elif action == 'back':
                    current_message_text = ""
                    update_gmail_display() # Cập nhật lại màn hình hiển thị sau khi xóa hết

                elif action == 'del':
                    if current_message_text:
                        current_message_text = current_message_text[:-1]
                        update_gmail_display() # Cập nhật lại màn hình hiển thị sau khi xóa ký tự

                elif action == 'space':
                    max_msg_lines = LCD_ROWS - 1 # 3 dòng cho tin nhắn
                    max_msg_len = LCD_COLS * max_msg_lines
                    if len(current_message_text) < max_msg_len:
                        current_message_text += ' '
                        update_gmail_display() # Cập nhật lại màn hình sau khi thêm dấu cách

                else: # Xử lý các ký tự bình thường
                    max_msg_lines = LCD_ROWS - 1 # 3 dòng cho tin nhắn
                    max_msg_len = LCD_COLS * max_msg_lines

                    if multi_tap_press_count == 0: # Lần nhấn đầu tiên hoặc sau timeout
                        if len(current_message_text) < max_msg_len:
                            current_message_text += action
                    else: # Multi-tap tiếp theo, thay thế ký tự cuối
                        # Chỉ thay thế ký tự cuối nếu nó thuộc cùng một nhóm phím
                        if current_message_text and current_message_text[-1] in key_data:
                            current_message_text = current_message_text[:-1] + action
                        elif len(current_message_text) < max_msg_len: # Trường hợp đặc biệt: multi-tap ngay khi rỗng
                            current_message_text += action
                    update_gmail_display() # Cập nhật lại màn hình sau khi thêm/thay thế ký tự

            last_multi_tap_time = current_time_ms
            time.sleep(0.15) # Giảm độ trễ để tăng tốc độ gõ

        elif last_physical_key_multi_tap is not None and (current_time_ms - last_multi_tap_time) > MULTI_TAP_TIMEOUT_MS_MSG:
            last_physical_key_multi_tap = None
            multi_tap_press_count = 0
            # Không cần cập nhật màn hình nếu không có thay đổi hiển thị

        last_button_1_state_gmail = current_button_1_state_gmail # Cập nhật trạng thái nút thoát
        time.sleep_ms(10)


# Tạo một từ điển để dễ dàng gọi hàm tương ứng với chỉ số menu
feature_actions = {
    1: run_calculator,
    2: run_weather,
    3: run_clock,
    4: run_music_player,
    5: run_Gmail ,
}
if connect_to_wifi():
    synchronize_time_ntp_simple()
# --- Hàm hiển thị Menu trên LCD ---
def display_menu():
    lcd.clear()
    for i in range(LCD_ROWS):
        menu_item_index = display_offset + i
        if menu_item_index < len(menu_chinh):
            lcd.set_cursor(1, i)
            lcd.print(menu_chinh[menu_item_index])
    # Hiển thị mục đang chọn với dấu ">"
    lcd.set_cursor(0, current_selection_index - display_offset)
    lcd.print(">")
# --- Vòng lặp chính ---
# Trạng thái nút trước đó, dùng để phát hiện "nhấn" (chuyển từ HIGH sang LOW)
last_button_state = BUTTON_PIN.value()
last_button_1_state = BUTTON_PIN_1.value()
# Hiển thị menu lần đầu tiên khi khởi động
display_menu()
while True:
    current_button_state = BUTTON_PIN.value() # Trạng thái hiện tại của nút CUỘN
    current_button_1_state = BUTTON_PIN_1.value() # Trạng thái hiện tại của nút CHỌN

    # Khi ở Menu chính
    if app_state == "MENU":
        # Xử lý nút CUỘN (BUTTON_PIN)
        if current_button_state == 0 and last_button_state == 1: # Nút CUỘN được nhấn
            current_selection_index += 1 # Tăng chỉ số lựa chọn
            # Đảm bảo current_selection_index không vượt quá giới hạn (trừ mục tiêu đề và EXIT)
            if current_selection_index >= len(menu_chinh) -1 : # Nếu đến mục cuối cùng (trừ EXIT)
                current_selection_index = 1 # Quay về "1. May tinh" (index 1)
                display_offset = 0          # Đảm bảo cuộn lại từ đầu màn hình
            # Logic cuộn màn hình khi di chuyển xuống
            elif (current_selection_index - display_offset) >= LCD_ROWS:
                display_offset += 1 # Cuộn menu xuống 1 hàng
            display_menu() # Cập nhật hiển thị menu
            time.sleep(0.3) # Chống rung nút
        # Xử lý nút CHỌN (BUTTON_PIN_1)
        if current_button_1_state == 0 and last_button_1_state == 1: # Nút CHỌN được nhấn
            if current_selection_index == len(menu_chinh) - 1: # Nếu chọn "--- EXIT ---"
                lcd.clear()
                lcd.print("Tam biet!")
                time.sleep(1)
                break # Thoát vòng lặp chính để kết thúc chương trình
            elif current_selection_index in feature_actions:
                # Gọi hàm tương ứng với tính năng được chọn
                feature_actions[current_selection_index]()
            time.sleep(0.3) # Chống rung nút

    # Cập nhật trạng thái nút cuối cùng cho vòng lặp tiếp theo
    last_button_state = current_button_state
    last_button_1_state = current_button_1_state
    time.sleep(0.01)




                                                                                                                     