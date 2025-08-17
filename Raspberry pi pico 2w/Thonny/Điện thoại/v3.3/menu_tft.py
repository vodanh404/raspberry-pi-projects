from machine import SPI, Pin
import utime
from st7735 import TFT, sysfont

# --- Cấu hình giao diện người dùng (Biến toàn cục đã được chuyển vào class) ---
placeholder_font = sysfont.sysfont
placeholder_text_color = TFT.CYAN
placeholder_bg_color = TFT.BLACK

def placeholder_function(tft_obj, message):
    """
    Một hàm giữ chỗ để mô phỏng các chức năng.
    Hàm này được dùng để hiển thị một thông báo tạm thời khi chọn một mục menu.
    """
    tft_obj.fill(placeholder_bg_color)
    
    # Đảm bảo màu chữ hiển thị rõ trên mọi nền
    text_color = TFT.WHITE
    if placeholder_bg_color == TFT.WHITE:
        text_color = TFT.BLACK
        
    tft_obj.text((10, 10), message, text_color, placeholder_font, 1, nowrap=True, aBgColor=placeholder_bg_color)
    utime.sleep(2)

class TFTMenu:
    """Lớp quản lý menu trên màn hình TFT ST7735."""
    
    def __init__(self, spi, dc, rst, cs, button_up_pin, button_down_pin, button_select_pin):   
        self.DC = dc
        self.RST = rst
        self.CS = cs
        
        self.spi = spi
        self.tft = TFT(spi, self.DC, self.RST, self.CS)
        
        self.current_rotation = 3
        
        self.tft.initr()
        self.tft.rgb(True)
        self.tft.rotation(self.current_rotation)
        
        # Biến instance cho màu sắc và font chữ
        self.font = sysfont.sysfont
        self.text_color = TFT.CYAN
        self.select_color = TFT.BLUE
        self.bg_color = TFT.BLACK
        
        self.tft.fill(self.bg_color)
        
        self.BUTTON_PIN_0 = Pin(button_up_pin, Pin.IN, Pin.PULL_UP)
        self.BUTTON_PIN_1 = Pin(button_down_pin, Pin.IN, Pin.PULL_UP)
        self.BUTTON_PIN_2 = Pin(button_select_pin, Pin.IN, Pin.PULL_UP)
        
        # --- Định nghĩa Menu ---
        self.menu1 = ["Menu chinh", "1.May tinh", "2.Thoi tiet", "3.Phat nhac", "4.Dong ho","5.Gui Thu",
                      "6.Cong cu","7.Bo suu tam", "8.Bang tuan hoan","9.Ma QR","10.Ghi chu","11.Game","12.Cai dat"]
        self.menu2 = ["Dia diem", "1.Ha Noi", "2.Da Nang", "3.Ho Chi Minh", "4.Thoat"]
        self.menu3 = ["Tinh Nang", "1.Dong ho", "2.Bam gio", "3.Dem Nguoc", "4.Dong ho ca chua","5.Lich", "6.Thoat"]
        self.menu4 = ["Cai dat", "1.Wifi", "2.Thay doi huong", "3.Giao dien","4.Thong tin", "5.Thoat"]
        self.menu5 = ["Chuc nang", "1.Do dien tro", "2.Bang quy uoc", "3.Thoat"]
        self.menu6 = ["Game", "1.Ping", "2.Bang quy uoc", "3.Thoat"]
        
        self.menu_giao_dien = ["Giao Dien", "1.Mac Dinh", "2.Giao dien toi", "3.Do & Den","4.Xanh la & Den",
                               "5.Cam & Xanh lam","6.Vang & Den","7.Hong & Den","8.Nau & Vang","9.Thoat"]
        
        # Thêm biến để quản lý vị trí cuộn
        self.scroll_offset = 0

    def set_theme(self, theme_choice):
        """Đặt màu sắc cho giao diện người dùng."""
        if theme_choice == 1: self.text_color = TFT.CYAN, self.select_color = TFT.BLUE, self.bg_color = TFT.BLACK
        elif theme_choice == 2: self.text_color = TFT.WHITE, self.select_color = TFT.GRAY, self.bg_color = TFT.BLACK
        elif theme_choice == 3: self.text_color = TFT.RED, self.select_color = TFT.GRAY, self.bg_color = TFT.BLACK
        elif theme_choice == 4: self.text_color = TFT.GREEN, self.select_color = TFT.GRAY, self.bg_color = TFT.BLACK
        elif theme_choice == 5: self.text_color = TFT.ORANGE, self.select_color = TFT.BLUE, self.bg_color = TFT.BLACK
        elif theme_choice == 6: self.text_color = TFT.YELLOW, self.select_color = TFT.GRAY, self.bg_color = TFT.BLACK
        elif theme_choice == 7: self.text_color = TFT.PINK, self.select_color = TFT.GRAY, self.bg_color = TFT.BLACK
        elif theme_choice == 8: self.text_color = TFT.BROWN, self.select_color = TFT.YELLOW, self.bg_color = TFT.BLACK
        
    def toggle_orientation(self):
        """Chuyển đổi giữa 4 hướng xoay của màn hình."""
        self.current_rotation = (self.current_rotation + 1) % 4
        self.tft.rotation(self.current_rotation)
        self.tft.fill(self.bg_color)
    
    def draw_menu_item(self, menu, index, is_selected, y_pos):
        """
        Vẽ lại một mục menu cụ thể.
        """
        item_text = menu[index]
        
        text_color = self.text_color
        bg_color = self.bg_color
        
        if is_selected:
            text_color = TFT.WHITE
            bg_color = self.select_color
        
        # Xóa dòng cũ trước khi vẽ dòng mới
        item_height = self.font["Height"] + 2
        self.tft.fillrect((0, y_pos), (self.tft.size()[0], item_height), bg_color)
        
        # Vẽ văn bản lên trên nền
        self.tft.text((10, y_pos + 1), item_text, text_color, self.font, 1, nowrap=True)

    def draw_menu(self, menu, selected_index):
        """
        Vẽ lại toàn bộ menu một lần và xử lý logic cuộn.
        Hàm này chỉ nên gọi khi vào một menu mới.
        """
        self.tft.fill(self.bg_color)
        
        # Vẽ tiêu đề menu
        title_color = TFT.WHITE if self.bg_color == TFT.BLACK else TFT.BLACK
        self.tft.text((10, 5), menu[0], title_color, self.font, 1, nowrap=True, aBgColor=self.bg_color)
        
        screen_height = self.tft.size()[1]
        item_height = self.font["Height"] + 2
        
        # Cập nhật vị trí cuộn để mục được chọn luôn hiển thị
        max_items_per_screen = (screen_height - 15) // item_height
        if selected_index >= self.scroll_offset + max_items_per_screen: self.scroll_offset = selected_index - max_items_per_screen + 1
        if selected_index < self.scroll_offset: self.scroll_offset = selected_index

        # Vẽ các mục menu
        for i in range(1, len(menu)):
            y_pos = 15 + (i - self.scroll_offset) * item_height
            
            # Chỉ vẽ các mục nằm trong khung màn hình
            if y_pos >= 15 and y_pos + item_height <= screen_height:
                is_selected = (i == selected_index)
                self.draw_menu_item(menu, i, is_selected, y_pos)
            
    def navigate_menu(self, current_menu):
        """Quản lý logic điều hướng menu bằng nút bấm."""
        selected_index = 1
        self.scroll_offset = 0 # Đặt lại vị trí cuộn khi vào menu mới
        
        # Vẽ menu lần đầu tiên khi vào
        self.draw_menu(current_menu, selected_index)

        while True:
            utime.sleep_ms(100) # Debounce 100ms
            
            old_selection = selected_index
            
            if self.BUTTON_PIN_0.value() == 0:
                selected_index -= 1
                if selected_index < 1:
                    selected_index = len(current_menu) - 1
                while self.BUTTON_PIN_0.value() == 0:
                    utime.sleep_ms(10)
            
            if self.BUTTON_PIN_1.value() == 0:
                selected_index += 1
                if selected_index >= len(current_menu):
                    selected_index = 1
                while self.BUTTON_PIN_1.value() == 0:
                    utime.sleep_ms(10)
            
            if self.BUTTON_PIN_2.value() == 0:
                while self.BUTTON_PIN_2.value() == 0:
                    utime.sleep_ms(10)
                return selected_index
            
            if selected_index != old_selection:
                screen_height = self.tft.size()[1]
                item_height = self.font["Height"] + 2
                max_items_per_screen = (screen_height - 15) // item_height
                
                # Logic cuộn: Kiểm tra nếu mục mới nằm ngoài màn hình hiện tại
                if selected_index >= self.scroll_offset + max_items_per_screen or selected_index < self.scroll_offset:
                    # Nếu cuộn, vẽ lại toàn bộ menu để cập nhật hiển thị
                    self.scroll_offset = selected_index - max_items_per_screen + 1 if selected_index >= self.scroll_offset + max_items_per_screen else selected_index
                    self.draw_menu(current_menu, selected_index)
                else:
                    # Nếu không cuộn, chỉ cập nhật 2 mục: cũ và mới
                    y_pos_old = 15 + (old_selection - self.scroll_offset) * item_height
                    y_pos_new = 15 + (selected_index - self.scroll_offset) * item_height
                    
                    self.draw_menu_item(current_menu, old_selection, False, y_pos_old)
                    self.draw_menu_item(current_menu, selected_index, True, y_pos_new)
                    
    def run_menu(self,):
        """Hàm chính để chạy logic menu."""
        current_menu = self.menu1
        while True:
            selection = self.navigate_menu(current_menu)

            if current_menu == self.menu1:
                if selection == 1:
                    from may_tinh import run_calculator
                    run_calculator(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 2:
                    current_menu = self.menu2
                elif selection == 3:
                    from phat_nhac import run_music_player
                    run_music_player(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 4:
                    current_menu = self.menu3
                elif selection == 5:
                    from gmail import run_Gmail
                    run_Gmail(self.tft, self.BUTTON_PIN_2, self.BUTTON_PIN_0, self.bg_color, self.text_color)
                elif selection == 6:
                    current_menu = self.menu5
                elif selection == 7:
                    from bo_suu_tam import run_image_viewer
                    run_image_viewer(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color,self.current_rotation)
                elif selection == 8:
                    from bang_tuan_hoan import Bang_tuan_hoan
                    Bang_tuan_hoan(self.tft, self.BUTTON_PIN_2, self.BUTTON_PIN_0, self.BUTTON_PIN_1, self.bg_color, self.text_color)
                elif selection == 9:
                    from ma_qr import run_qr
                    run_qr(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color,self.current_rotation)
                elif selection == 10:
                    from ghi_chu import run_note
                    run_note(self.tft, self.BUTTON_PIN_2, self.BUTTON_PIN_0, self.BUTTON_PIN_1, self.bg_color, self.text_color)
                elif selection == 11:
                    current_menu = self.menu6
                elif selection == 12:
                    current_menu = self.menu4
                    
            elif current_menu == self.menu2:
                from thoi_tiet import lay_du_lieu_thoi_tiet
                if selection == 1:  lay_du_lieu_thoi_tiet(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color,0)
                elif selection == 2: lay_du_lieu_thoi_tiet(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color,1)
                elif selection == 3: lay_du_lieu_thoi_tiet(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color,2)
                elif selection == 4: current_menu = self.menu1
            
            elif current_menu == self.menu3:
                from dong_ho import run_clock, Bam_gio, Dem_nguoc, Dong_ho_ca_chua, Xem_Lich
                if selection == 1: run_clock(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 2: Bam_gio(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 3: Dem_nguoc(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 4: Dong_ho_ca_chua(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 5: Xem_Lich(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 6: current_menu = self.menu1
            elif current_menu == self.menu4:
                if selection == 1:
                    from ket_noi_wifi import hien_thi_ket_noi_wifi
                    hien_thi_ket_noi_wifi(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 2:
                    self.toggle_orientation()
                elif selection == 3:
                    current_menu = self.menu_giao_dien
                elif selection == 4:
                    from thong_tin_thiet_bi import thong_tin
                    thong_tin(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 5:
                    current_menu = self.menu1

            elif current_menu == self.menu_giao_dien:
                if selection == 1:self.set_theme(1)
                elif selection == 2:self.set_theme(2)
                elif selection == 3:self.set_theme(3)
                elif selection == 4:self.set_theme(4)
                elif selection == 5:self.set_theme(5)
                elif selection == 6:self.set_theme(6)
                elif selection == 7:self.set_theme(7)
                elif selection == 8:self.set_theme(8)
                elif selection == 9:current_menu = self.menu4
            
            elif current_menu == self.menu5:
                if selection == 1:
                    from do_dien_tro import run_resistor
                    run_resistor(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 2:
                    from quy_uoc import run_quy_uoc
                    run_quy_uoc(self.tft, self.BUTTON_PIN_2, self.BUTTON_PIN_0, self.BUTTON_PIN_1, self.bg_color, self.text_color)
                elif selection == 3:
                    current_menu = self.menu1
                    
            elif current_menu == self.menu6:
                if selection == 1:
                    from pong_game import run_pong_game
                    run_pong_game(self.tft, self.BUTTON_PIN_2, self.bg_color, self.text_color)
                elif selection == 2:
                    from quy_uoc import run_quy_uoc
                    run_quy_uoc(self.tft, self.BUTTON_PIN_2, self.BUTTON_PIN_0, self.BUTTON_PIN_1, self.bg_color, self.text_color)
                elif selection == 3:
                    current_menu = self.menu1