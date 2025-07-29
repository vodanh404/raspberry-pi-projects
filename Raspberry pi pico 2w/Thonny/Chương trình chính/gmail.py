import utime
from machine import I2C, Pin
import umail
from DIYables_Pico_Keypad import Keypad
from ket_noi_wifi import do_connect_wifi 
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

def update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    global current_message_text, current_email_index
    lcd_obj.clear() # Xóa toàn bộ màn hình
    lcd_obj.set_cursor(0, 0)
    lcd_obj.print("Tin nhan:")
    lcd_obj.set_cursor(10, 0) # Đặt "Gui den:" trên cùng một dòng với "Tin nhan:"
    lcd_obj.print(f"Gui den:{current_email_index}")

    # In tin nhắn, ngắt dòng tự động qua các dòng 1, 2, 3
    display_text = current_message_text
    current_char_index = 0
    # Lặp qua các dòng 1, 2, 3 (chỉ số 1, 2, 3)
    for row in range(1, lcd_rows):
        if current_char_index < len(display_text):
            line_to_print = display_text[current_char_index : current_char_index + lcd_cols]
            lcd_obj.set_cursor(0, row)
            lcd_obj.print(line_to_print)
            current_char_index += lcd_cols
        else:
            # Nếu không còn văn bản để in, đảm bảo các dòng còn lại được xóa
            lcd_obj.set_cursor(0, row)
            lcd_obj.print(" " * lcd_cols) 

def run_Gmail(lcd_obj, button_select_pin, lcd_cols, lcd_rows, button_up_pin):
    global current_message_text, last_physical_key_multi_tap, multi_tap_press_count, last_multi_tap_time, current_email_index, recipient_email

    GMAIL = True 
    lcd_obj.clear()
    while GMAIL:
        DEBOUNCE_DELAY_BTN2 = 200
        if button_select_pin.value() == 0: 
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            GMAIL = False 
            continue

        current_time_ms = utime.ticks_ms()

        # Xử lý nút chuyển người nhận (BUTTON_PIN_2)
        current_button_2_state_gmail = button_up_pin.value()
        if current_button_2_state_gmail == 0 and last_button_2_state_gmail == 1: # Nút được nhấn (từ HIGH xuống LOW)
            # Kiểm tra chống rung nút
            if (current_time_ms - last_multi_tap_time) > DEBOUNCE_DELAY_BTN2: # Sử dụng last_multi_tap_time để chung debouncing
                current_email_index = (current_email_index + 1) % len(recipient_email)
                update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows) # Cập nhật hiển thị sau khi thay đổi người nhận

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
                        for i in range(1, lcd_rows): # Xóa các dòng 1, 2, 3
                            lcd_obj.set_cursor(0, i)
                            lcd_obj.print(" " * lcd_cols)
                        lcd_obj.set_cursor(0, 1)
                        lcd_obj.print("Dang gui tin nhan...")

                        if do_connect_wifi():
                            smtp = None
                            try:
                                smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)
                                smtp.login(sender_email, sender_app_password)
                                smtp.to([recipient_email[current_email_index]])
                                smtp.write("From:" + sender_name + "<"+ sender_email+">\n")
                                smtp.write("Subject:" + email_subject + "\n")
                                smtp.send(current_message_text) # Sử dụng smtp.send() đúng cách
                                # Xóa vùng tin nhắn và hiển thị thành công
                                for i in range(1, lcd_rows): 
                                    lcd_obj.set_cursor(0, i)
                                    lcd_obj.print(" " * lcd_cols)
                                lcd_obj.set_cursor(3, 1)
                                lcd_obj.print("Gui thanh cong!")
                                current_message_text = "" # Xóa tin nhắn sau khi gửi thành công
                            except Exception as e:
                                # Xóa vùng tin nhắn và hiển thị thất bại
                                for i in range(1, lcd_rows):
                                    lcd_obj.set_cursor(0, i)
                                    lcd_obj.print(" " * lcd_cols)
                                lcd_obj.set_cursor(4, 1)
                                lcd_obj.print("Gui that bai!")
                                lcd_obj.set_cursor(0,2)
                                lcd_obj.print(f"Error: {e}") # Debugging
                            finally:
                                if smtp:
                                    smtp.quit()
                        else:
                            # Xóa vùng tin nhắn và hiển thị không có WiFi
                            for i in range(1, lcd_rows):
                                lcd_obj.set_cursor(0, i)
                                lcd_obj.print(" " * lcd_cols)
                            lcd_obj.set_cursor(3, 1)
                            lcd_obj.print("Khong co WiFi!")
                            lcd_obj.set_cursor(4, 2)
                            lcd_obj.print("Gui that bai!")
                        utime.sleep(2) # Giữ thông báo trên màn hình
                        update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows) # Cập nhật lại màn hình về chế độ nhập tin nhắn

                    else: # Không có tin nhắn để gửi
                        for i in range(1, lcd_rows): 
                            lcd_obj.set_cursor(0, i)
                            lcd_obj.print(" " * lcd_cols)
                        lcd_obj.set_cursor(2, 1)
                        lcd_obj.print("Khong co tin nhan")
                        lcd_obj.set_cursor(7, 2)
                        lcd_obj.print("de gui")
                        utime.sleep(1)
                        update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows) # Cập nhật lại màn hình về chế độ nhập tin nhắn

                elif action == 'back':
                    current_message_text = ""
                    update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows) # Cập nhật lại màn hình hiển thị sau khi xóa hết

                elif action == 'del':
                    if current_message_text:
                        current_message_text = current_message_text[:-1]
                        update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows) # Cập nhật lại màn hình hiển thị sau khi xóa ký tự

                elif action == 'space':
                    max_msg_lines = lcd_rows - 1 # 3 dòng cho tin nhắn
                    max_msg_len = lcd_cols * max_msg_lines
                    if len(current_message_text) < max_msg_len:
                        current_message_text += ' '
                        update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows) # Cập nhật lại màn hình sau khi thêm dấu cách

                else: # Xử lý các ký tự bình thường
                    max_msg_lines = lcd_rows - 1 # 3 dòng cho tin nhắn
                    max_msg_len = lcd_cols * max_msg_lines

                    if multi_tap_press_count == 0: # Lần nhấn đầu tiên hoặc sau timeout
                        if len(current_message_text) < max_msg_len:
                            current_message_text += action
                    else: # Multi-tap tiếp theo, thay thế ký tự cuối
                        # Chỉ thay thế ký tự cuối nếu nó thuộc cùng một nhóm phím
                        if current_message_text and current_message_text[-1] in key_data:
                            current_message_text = current_message_text[:-1] + action
                        elif len(current_message_text) < max_msg_len: # Trường hợp đặc biệt: multi-tap ngay khi rỗng
                            current_message_text += action
                    update_gmail_display(lcd_obj, button_select_pin, lcd_cols, lcd_rows) # Cập nhật lại màn hình sau khi thêm/thay thế ký tự

            last_multi_tap_time = current_time_ms
            utime.sleep(0.15) # Giảm độ trễ để tăng tốc độ gõ

        elif last_physical_key_multi_tap is not None and (current_time_ms - last_multi_tap_time) > MULTI_TAP_TIMEOUT_MS_MSG:
            last_physical_key_multi_tap = None
            multi_tap_press_count = 0
            # Không cần cập nhật màn hình nếu không có thay đổi hiển thị

        utime.sleep_ms(10)
