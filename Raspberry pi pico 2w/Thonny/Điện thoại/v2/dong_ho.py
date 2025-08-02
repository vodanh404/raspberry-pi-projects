import utime
import urtc
import ntptime
from machine import I2C, Pin, PWM
from DIYables_Pico_Keypad import Keypad
from ket_noi_wifi import do_connect_wifi

days_of_week = ['Mon', 'Tue', 'Wednes', 'Thur', 'Fri', 'Sat', 'Sun']

rtc = urtc.DS1307(I2C(1, scl=Pin(3), sda=Pin(2)))

NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [13, 12, 11, 10]
COLUMN_PINS = [9, 8, 7, 6]
KEYMAP = ['1', '2', '3', '+', '4', '5', '6', '-', '7', '8', '9', 'x', 'AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)

buzzer = PWM(Pin(15))
LOUDEST_FREQUENCY = 3000 
DUTY_CYCLE_50_PERCENT = 32768

# Đồng bộ thời gian
if do_connect_wifi():
    try:
        ntptime.host = "time.google.com"
        ntptime.settime()
        local_seconds = utime.time() + (7 * 3600)
        tm = utime.localtime(local_seconds)
        rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
        print('Đồng bộ thời gian NTP và cập nhật RTC thành công!')
    except Exception as e:
        print(f'Lỗi khi đồng bộ NTP: {e}')
        print('Sử dụng thời gian hiện có từ RTC.')
else:
    print('Không có kết nối mạng. Sử dụng thời gian hiện có từ RTC.')
    
# Đồng hồ  
def run_clock(lcd_obj, button_select_pin, lcd_cols, lcd_rows): 
    Dong_Ho = True 
    lcd_obj.clear()
    
    while Dong_Ho:
        current_datetime = rtc.datetime()
        if button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            Dong_Ho = False 
            continue 
        
        lcd_obj.clear()
        lcd_obj.set_cursor(0, 0);
        lcd_obj.print("--------------------");
        lcd_obj.set_cursor(5, 1);            
        lcd_obj.print(f"{current_datetime.day:02d}/{current_datetime.month:02d}/{current_datetime.year}");     
        lcd_obj.set_cursor(6, 2);            
        lcd_obj.print(f"{current_datetime.hour:02d}:{current_datetime.minute:02d}:{current_datetime.second}");
        lcd_obj.set_cursor(0, 3);
        lcd_obj.print("--------------------");
        utime.sleep(1)

# Bấm giờ (Stopwatch) 
def Bam_gio(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    BAM_GIO = True
    stopwatch_active = False
    start_time = 0
    elapsed_time = 0
    paused_time = 0

    # In ra hướng dẫn ban đầu chỉ một lần
    lcd_obj.clear()
    lcd_obj.set_cursor(0,0)
    lcd_obj.print("Bam Gio")
    lcd_obj.set_cursor(0,1)
    lcd_obj.print("A: Chay/Dung") # Sửa ký tự theo KEYMAP của bạn
    lcd_obj.set_cursor(0,2)
    lcd_obj.print("B: Dat lai") # Sửa ký tự theo KEYMAP của bạn

    # Biến để kiểm soát việc cập nhật LCD chỉ khi có thay đổi
    last_display_time = -1
    last_status = ""

    while BAM_GIO:
        key = keypad.get_key() # Đọc phím bấm
        
        # Xử lý phím '+', '-'
        if key == '+': # Bắt đầu/Tạm dừng
            if not stopwatch_active:
                stopwatch_active = True
                start_time = utime.ticks_ms() - paused_time # Tiếp tục từ thời điểm dừng
            else:
                stopwatch_active = False
                paused_time = utime.ticks_diff(utime.ticks_ms(), start_time) # Lưu thời gian đã trôi qua khi tạm dừng
            # Cần một độ trễ nhỏ sau khi bấm phím để tránh đọc lại nhiều lần
            utime.sleep_ms(250) 
            
        elif key == '-': # Đặt lại
            stopwatch_active = False
            start_time = elapsed_time = paused_time = 0
            # Cần một độ trễ nhỏ sau khi bấm phím để tránh đọc lại nhiều lần
            utime.sleep_ms(250) 
            
        # Xử lý nút thoát (button_select_pin)
        elif button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0: 
                utime.sleep(0.05)
            BAM_GIO = False
            continue

        # Tính toán thời gian đã trôi qua
        if stopwatch_active:
            elapsed_time = utime.ticks_diff(utime.ticks_ms(), start_time)
        else:
            # Khi tạm dừng, elapsed_time phải giữ giá trị của paused_time
            elapsed_time = paused_time 
            
        total_seconds = elapsed_time // 1000
        milliseconds = (elapsed_time % 1000) // 10 # Chỉ lấy 2 chữ số miligiây

        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        # Tạo chuỗi hiển thị thời gian và trạng thái
        display_time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
        status_str = "Dang Chay" if stopwatch_active else ("Dang Dung" if elapsed_time > 0 else "San Sang")

        # Cập nhật LCD chỉ khi thông tin hiển thị thay đổi
        # Điều này giúp giảm nhấp nháy màn hình và cải thiện hiệu suất
        if display_time_str != last_display_time or status_str != last_status:
            lcd_obj.clear()
            lcd_obj.set_cursor(0,0)
            lcd_obj.print("Bam Gio")
            lcd_obj.set_cursor(0,1)
            lcd_obj.print(display_time_str)
            lcd_obj.set_cursor(0,2)
            lcd_obj.print(status_str)
            
            last_display_time = display_time_str
            last_status = status_str

        utime.sleep_ms(20)
        
# Đếm ngược
def Dem_nguoc(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    # --- Khởi tạo trạng thái ban đầu ---
    DEM_NGUOC = True
    countdown_active = False
    remaining_seconds = set_hours = set_minutes = set_seconds = 0

    last_time_str = ""       # Lưu chuỗi thời gian hiển thị trước đó để tránh cập nhật dư thừa
    last_status_str = ""     # Lưu chuỗi trạng thái hiển thị trước đó
    last_update_tick = utime.ticks_ms() 

    # --- Hiển thị thông tin ban đầu trên LCD ---
    lcd_obj.clear()
    lcd_obj.set_cursor(0, 0)
    lcd_obj.print("DEM NGUOC")
    lcd_obj.set_cursor(0, 2) 
    lcd_obj.print("Dung/Tiep tuc")
    lcd_obj.set_cursor(0, 3) 
    lcd_obj.print("Dat lai")
    
    # Vị trí hiển thị thời gian chính
    TIME_DISPLAY_ROW = 1 
    STATUS_DISPLAY_ROW = 2

    # --- Vòng lặp chính của chức năng đếm ngược ---
    while DEM_NGUOC:
        key = keypad.get_key()
        if key:
            if not countdown_active:
                if key == '1': set_hours = min(set_hours + 1, 23)
                elif key == '4': set_hours = max(set_hours - 1, 0)
                elif key == '2': set_minutes = min(set_minutes + 1, 59)
                elif key == '5': set_minutes = max(set_minutes - 1, 0)
                elif key == '3': set_seconds = min(set_seconds + 1, 59)
                elif key == '6': set_seconds = max(set_seconds - 1, 0)

                remaining_seconds = set_hours * 3600 + set_minutes * 60 + set_seconds
                
            if key == '+': # Nút "Dừng/Tiếp tục"
                if remaining_seconds > 0: # Chỉ cho phép bắt đầu/tiếp tục nếu có thời gian
                    countdown_active = not countdown_active
                    last_update_tick = utime.ticks_ms() 
            elif key == '-': # Nút "Đặt lại"
                countdown_active = False
                set_hours = set_minutes = set_seconds = 0
                remaining_seconds = 0
            utime.sleep_ms(200) 

        # --- Xử lý nút thoát (button_select_pin) ---
        if button_select_pin.value() == 0: # Nút được nhấn (giả sử active low)
            lcd_obj.clear()
            lcd_obj.set_cursor(0, 0)
            lcd_obj.print("Dang thoat...")
            utime.sleep(1) # Hiển thị thông báo thoát
            while button_select_pin.value() == 0: 
                utime.sleep_ms(50) 
            return # Thoát khỏi hàm

        # --- Cập nhật thời gian đếm ngược ---
        current_tick = utime.ticks_ms()
        elapsed_ms = utime.ticks_diff(current_tick, last_update_tick)   # Tính toán thời gian trôi qua kể từ lần cập nhật cuối cùng

        if countdown_active and remaining_seconds > 0 and elapsed_ms >= 1000:
            seconds_passed = elapsed_ms // 1000
            remaining_seconds = max(0, remaining_seconds - seconds_passed)
            last_update_tick += seconds_passed * 1000 # Cập nhật điểm thời gian cuối
            
            if remaining_seconds == 0:
                countdown_active = False
                # Xóa dòng trạng thái và hiển thị "KET THUC!"
                lcd_obj.set_cursor(0, STATUS_DISPLAY_ROW)
                lcd_obj.print("                    ")
                lcd_obj.set_cursor(0, STATUS_DISPLAY_ROW)
                lcd_obj.print("KET THUC!")
                buzzer.freq(LOUDEST_FREQUENCY)
                buzzer.duty_u16(DUTY_CYCLE_50_PERCENT) 
                utime.sleep(3) 
                buzzer.duty_u16(0) 
                utime.sleep(2) 
                continue 
        # --- Hiển thị thời gian trên LCD ---
        display_hours = remaining_seconds // 3600
        display_minutes = (remaining_seconds % 3600) // 60
        display_seconds = remaining_seconds % 60
        time_str = f"{display_hours:02d}:{display_minutes:02d}:{display_seconds:02d}"
        if time_str != last_time_str:
            # Xóa dòng thời gian cũ trước khi in cái mới để tránh sót ký tự
            lcd_obj.set_cursor(0, TIME_DISPLAY_ROW)
            lcd_obj.print("                    ")
            lcd_obj.set_cursor(0, TIME_DISPLAY_ROW)
            lcd_obj.print(time_str)
            last_time_str = time_str

        # --- Hiển thị trạng thái trên LCD ---
        status_str = ""
        if remaining_seconds == 0 and not countdown_active:
            status_str = "San Sang" if set_hours == 0 and set_minutes == 0 and set_seconds == 0 else "Nhap Thoi Gian"
        elif countdown_active:
            status_str = "Dang Chay"
        else: # countdown_active is False and remaining_seconds > 0 (Dừng)
            status_str = "Tam Dung"

        if status_str != last_status_str:
            # Xóa dòng trạng thái cũ trước khi in cái mới
            lcd_obj.set_cursor(0, STATUS_DISPLAY_ROW)
            lcd_obj.print("                    ")
            lcd_obj.set_cursor(0, STATUS_DISPLAY_ROW)
            lcd_obj.print(status_str)
            last_status_str = status_str
        utime.sleep_ms(50)
    
# Đồng hồ cà chua
def Dong_ho_ca_chua(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    DONG_HO_CA_CHUA = True

    POMODORO_SECONDS = 25 * 60
    BREAK_SECONDS = 5 * 60

    state = "Lam viec"
    seconds_left = POMODORO_SECONDS
    running = False
    last_display = ""

    lcd_obj.clear()
    lcd_obj.set_cursor(0, 0)
    lcd_obj.print("Dong Ho Ca Chua")

    while DONG_HO_CA_CHUA:

        if button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            DONG_HO_CA_CHUA = False 
            continue 

        key = keypad.get_key()
        if key == '+':
            running = not running
            utime.sleep(0.3)
        elif key == '-':
            running = False
            state = "Lam Viec"
            seconds_left = POMODORO_SECONDS
            # buzzer.on(); utime.sleep(0.2); buzzer.off()
            utime.sleep(0.3)

        # Cập nhật thời gian
        if running and seconds_left > 0:
            utime.sleep(1)
            seconds_left -= 1

        elif running and seconds_left == 0:
            running = False
            buzzer.freq(LOUDEST_FREQUENCY)
            buzzer.duty_u16(DUTY_CYCLE_50_PERCENT) 
            utime.sleep(3) 
            buzzer.duty_u16(0) 
            state = "Nghi Ngoi" if state == "Lam Viec" else "Lam Viec"
            seconds_left = BREAK_SECONDS if state == "Nghi Ngoi" else POMODORO_SECONDS

        # Hiển thị
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        display = f"{state}: {minutes:02d}:{seconds:02d}"

        if display != last_display:
            lcd_obj.set_cursor(0, 1)
            lcd_obj.print(display)
            last_display = display
