# thong_tin_thiet_bi.py
import utime
from st7735 import sysfont

def thong_tin(tft_obj, button_select_pin, bg_color, text_color):
    
    tft_obj.fill(bg_color)
    THONG_TIN = True
    
    tft_obj.text((10, 10), "Ten san pham: Myphone", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 30), "Phien ban: V3.3", text_color, sysfont.sysfont, 1)
    
    tft_obj.text((10, 50), "Lan cap nhap cuoi:", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 65), "16/08/2025", text_color, sysfont.sysfont, 1)
    
    tft_obj.text((10, 80), "Nguoi che tac:", text_color, sysfont.sysfont, 1)
    tft_obj.text((10, 95), "Dinh Viet Phuc", text_color, sysfont.sysfont, 1)
    
    while THONG_TIN:
        # Kiểm tra nút thoát
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            THONG_TIN = False
            continue