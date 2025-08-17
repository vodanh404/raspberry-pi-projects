# bang_tuan_hoan.py
import utime
from machine import SPI, Pin
from st7735 import sysfont
from Bang_Tuan_Hoan import periodic_table_data

def display_element_info(tft_obj, element_data, bg_color, text_color):
    """
    Hàm vẽ thông tin chi tiết của một nguyên tố lên màn hình.
    Việc tách hàm này giúp code gọn gàng và dễ quản lý hơn.
    """
    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), f"So nguyen tu: {element_data['stt']}", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 20), f"Ki hieu: {element_data['ki_hieu']}", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 30), f"Ten day du: {element_data['ten_day_du']}", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 40), f"Phan tu khoi: {element_data['phan_tu_khoi']}", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 50), f"Nhom: {element_data['nhom']}", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 60), f"Chu ki: {element_data['chu_ki']}", text_color, sysfont.sysfont, 1)

def Bang_tuan_hoan(tft_obj, button_select_pin, button_up_pin, button_down_pin, bg_color, text_color):
    """
    Chương trình chính để duyệt bảng tuần hoàn.
    Sử dụng một biến kiểm tra để chỉ vẽ lại màn hình khi có sự thay đổi.
    """
    current_element_index = 0
    num_elements = len(periodic_table_data)

    # Vẽ màn hình lần đầu tiên
    display_element_info(tft_obj, periodic_table_data[current_element_index], bg_color, text_color)

    BANG_TUAN_HOAN = True
    while BANG_TUAN_HOAN:
        previous_element_index = current_element_index
        utime.sleep_ms(10)

        # Kiểm tra nút thoát
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            BANG_TUAN_HOAN = False
            continue

        # Hiển thị nguyên tố trước
        elif button_up_pin.value() == 0:
            current_element_index = (current_element_index - 1 + num_elements) % num_elements
            # Chờ nhả nút để tránh lướt quá nhanh
            while button_up_pin.value() == 0:
                utime.sleep(0.05)

        # Hiển thị nguyên tố sau
        elif button_down_pin.value() == 0:
            current_element_index = (current_element_index + 1) % num_elements
            # Chờ nhả nút để tránh lướt quá nhanh
            while button_down_pin.value() == 0:
                utime.sleep(0.05)

        # Chỉ vẽ lại màn hình nếu chỉ số nguyên tố đã thay đổi
        if current_element_index != previous_element_index:
            display_element_info(tft_obj, periodic_table_data[current_element_index], bg_color, text_color)