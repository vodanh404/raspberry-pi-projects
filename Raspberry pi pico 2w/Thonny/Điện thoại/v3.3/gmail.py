import utime
from machine import Pin
from DIYables_Pico_Keypad import Keypad
import umail
from ket_noi_wifi import do_connect_wifi
from st7735 import sysfont

# --- Cấu hình bàn phím ---
NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [9, 8, 7, 6]
COLUMN_PINS = [5, 4, 3, 2]
KEYMAP = ['1', '2', '3', '+',
          '4', '5', '6', '-',
          '7', '8', '9', 'x',
          'AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_COLS, NUM_ROWS)
keypad.set_debounce_time(200)

# --- Bản đồ chức năng phím ---
Tinh_nang_nut = [
    ['1', ['1']], ['2', ['A', 'B', 'C', '2']],
    ['3', ['D', 'E', 'F', '3']], ['4', ['G', 'H', 'I', '4']],
    ['5', ['J', 'K', 'L', '5']], ['6', ['M', 'N', 'O', '6']],
    ['7', ['P', 'Q', 'R', 'S', '7']], ['8', ['T', 'U', 'V', '8']],
    ['9', ['W', 'X', 'Y', 'Z', '9']], ['AC', ['*']], ['0', [' ', '0']],
    ['=', ['#', '.']], ['+', ['send']], ['-', ['back']],
    ['x', ['del']], [':', ['space']]
]

# --- Cấu hình Email ---
# Email gửi
sender_email = "ungdungthu3@gmail.com"
sender_name = 'Myphone'
sender_app_password = "dvmq ponq gplj awdq"
# Email nhận
recipient_email = ['dinhphuchd2008@gmail.com', "anhkhoangovan20008@gmail.com"]
current_email_index = 0
email_subject = "Tin nhan tu Myphone"

# --- Các biến toàn cục cho tính năng nhắn tin ---
current_message_text = ""
last_physical_key_multi_tap = None
multi_tap_press_count = 0
last_multi_tap_time = 0
MULTI_TAP_TIMEOUT_MS_MSG = 800  # Thời gian chờ giữa các lần nhấn phím (ms)

# --- Hằng số cho màn hình TFT 128x160 ---
MAX_CHARS_PER_LINE = 20  # Số ký tự tối đa trên một dòng (128 / 8px font width)
LINE_SPACING = 15        # Khoảng cách giữa các dòng
MSG_START_Y = 40         # Tọa độ Y để bắt đầu vẽ tin nhắn
MAX_MSG_LINES = 20       # Số dòng tin nhắn tối đa hiển thị ( (160-40)/10 )

def display_status_message(tft_obj, bg_color, text_color, message, delay_s=0):
    """Hàm hiển thị thông báo trạng thái tạm thời trên màn hình TFT."""
    tft_obj.fill(bg_color)
    lines = message.split('\n')
    y_pos = 60
    width, height = tft_obj.size() # Lấy kích thước màn hình
    for line in lines:
        # Canh giữa văn bản một cách đơn giản
        font_width = 8 # Chiều rộng của font sysfont
        text_width = len(line) * font_width
        x_pos = max(0, (width - text_width) // 2) # Sử dụng width đã lấy được
        tft_obj.text((x_pos, y_pos), line, text_color, sysfont.sysfont, 1)
        y_pos += LINE_SPACING + 2 # Tăng khoảng cách dòng cho thông báo
    if delay_s > 0:
        utime.sleep(delay_s)

def update_gmail_display(tft_obj, bg_color, text_color):
    """
    Cập nhật giao diện nhập tin nhắn trên màn hình TFT, có cuộn tin nhắn.
    """
    global current_message_text, current_email_index, recipient_email

    tft_obj.fill(bg_color)

    # Hiển thị người nhận (chỉ hiển thị phần tên trước @)
    recipient_name = recipient_email[current_email_index].split('@')[0]
    tft_obj.text((5, 10), f"Den: {recipient_name}", text_color, sysfont.sysfont, 1)

    # Hiển thị tiêu đề
    tft_obj.text((5, 25), "Soan tin:", text_color, sysfont.sysfont, 1)

    display_text_with_cursor = current_message_text + "_"
    lines = []
    # Tách tin nhắn thành các dòng phù hợp với chiều rộng màn hình
    words = display_text_with_cursor.split(' ')
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= MAX_CHARS_PER_LINE:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())

    # Lấy các dòng cuối cùng để tạo hiệu ứng cuộn
    lines_to_display = lines[-MAX_MSG_LINES:]

    y_pos = MSG_START_Y
    for line in lines_to_display:
        tft_obj.text((5, y_pos), line, text_color, sysfont.sysfont, 1)
        y_pos += LINE_SPACING


def run_Gmail(tft_obj, button_select_pin, button_up_pin, bg_color, text_color):
    """Hàm chính chạy ứng dụng Gmail trên màn hình TFT."""
    global current_message_text, last_physical_key_multi_tap, multi_tap_press_count, last_multi_tap_time, current_email_index

    GMAIL = True
    last_button_up_state = 1
    last_button_press_time = 0
    DEBOUNCE_DELAY_BTN = 200

    # Cập nhật màn hình lần đầu
    update_gmail_display(tft_obj, bg_color, text_color)

    while GMAIL:
        current_time_ms = utime.ticks_ms()

        # Xử lý nút thoát (button_select_pin)
        if button_select_pin.value() == 0:
            display_status_message(tft_obj, bg_color, text_color, "Dang thoat...", 1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            GMAIL = False
            continue

        # Xử lý nút chuyển người nhận (button_up_pin)
        current_button_up_state = button_up_pin.value()
        if current_button_up_state == 0 and last_button_up_state == 1:
            if (current_time_ms - last_button_press_time) > DEBOUNCE_DELAY_BTN:
                last_button_press_time = current_time_ms
                current_email_index = (current_email_index + 1) % len(recipient_email)
                update_gmail_display(tft_obj, bg_color, text_color)
        last_button_up_state = current_button_up_state

        # Xử lý bàn phím
        key = keypad.get_key()
        if key:
            if key != last_physical_key_multi_tap or (current_time_ms - last_multi_tap_time) > MULTI_TAP_TIMEOUT_MS_MSG:
                last_physical_key_multi_tap = key
                multi_tap_press_count = 0
            else:
                multi_tap_press_count += 1

            key_data = next((item[1] for item in Tinh_nang_nut if item[0] == key), None)

            if key_data:
                action = key_data[multi_tap_press_count % len(key_data)]

                if action == 'send':
                    if current_message_text:
                        display_status_message(tft_obj, bg_color, text_color, "Dang gui tin nhan...")
                        if do_connect_wifi():
                            smtp = None
                            try:
                                smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)
                                smtp.login(sender_email, sender_app_password)
                                smtp.to(recipient_email[current_email_index])
                                smtp.write(f"From: {sender_name} <{sender_email}>\n")
                                smtp.write(f"Subject: {email_subject}\n\n")
                                smtp.send(current_message_text)
                                display_status_message(tft_obj, bg_color, text_color, "Gui thanh cong!", 2)
                                current_message_text = ""
                            except Exception as e:
                                print(f"Error: {e}") # In lỗi ra console để debug
                                display_status_message(tft_obj, bg_color, text_color, f"Gui that bai!\nLoi: {type(e).__name__}", 3)
                            finally:
                                if smtp:
                                    smtp.quit()
                        else:
                            display_status_message(tft_obj, bg_color, text_color, "Khong co WiFi!\nGui that bai!", 2)
                    else:
                        display_status_message(tft_obj, bg_color, text_color, "Khong co tin nhan\nde gui!", 2)
                    
                    update_gmail_display(tft_obj, bg_color, text_color) # Quay lại màn hình soạn thảo

                elif action == 'back': # Xóa toàn bộ tin nhắn
                    current_message_text = ""
                    update_gmail_display(tft_obj, bg_color, text_color)

                elif action == 'del': # Xóa ký tự cuối
                    if current_message_text:
                        current_message_text = current_message_text[:-1]
                        update_gmail_display(tft_obj, bg_color, text_color)

                elif action == 'space':
                    current_message_text += ' '
                    update_gmail_display(tft_obj, bg_color, text_color)

                else: # Thêm ký tự vào tin nhắn
                    if multi_tap_press_count == 0:
                        current_message_text += action
                    else:
                        # Chỉ thay thế ký tự cuối nếu nó thuộc cùng một nhóm phím
                        if current_message_text and current_message_text[-1] in key_data:
                            current_message_text = current_message_text[:-1] + action
                        else:
                            current_message_text += action
                    update_gmail_display(tft_obj, bg_color, text_color)

            last_multi_tap_time = current_time_ms
            utime.sleep(0.1)

        # Đặt lại trạng thái multi-tap nếu hết thời gian chờ
        elif last_physical_key_multi_tap is not None and (current_time_ms - last_multi_tap_time) > MULTI_TAP_TIMEOUT_MS_MSG:
            last_physical_key_multi_tap = None
            multi_tap_press_count = 0

        utime.sleep_ms(10)