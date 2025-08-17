# ghi_chu.py
import utime
from machine import Pin
from st7735 import sysfont

def run_note(tft_obj, button_select_pin, button_up_pin, button_down_pin, bg_color, text_color):
    # Dữ liệu văn bản
    info_text = [
        "---GHI CHU---",
        "Phien ban: V3.3",
        "Lan cap nhap cuoi: 16/08/2025",
        "Nguoi che tac: Dinh Viet Phuc",
        "", 
        "---------------------",
        "Cac thong tin khac:",
        "- Vi xu ly: Raspberry pi pico 2w",
        "- Bo nho: 2.5MB",
        "- Ket noi: Wifi",
        "- So tinh nang: 18",
        "- Nguon: USB",
        "",
        "---------------------",
        "Thong tin bo nho SD:",
        "- The SD gan vao:",
        "  - Dung luong: 8GB",
        "  - Trang thai: OK",
        "Test ok!!!"
    ]
    
    # Lấy kích thước màn hình từ thuộc tính _size của đối tượng TFT
    display_width, display_height = tft_obj.size()

    # Chiều cao của một dòng văn bản
    line_height = 10
    # Biến theo dõi vị trí cuộn hiện tại
    scroll_offset = 0

    # Hàm tính chiều rộng văn bản tùy chỉnh
    def text_width(text, font, size=1):
        font_width = font['Width']
        return (len(text) * font_width * size) + len(text)

    # Hàm tự động xuống dòng và trả về danh sách các dòng đã được xử lý
    def wrap_text_to_lines(text, max_width):
        lines = []
        words = text.split(' ')
        current_line = ''
        for word in words:
            if text_width(current_line + ' ' + word, sysfont.sysfont, 1) < max_width:
                current_line += ' ' + word
            else:
                lines.append(current_line.strip())
                current_line = word
        lines.append(current_line.strip())
        return lines

    # Chuẩn bị toàn bộ nội dung đã được xuống dòng trước khi vẽ
    all_lines = []
    # Chiều rộng tối đa cho văn bản, có tính toán lề
    max_text_width = display_width - 20
    for line in info_text:
        if text_width(line, sysfont.sysfont, 1) > max_text_width:
            wrapped_lines = wrap_text_to_lines(line, max_text_width)
            all_lines.extend(wrapped_lines)
        else:
            all_lines.append(line)
    
    # Tổng chiều cao của toàn bộ văn bản sau khi đã xuống dòng
    total_height = len(all_lines) * line_height

    # Hàm vẽ lại toàn bộ nội dung
    def draw_content():
        tft_obj.fill(bg_color)
        start_y = 10 - scroll_offset
        for i, line in enumerate(all_lines):
            y_pos = start_y + i * line_height
            # Chỉ vẽ các dòng nằm trong vùng hiển thị
            if -line_height < y_pos < display_height:
                tft_obj.text((10, y_pos), line, text_color, sysfont.sysfont, 1)

    # Lần vẽ đầu tiên
    draw_content()
    NOTE = True
    while NOTE:
        # Kiểm tra nút lên
        if button_up_pin.value() == 0:
            if scroll_offset > 0:
                scroll_offset -= line_height
                draw_content()
                utime.sleep(0.2)
            while button_up_pin.value() == 0:
                utime.sleep(0.05)

        # Kiểm tra nút xuống
        if button_down_pin.value() == 0:
            if total_height - scroll_offset > display_height - 20:
                scroll_offset += line_height
                draw_content()
                utime.sleep(0.2)
            while button_down_pin.value() == 0:
                utime.sleep(0.05)

        # Kiểm tra nút thoát (select)
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            NOTE = False
            continue