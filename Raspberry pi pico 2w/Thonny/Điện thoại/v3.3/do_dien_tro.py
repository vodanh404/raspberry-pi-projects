# -*- coding: utf-8 -*-
import utime
from machine import Pin
from st7735 import sysfont
from DIYables_Pico_Keypad import Keypad
# --- PHAN CAU HINH ---
# Ban phim 4x4
NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [9, 8, 7, 6]
COLUMN_PINS = [5, 4, 3, 2]
KEYMAP = [
    '1', '2', '3', '+',
    '4', '5', '6', '-',
    '7', '8', '9', 'x',
    'AC', '0', '=', ':'
]
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_COLS, NUM_ROWS)
keypad.set_debounce_time(200)

# --- CO SO DU LIEU MAU DIEN TRO (Thiet ke lai cho dung thuc te) ---

# Bang tra gia tri cho cac vach so
VALUE_MAP = {
    'Den': 0, 'Nau': 1, 'Do': 2, 'Cam': 3, 'Vang': 4,
    'Luc': 5, 'Lam': 6, 'Tim': 7, 'Xam': 8, 'Trang': 9
}

# Bang tra he so nhan
MULTIPLIER_MAP = {
    'Den': 1, 'Nau': 10, 'Do': 100, 'Cam': 1000, 'Vang': 10000,
    'Luc': 100000, 'Lam': 1000000, 'Tim': 10000000,
    'Nhu vang': 0.1, 'Nhu bac': 0.01
}

# Bang tra dung sai
TOLERANCE_MAP = {
    'Nau': '±1%', 'Do': '±2%', 'Luc': '±0.5%', 'Lam': '±0.25%',
    'Tim': '±0.1%', 'Xam': '±0.05%', 'Nhu vang': '±5%', 'Nhu bac': '±10%',
    'Khong mau': '±20%'
}

# Bang tra he so nhiet do (PPM)
PPM_MAP = {
    'Nau': '100 ppm/K', 'Do': '50 ppm/K', 'Cam': '15 ppm/K',
    'Vang': '25 ppm/K', 'Lam': '10 ppm/K', 'Tim': '5 ppm/K'
}

# DANH SACH CAC MAU HOP LE CHO TUNG VACH
# Vach so (khong bao gom Den o vach dau tien)
DIGIT_COLORS = ['Nau', 'Do', 'Cam', 'Vang', 'Luc', 'Lam', 'Tim', 'Xam', 'Trang', 'Den']
# Vach he so nhan
MULTIPLIER_COLORS = ['Den', 'Nau', 'Do', 'Cam', 'Vang', 'Luc', 'Lam', 'Tim', 'Nhu vang', 'Nhu bac']
# Vach dung sai
TOLERANCE_COLORS = ['Nau', 'Do', 'Luc', 'Lam', 'Tim', 'Xam', 'Nhu vang', 'Nhu bac', 'Khong mau']
# Vach he so nhiet
PPM_COLORS = ['Nau', 'Do', 'Cam', 'Vang', 'Lam', 'Tim']

# --- CAC HAM TIEN ICH ---

def format_resistance_value(value):
    """Dinh dang gia tri dien tro sang don vi Ohm, kOhm, MOhm, GOhm mot cach linh hoat."""
    value = float(value)
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} GOhm".replace('.00', '')
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f} MOhm".replace('.00', '')
    if value >= 1000:
        return f"{value / 1000:.2f} kOhm".replace('.00', '')
    # Su dung .2f de xu ly cac gia tri < 1 Ohm (khi nhan voi 0.1, 0.01)
    if value == int(value):
        return f"{int(value)} Ohm"
    else:
        return f"{value:.2f} Ohm"

def get_valid_colors_for_band(band_index, num_total_bands):
    """Tra ve danh sach cac mau hop le dua tren vi tri vach dang chon."""
    # Vach 1, 2 la vach gia tri
    if band_index in [0, 1]:
        # Vach dau tien khong the la mau den
        return DIGIT_COLORS[:-1] if band_index == 0 else DIGIT_COLORS
    
    # Logic cho he dien tro 3, 4 vach mau
    if num_total_bands <= 4:
        if band_index == 2: return MULTIPLIER_COLORS
        if band_index == 3: return TOLERANCE_COLORS
        
    # Logic cho he dien tro 5, 6 vach mau
    else:
        if band_index == 2: return DIGIT_COLORS
        if band_index == 3: return MULTIPLIER_COLORS
        if band_index == 4: return TOLERANCE_COLORS
        if band_index == 5: return PPM_COLORS
        
    return [] # Truong hop khong hop le

# --- HAM CHINH ---

def run_resistor(tft_obj, button_select_pin, bg_color, text_color):
    """Chay ung dung tinh toan dien tro."""
    is_running = True
    last_key = None
    
    selected_bands = []
    color_index = 0
    num_bands_selector = 4 # Mac dinh tinh cho dien tro 4 vach
    is_selecting_num_bands = True # Bat dau bang viec chon so vach mau
    
    def display_ui():
        """Cap nhat toan bo giao dien nguoi dung."""
        tft_obj.fill(bg_color)
        
        if is_selecting_num_bands:
            tft_obj.text((5, 10), "Chon so vach mau:", text_color, sysfont.sysfont, 1)
            tft_obj.text((10, 30), f"-> {num_bands_selector} vach", text_color, sysfont.sysfont, 2)
            tft_obj.text((5, 60), "Dung 'A' hoac 'B'", text_color, sysfont.sysfont, 1)
            tft_obj.text((5, 75), "Nhan '#' de chon.", text_color, sysfont.sysfont, 1)
            return

        # --- Giao dien khi dang chon mau ---
        tft_obj.text((5, 5), f"Dien tro {num_bands_selector} vach", text_color, sysfont.sysfont, 1)
        
        # Hien thi cac dai mau da chon
        y_pos = 20
        for i, band_name in enumerate(selected_bands):
            tft_obj.text((10, y_pos), f"Vach {i+1}: {band_name}", text_color, sysfont.sysfont, 1)
            y_pos += 15

        current_band_index = len(selected_bands)
        if current_band_index < num_bands_selector:
            # Hien thi menu chon mau cho vach tiep theo
            valid_colors = get_valid_colors_for_band(current_band_index, num_bands_selector)
            if valid_colors:
                current_color_name = valid_colors[color_index]
                tft_obj.text((5, 90), f"Chon vach {current_band_index + 1}:", text_color, sysfont.sysfont, 1)
                tft_obj.text((10, 105), f"-> {current_color_name}", text_color, sysfont.sysfont, 1.5)
        
        # Tinh toan va hien thi ket qua neu da chon du vach
        if len(selected_bands) == num_bands_selector:
            calculate_and_display()

    def calculate_and_display():
        """Tinh toan gia tri dien tro tu cac vach mau va hien thi."""
        try:
            num_digit_bands = 2 if num_bands_selector <= 4 else 3
            
            # Lay cac vach gia tri
            digit_bands = selected_bands[:num_digit_bands]
            
            # Ghep cac so lai
            str_value = "".join([str(VALUE_MAP[color]) for color in digit_bands])
            base_value = int(str_value)
            
            # Lay he so nhan
            multiplier_color = selected_bands[num_digit_bands]
            multiplier = MULTIPLIER_MAP[multiplier_color]
            
            # Tinh gia tri cuoi cung
            final_value = base_value * multiplier
            
            # Hien thi ket qua
            y_pos = 90
            tft_obj.text((5, y_pos), "Ket qua:", text_color, sysfont.sysfont, 1)
            y_pos += 15
            tft_obj.text((10, y_pos), f"{format_resistance_value(final_value)}", text_color, sysfont.sysfont, 1)
            y_pos += 15

            # Hien thi dung sai
            if num_bands_selector >= 4:
                tolerance_color = selected_bands[num_digit_bands + 1]
                tolerance = TOLERANCE_MAP.get(tolerance_color, "N/A")
                tft_obj.text((10, y_pos), f"Dung sai: {tolerance}", text_color, sysfont.sysfont, 1)
                y_pos += 15

            # Hien thi he so nhiet
            if num_bands_selector == 6:
                ppm_color = selected_bands[5]
                ppm = PPM_MAP.get(ppm_color, "N/A")
                tft_obj.text((10, y_pos), f"HS nhiet: {ppm}", text_color, sysfont.sysfont, 1)

        except (KeyError, IndexError) as e:
            tft_obj.text((10, 100), "Loi tinh toan!", text_color, sysfont.sysfont, 1)
            print(f"Error: {e}") # In loi ra console de debug

    # Vong lap chinh
    display_ui()
    while is_running:
        key = keypad.get_key()
        
        if button_select_pin.value() == 0:
            is_running = False
            continue

        if key and key != last_key:
            last_key = key
            
            if is_selecting_num_bands:
                if key == '+': num_bands_selector = min(6, num_bands_selector + 1)
                elif key == '-': num_bands_selector = max(3, num_bands_selector - 1)
                elif key == '=': is_selecting_num_bands = False
            
            else: # Dang chon mau
                current_band_index = len(selected_bands)
                if current_band_index < num_bands_selector:
                    valid_colors = get_valid_colors_for_band(current_band_index, num_bands_selector)
                    num_valid_colors = len(valid_colors)

                    if key == '+':
                        color_index = (color_index + 1) % num_valid_colors
                    elif key == '-':
                        color_index = (color_index - 1 + num_valid_colors) % num_valid_colors
                    elif key == '=':
                        selected_color = valid_colors[color_index]
                        selected_bands.append(selected_color)
                        color_index = 0 # Reset chi so mau cho vach tiep theo
                
                if key == 'AC':
                    # Reset lai tu dau
                    selected_bands = []
                    color_index = 0
                    is_selecting_num_bands = True
            
            display_ui() # Cap nhat man hinh sau moi lan nhan phim

        if not key:
            last_key = None
            
        utime.sleep_ms(50)

