# menu_lcd.py
from machine import I2C, Pin
from DIYables_MicroPython_LCD_I2C import LCD_I2C
import utime

class LCDMenu:
    # Hàm khởi tạo bây giờ nhận các đối tượng I2C và Pin đã được tạo sẵn
    def __init__(self, i2c_obj, i2c_addr, lcd_rows, lcd_cols, button_up_pin, button_down_pin, button_select_pin):
        self.LCD_COLS = lcd_cols
        self.LCD_ROWS = lcd_rows
        
        # Sử dụng đối tượng I2C đã được truyền vào
        self.i2c = i2c_obj
        # Khởi tạo LCD với đối tượng I2C đã có
        self.lcd = LCD_I2C(self.i2c, i2c_addr, self.LCD_ROWS, self.LCD_COLS)
        
        # Bật đèn nền và xóa màn hình ngay khi khởi tạo
        self.lcd.backlight_on()
        self.lcd.clear()

        # Sử dụng các đối tượng Pin đã được truyền vào
        self.BUTTON_PIN_0 = button_up_pin     # Nút lên
        self.BUTTON_PIN_1 = button_down_pin   # Nút xuống
        self.BUTTON_PIN_2 = button_select_pin # Nút chọn

        self.Trang_thai_chon = 0 # Biến lưu trạng thái chọn

        # --- Định nghĩa Menu ---
        self.menu1 = ["-----Menu chinh------", "1.May tinh", "2.Thoi tiet", "3.Phat nhac", "4.Dong ho", "5.Gui Thu",
                      "6.Nhan tin", "7.Ban phim", "8.Bang tuan hoan", "9.Cai dat"]
        self.menu2 = ["------Dia diem------", "1.Ha Noi", "2.Da Nang", "3.Ho Chi Minh", "4.Thoat"]
        self.menu3 = ["-----Tinh Nang------", "1.Dong ho", "2.Bam gio", "3.Dem Nguoc", "4.Dong ho ca chua", "5.Thoat"]
        self.menu4 = ["------Cai dat-------", "1.Wifi", "2.Bluetooth", "3.Thoat"]

    # Hàm hiển thị menu trên LCD
    def hien_thi_menu(self, menu, vi_tri_chon):
        self.lcd.clear()
        self.lcd.set_cursor(0, 0)
        self.lcd.print(menu[0])  # Tiêu đề menu trên dòng đầu

    # Tính toán chỉ số bắt đầu để cuộn menu nếu cần
        max_items = self.LCD_ROWS - 1  # Số dòng hiển thị lựa chọn (vì dòng đầu dành cho tiêu đề)
        start_index = max(1, vi_tri_chon - max_items + 1)
        end_index = min(start_index + max_items, len(menu))

        for i in range(start_index, end_index):
            y = i - start_index + 1  # vị trí dòng từ 1 đến LCD_ROWS-1
            self.lcd.set_cursor(0, y)
            prefix = "> " if i == vi_tri_chon else "  "
            item_text = menu[i][:18]  # Cắt chuỗi nếu quá dài (20 - 2 ký tự cho prefix)
            self.lcd.print(prefix + item_text)

    # Hàm xử lý điều hướng menu
    def dieu_huong_menu(self, menu_hien_tai):
        vi_tri_chon = 1
        vi_tri_truoc_do = -1

        while True:
            if vi_tri_chon != vi_tri_truoc_do:
                self.hien_thi_menu(menu_hien_tai, vi_tri_chon)
                vi_tri_truoc_do = vi_tri_chon
            utime.sleep(0.05)
            
            if self.BUTTON_PIN_0.value() == 0:
                vi_tri_chon -= 1
                if vi_tri_chon < 1:
                    vi_tri_chon = len(menu_hien_tai) - 1
                while self.BUTTON_PIN_0.value() == 0:
                    utime.sleep(0.05)

            if self.BUTTON_PIN_1.value() == 0:
                vi_tri_chon += 1
                if vi_tri_chon >= len(menu_hien_tai):
                    vi_tri_chon = 1
                while self.BUTTON_PIN_1.value() == 0:
                    utime.sleep(0.05)

            if self.BUTTON_PIN_2.value() == 0:
                while self.BUTTON_PIN_2.value() == 0:
                    utime.sleep(0.05)
                return vi_tri_chon

    # Vòng lặp chính của chương trình menu
    def run_menu(self):
        current_menu = self.menu1

        while True:
            self.Trang_thai_chon = self.dieu_huong_menu(current_menu)

            if current_menu == self.menu1:
                if self.Trang_thai_chon == 1:
                    self.lcd.clear()
                    from may_tinh import run_calculator
                    run_calculator(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 2:
                    current_menu = self.menu2
                elif self.Trang_thai_chon == 3:
                    self.lcd.clear()
                    self.lcd.set_cursor(0, 0)
                    from phat_nhac import run_music_player
                    run_music_player(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 4:
                    current_menu = self.menu3
                elif self.Trang_thai_chon == 5:
                    self.lcd.clear()
                    self.lcd.set_cursor(0, 0)
                    from gmail import run_Gmail
                    run_Gmail(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS, self.BUTTON_PIN_0)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 9:
                    current_menu = self.menu4
                else:
                    self.lcd.clear()
                    self.lcd.set_cursor(0, 0)
                    self.lcd.print(f"Ban chon: {self.menu1[self.Trang_thai_chon]}")
                    utime.sleep(2)

            elif current_menu == self.menu2:
                if self.Trang_thai_chon == 1:
                    from thoi_tiet import lay_du_lieu_thoi_tiet
                    self.lcd.clear()
                    lay_du_lieu_thoi_tiet(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS,0)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 2:
                    from thoi_tiet import lay_du_lieu_thoi_tiet
                    self.lcd.clear()
                    lay_du_lieu_thoi_tiet(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS,1)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 3:
                    from thoi_tiet import lay_du_lieu_thoi_tiet
                    self.lcd.clear()
                    lay_du_lieu_thoi_tiet(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS,2)
                    utime.sleep(2)
                else:
                    current_menu = self.menu1

            elif current_menu == self.menu3:
                if self.Trang_thai_chon == 1:
                    from dong_ho import run_clock
                    self.lcd.clear()
                    run_clock(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 2:
                    from dong_ho import run_clock
                    self.lcd.clear()
                    run_clock(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 3:
                    from dong_ho import run_clock
                    self.lcd.clear()
                    run_clock(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS)
                    utime.sleep(2)
                elif self.Trang_thai_chon == 4:
                    from dong_ho import run_clock
                    self.lcd.clear()
                    run_clock(self.lcd, self.BUTTON_PIN_2, self.LCD_COLS, self.LCD_ROWS)
                else:
                    current_menu = self.menu1
                    
            elif current_menu == self.menu4:
                if self.Trang_thai_chon == 3:
                    current_menu = self.menu1
                else:
                    self.lcd.clear()
                    self.lcd.set_cursor(0, 0)
                    self.lcd.print(f"Ban chon: {self.menu4[self.Trang_thai_chon]}")
                    utime.sleep(2)