import utime
import ntptime
from machine import Pin, PWM, RTC
from DIYables_Pico_Keypad import Keypad
from ket_noi_wifi import do_connect_wifi
from st7735 import sysfont

# --- Khởi tạo các thành phần khác ---
days_of_week = ['Mon', 'Tue', 'Wed', 'Thur', 'Fri', 'Sat', 'Sun']
rtc = RTC()

NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [9, 8, 7, 6]
COLUMN_PINS = [5, 4, 3, 2]
KEYMAP = ['1', '2', '3', '+','4', '5', '6', '-', '7', '8', '9', 'x', 'AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)

buzzer = PWM(Pin(15))
LOUDEST_FREQUENCY = 3000
DUTY_CYCLE_50_PERCENT = 32768

# Đồng bộ thời gian qua NTP
if do_connect_wifi():
    try:
        ntptime.host = "time.google.com"
        ntptime.settime()
        print('Đồng bộ thời gian NTP thành công!')
        current_time = rtc.datetime()
        year, month, day, weekday, hour, minute, second, subseconds = rtc.datetime()
        new_hour = hour + 7
        if new_hour >= 24:
            new_hour %= 24
            pass
        new_datetime = (year, month, day, weekday, new_hour, minute, second, subseconds)
        rtc.datetime(new_datetime)
        
        print('Đã cập nhật RTC với múi giờ Việt Nam (GMT+7).')
    except Exception as e:
        print(f'Lỗi khi đồng bộ NTP hoặc cập nhật múi giờ: {e}')
        print('Sử dụng thời gian hiện có từ RTC.')
else:
    print('Không có kết nối mạng. Sử dụng thời gian hiện có từ RTC.')

# --- Các chế độ hoạt động ---

# Đồng hồ
def run_clock(tft_obj, button_select_pin, bg_color, text_color):
    Dong_Ho = True
    tft_obj.fill(bg_color)
    prev_time_str = ""
    prev_date_str = ""
    
    # Cài đặt kích thước và vị trí cố định
    tft_obj.text((10, 10), "Dong Ho", text_color, sysfont.sysfont, 1) # Có thể giữ lại hoặc bỏ tùy thích

    while Dong_Ho:
        current_datetime = rtc.datetime()
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            Dong_Ho = False
            continue

        date_str = f"{current_datetime[2]:02d}/{current_datetime[1]:02d}/{current_datetime[0]}"
        time_str = f"{current_datetime[4]:02d}:{current_datetime[5]:02d}:{current_datetime[6]:02d}"

        # Căn giữa và làm lớn chữ cho giờ, phút, giây
        if time_str != prev_time_str:
            tft_obj.text((5, 30), prev_time_str, bg_color, sysfont.sysfont, 2) # Xóa thời gian cũ
            tft_obj.text((5, 30), time_str, text_color, sysfont.sysfont, 2) # Hiển thị thời gian mới với cỡ chữ 3
            prev_time_str = time_str
        
        # Cập nhật ngày tháng năm với cỡ chữ nhỏ hơn
        if date_str != prev_date_str:
            tft_obj.text((10, 10), prev_date_str, bg_color, sysfont.sysfont, 1) # Xóa ngày tháng cũ
            tft_obj.text((10, 10), date_str, text_color, sysfont.sysfont, 1) # Hiển thị ngày tháng mới với cỡ chữ 1
            prev_date_str = date_str

        utime.sleep(1)
        
# Bấm giờ (Stopwatch)
def Bam_gio(tft_obj, button_select_pin, bg_color, text_color):

    BAM_GIO = True
    stopwatch_active = False
    start_time = 0
    elapsed_time = 0
    paused_time = 0

    last_display_time = "00:00.00"
    last_status = "San Sang"

    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), "Bam Gio", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 40), last_display_time, text_color, sysfont.sysfont, 2)
    tft_obj.text((10, 80), last_status, text_color, sysfont.sysfont, 1)

    while BAM_GIO:
        key = keypad.get_key()

        if key == 'x':  # Bắt đầu/Tạm dừng
            if not stopwatch_active:
                stopwatch_active = True
                start_time = utime.ticks_ms() - paused_time
            else:
                stopwatch_active = False
                paused_time = utime.ticks_diff(utime.ticks_ms(), start_time)
            utime.sleep_ms(250)

        elif key == 'AC':  # Đặt lại
            stopwatch_active = False
            start_time = elapsed_time = paused_time = 0
            utime.sleep_ms(250)

        elif button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            BAM_GIO = False
            continue

        if stopwatch_active:
            elapsed_time = utime.ticks_diff(utime.ticks_ms(), start_time)
        else:
            elapsed_time = paused_time

        total_seconds = elapsed_time // 1000
        milliseconds = (elapsed_time % 1000) // 10

        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        display_time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
        status_str = "Dang Chay" if stopwatch_active else ("Tam Dung" if elapsed_time > 0 else "San Sang")

        if display_time_str != last_display_time:
            tft_obj.text((10, 40), last_display_time, bg_color, sysfont.sysfont, 2)
            tft_obj.text((10, 40), display_time_str, text_color, sysfont.sysfont, 2)
            last_display_time = display_time_str

        if status_str != last_status:
            tft_obj.text((10, 80), last_status, bg_color, sysfont.sysfont, 1)
            tft_obj.text((10, 80), status_str, text_color, sysfont.sysfont, 1)
            last_status = status_str

        utime.sleep_ms(20)

# Đếm ngược
def Dem_nguoc(tft_obj, button_select_pin, bg_color, text_color):
    DEM_NGUOC = True
    countdown_active = False
    remaining_seconds = 0
    set_hours = set_minutes = set_seconds = 0

    last_time_str = "00:00:00"
    last_status_str = "San Sang"
    last_update_tick = utime.ticks_ms()
    buzzer_played = False

    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), "DEM NGUOC", text_color, sysfont.sysfont, 1)

    def update_display():
        """Hàm con để cập nhật màn hình."""
        nonlocal last_time_str, last_status_str
        
        display_hours = remaining_seconds // 3600
        display_minutes = (remaining_seconds % 3600) // 60
        display_seconds = remaining_seconds % 60
        time_str = f"{display_hours:02d}:{display_minutes:02d}:{display_seconds:02d}"

        if remaining_seconds == 0 and not countdown_active:
            status_str = "San Sang" if set_hours == 0 and set_minutes == 0 and set_seconds == 0 else "Nhap Thoi Gian"
        elif countdown_active:
            status_str = "Dang Chay"
        else:
            status_str = "Tam Dung"

        if time_str != last_time_str:
            tft_obj.text((10, 40), last_time_str, bg_color, sysfont.sysfont, 2)
            tft_obj.text((10, 40), time_str, text_color, sysfont.sysfont, 2)
            last_time_str = time_str
        
        if status_str != last_status_str:
            tft_obj.text((10, 80), last_status_str, bg_color, sysfont.sysfont, 1)
            tft_obj.text((10, 80), status_str, text_color, sysfont.sysfont, 1)
            last_status_str = status_str

    update_display() # Hiển thị ban đầu

    while DEM_NGUOC:
        key = keypad.get_key()

        # Xử lý nút thoát
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep_ms(50)
            DEM_NGUOC = False
            continue
            
        # Xử lý phím bấm
        if key:
            if not countdown_active:
                # Điều chỉnh thời gian
                if key == '1': set_hours = min(set_hours + 1, 23)
                elif key == '4': set_hours = max(set_hours - 1, 0)
                elif key == '2': set_minutes = min(set_minutes + 1, 59)
                elif key == '5': set_minutes = max(set_minutes - 1, 0)
                elif key == '3': set_seconds = min(set_seconds + 1, 59)
                elif key == '6': set_seconds = max(set_seconds - 1, 0)
            
            if key == '+':  # Bắt đầu/Tạm dừng
                if remaining_seconds > 0:
                    countdown_active = not countdown_active
                    last_update_tick = utime.ticks_ms()
            elif key == '-':  # Đặt lại
                countdown_active = False
                set_hours = set_minutes = set_seconds = 0
                remaining_seconds = 0
                buzzer_played = False
            
            # Cập nhật tổng số giây sau mỗi lần nhập
            remaining_seconds = set_hours * 3600 + set_minutes * 60 + set_seconds
            
            update_display()
            utime.sleep_ms(200) # Chống dội phím

        # Xử lý thời gian đếm ngược
        if countdown_active and remaining_seconds > 0:
            current_tick = utime.ticks_ms()
            if utime.ticks_diff(current_tick, last_update_tick) >= 1000:
                remaining_seconds -= 1
                last_update_tick = current_tick
                buzzer_played = False # Reset cờ chuông
                update_display()

        # Phát chuông khi kết thúc
        if remaining_seconds == 0 and not countdown_active and not buzzer_played:
            tft_obj.text((10, 90), "KET THUC!", text_color, sysfont.sysfont, 1)
            buzzer.freq(LOUDEST_FREQUENCY)
            buzzer.duty_u16(DUTY_CYCLE_50_PERCENT)
            utime.sleep(3)
            buzzer.duty_u16(0)
            buzzer_played = True # Đặt cờ đã phát chuông
            update_display()
        
        utime.sleep_ms(20) # Giảm độ trễ

# Đồng hồ cà chua
def Dong_ho_ca_chua(tft_obj, button_select_pin, bg_color, text_color):
    DONG_HO_CA_CHUA = True
    POMODORO_SECONDS = 25 * 60
    BREAK_SECONDS = 5 * 60
    
    state = "Lam viec"
    seconds_left = POMODORO_SECONDS
    running = False
    buzzer_played = False
    
    last_display = ""
    last_status_display = ""
    last_update_tick = utime.ticks_ms()

    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), "Dong Ho Ca Chua", text_color, sysfont.sysfont, 1)

    def update_display():
        """Hàm con để cập nhật màn hình."""
        nonlocal last_display, last_status_display
        
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        display_str = f"{state}: {minutes:02d}:{seconds:02d}"
        status_str = f"Trang thai: {'Dang Chay' if running else 'Dung'}"

        if display_str != last_display:
            tft_obj.text((10, 40), last_display, bg_color, sysfont.sysfont, 2)
            tft_obj.text((10, 40), display_str, text_color, sysfont.sysfont, 2)
            last_display = display_str
        
        if status_str != last_status_display:
            tft_obj.text((10, 80), last_status_display, bg_color, sysfont.sysfont, 1)
            tft_obj.text((10, 80), status_str, text_color, sysfont.sysfont, 1)
            last_status_display = status_str

    update_display()

    while DONG_HO_CA_CHUA:
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            DONG_HO_CA_CHUA = False
            continue

        key = keypad.get_key()
        if key == '+':
            running = not running
            last_update_tick = utime.ticks_ms()
            update_display()
            utime.sleep_ms(300)
        elif key == '-':
            running = False
            state = "Lam viec"
            seconds_left = POMODORO_SECONDS
            buzzer_played = False
            update_display()
            utime.sleep_ms(300)

        if running and seconds_left > 0:
            current_tick = utime.ticks_ms()
            if utime.ticks_diff(current_tick, last_update_tick) >= 1000:
                seconds_left -= 1
                last_update_tick = current_tick
                buzzer_played = False
                update_display()

        elif running and seconds_left == 0 and not buzzer_played:
            running = False
            buzzer.freq(LOUDEST_FREQUENCY)
            buzzer.duty_u16(DUTY_CYCLE_50_PERCENT)
            utime.sleep(3)
            buzzer.duty_u16(0)
            
            # Chuyển trạng thái và đặt lại thời gian
            state = "Nghi Ngoi" if state == "Lam viec" else "Lam viec"
            seconds_left = BREAK_SECONDS if state == "Nghi Ngoi" else POMODORO_SECONDS
            last_update_tick = utime.ticks_ms()
            buzzer_played = True # Đặt cờ đã phát chuông
            update_display()
            
        utime.sleep_ms(20)


def Xem_Lich(tft_obj, button_select_pin, bg_color, text_color):
    XEM_LICH = True
    
    # Lấy thông tin ngày tháng năm hiện tại
    year, month, day, weekday, _, _, _, _ = rtc.datetime()
    current_year = year
    current_month = month
    
    # Danh sách số ngày trong các tháng, có tính đến năm nhuận
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    def is_leap_year(y):
        return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)

    def display_calendar(y, m):
        tft_obj.fill(bg_color)
        
        # Tiêu đề tháng và năm
        month_name = ['Thang 1', 'Thang 2', 'Thang 3', 'Thang 4', 'Thang 5', 'Thang 6', 
                      'Thang 7', 'Thang 8', 'Thang 9', 'Thang 10', 'Thang 11', 'Thang 12']
        title = f"{month_name[m-1]} {y}"
        # Căn chỉnh lại vị trí Y để cân đối hơn
        tft_obj.text((10, 10), title, text_color, sysfont.sysfont, 2)
        
        # Tiêu đề các ngày trong tuần (T2-CN)
        week_days_label = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
        for i, wd in enumerate(week_days_label):
            tft_obj.text((2 + i * 18, 35), wd, text_color, sysfont.sysfont, 1)

        # Xác định ngày đầu tiên của tháng là thứ mấy (thứ 0=T2, thứ 6=CN)
        first_day_of_month_tuple = utime.localtime(utime.mktime((y, m, 1, 0, 0, 0, 0, 0)))
        start_weekday = first_day_of_month_tuple[3]
        
        if start_weekday == 6: # Tùy chỉnh để CN nằm cuối tuần
            start_weekday = -1
        
        # Cập nhật số ngày của tháng 2 nếu là năm nhuận
        if m == 2 and is_leap_year(y):
            num_days = 29
        else:
            num_days = days_in_month[m]
            
        y_offset = 55
        
        for d in range(1, num_days + 1):
            day_str = str(d)
            
            # Tính toán vị trí X, Y cho từng ngày
            x_pos = 2 + ((d + start_weekday) % 7) * 18
            y_pos = y_offset + ((d + start_weekday) // 7) * 16

            # Tô màu cho ngày hiện tại
            if d == day and y == year and m == month:
                tft_obj.text((x_pos, y_pos), day_str, 0x07E0, sysfont.sysfont, 1)
            else:
                tft_obj.text((x_pos, y_pos), day_str, text_color, sysfont.sysfont, 1)
                
    display_calendar(current_year, current_month)

    while XEM_LICH:
        key = keypad.get_key()

        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep_ms(50)
            XEM_LICH = False
            continue

        if key == '+': # Quay lại tháng trước
            current_month -= 1
            if current_month < 1:
                current_month = 12
                current_year -= 1
            display_calendar(current_year, current_month)
            utime.sleep_ms(200)

        elif key == '-': # Chuyển sang tháng sau
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
            display_calendar(current_year, current_month)
            utime.sleep_ms(200)
            
        elif key == 'x': # Trở về tháng hiện tại
            current_year = year
            current_month = month
            display_calendar(current_year, current_month)
            utime.sleep_ms(200)

        utime.sleep_ms(20)