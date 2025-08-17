import utime
from machine import Pin
from st7735 import sysfont
from DIYables_Pico_Keypad import Keypad

# Thiết lập bàn phím
NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [9, 8, 7, 6]
COLUMN_PINS = [5, 4, 3, 2]
KEYMAP = ['1', '2', '3', '+','4', '5', '6', '-','7', '8', '9', 'x','AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_COLS, NUM_ROWS)
keypad.set_debounce_time(200)

# Định nghĩa các hằng số cho màn hình
MAX_CHARS_PER_LINE = 19  # Số ký tự tối đa trên một dòng màn hình TFT
LINE_SPACING = 15        # Khoảng cách giữa các dòng

def run_calculator(tft_obj, button_select_pin, bg_color, text_color):
    """
    Chạy chương trình máy tính trên màn hình TFT và bàn phím ma trận.
    Args:
        tft_obj: Đối tượng màn hình TFT đã được khởi tạo.
        button_select_pin: Pin của nút bấm để thoát chương trình.
        bg_color: Màu nền của màn hình.
        text_color: Màu chữ.
    """
    bieu_thuc = ""
    is_calculator_running = True
    last_key = None

    # Hiển thị thông báo khởi động
    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), "May tinh da san sang", text_color, sysfont.sysfont, 1)
    utime.sleep(1)

    def display_content(result_text=None):
        """Hiển thị biểu thức và kết quả (nếu có) lên màn hình."""
        tft_obj.fill(bg_color)

        # Chia biểu thức thành các dòng
        lines = [bieu_thuc[i:i + MAX_CHARS_PER_LINE] for i in range(0, len(bieu_thuc), MAX_CHARS_PER_LINE)]
        
        # Chỉ hiển thị 3 dòng cuối cùng của biểu thức
        lines_to_display = lines[-3:]

        # Hiển thị từng dòng của biểu thức
        y_pos = 10
        for line in lines_to_display:
            tft_obj.text((10, y_pos), line, text_color, sysfont.sysfont, 1)
            y_pos += LINE_SPACING
        
        # Hiển thị kết quả nếu có
        if result_text:
            tft_obj.text((10, y_pos), result_text, text_color, sysfont.sysfont, 1)

    # Hiển thị màn hình khởi đầu
    display_content()

    while is_calculator_running:
        key = keypad.get_key()

        # Kiểm tra nút thoát
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            is_calculator_running = False
            continue

        if key and key != last_key:
            last_key = key
            
            if key == 'AC':
                # Xóa toàn bộ biểu thức
                bieu_thuc = ""
                display_content()
            elif key == '=':
                try:
                    # Thay thế các ký hiệu để eval có thể hiểu
                    expr_to_eval = bieu_thuc.replace('x', '*').replace(':', '/')
                    result = str(eval(expr_to_eval))
                    
                    # Hiển thị biểu thức và kết quả
                    display_content(f"={result}")
                    
                    # Cập nhật biểu thức bằng kết quả để tiếp tục tính toán
                    bieu_thuc = result
                except (SyntaxError, NameError, ZeroDivisionError):
                    display_content("Loi phep tinh!")
                    bieu_thuc = ""
                except Exception:
                    display_content("Loi khong xac dinh!")
                    bieu_thuc = ""
            else:
                # Thêm phím vào biểu thức
                bieu_thuc += key
                display_content()

        # Đặt lại last_key sau khi xử lý xong
        if key is None:
            last_key = None

        utime.sleep_ms(50)