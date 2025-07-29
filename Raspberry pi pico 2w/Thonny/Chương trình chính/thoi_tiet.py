import urequests
import json
import time
from ket_noi_wifi import do_connect_wifi 

# Khai báo các biến toàn cục
API_KEYS = ["383c5c635c88590b37c698bc100f6377", "fe8d8c65cf345889139d8e545f57819a", "68c51539817878022c5315a3b403165c"]
current_key_index = 0
MAX_KEY_INDEX = len(API_KEYS) - 1

CITIES_DATA = [
    {"display_name": "Ha Noi", "lat": 21.0245, "lon": 105.8412}, 
    {"display_name": "Da Nang", "lat": 16.068, "lon": 108.212}, 
    {"display_name": "Ho Chi Minh", "lat": 10.762622, "lon": 106.660172} 
]
current_city_index = 0
UNITS = "metric"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

temperature_symbol = [0b00110, 0b01001, 0b01001, 0b00110, 0b00000, 0b00000, 0b00000, 0b00000]

# Hàm lấy dữ liệu thời tiết - không thay đổi nhiều, chỉ loại bỏ time.sleep(1) cuối cùng
def get_weather_data(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    global current_key_index
    api_key_to_use = API_KEYS[current_key_index]
    city_info = CITIES_DATA[current_city_index]
    city_display_name = city_info["display_name"] # Tên để hiển thị
    city_lat = city_info["lat"]
    city_lon = city_info["lon"]
    request_url = f"{BASE_URL}?lat={city_lat}&lon={city_lon}&appid={api_key_to_use}&units={UNITS}&lang=vi"
    retries = len(API_KEYS)
    lcd_obj.custom_char(0, temperature_symbol)
    for _ in range(retries):
        try:
            response = urequests.get(request_url)
            if response.status_code == 200:
                weather_data = json.loads(response.text)

                temperature = weather_data['main']['temp']
                humidity = weather_data['main']['humidity']
                wind_speed = weather_data['wind']['speed']

                if lcd_obj:
                    lcd_obj.clear()
                    lcd_obj.set_cursor(0, 0)
                    lcd_obj.print(f"City: {city_display_name}") 
                    lcd_obj.set_cursor(0, 1)
                    lcd_obj.print(f"Temp: {temperature:.1f}")
                    lcd_obj.print_custom_char(0)
                    lcd_obj.print("C")
                    lcd_obj.set_cursor(0, 2)
                    lcd_obj.print(f"Humid: {humidity}%")
                    lcd_obj.set_cursor(0, 3)
                    lcd_obj.print(f"Wind: {wind_speed:.1f} m/s")
                time.sleep(1)
                return True
            elif response.status_code == 429: # Lỗi giới hạn rate
                response.close()
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                print(f"API Key {api_key_to_use} hết lượt yêu cầu. Chuyển sang key tiếp theo. Đợi 5s.")
                time.sleep(5)
            else: # Các lỗi khác
                response.close()
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                print(f"Lỗi HTTP {response.status_code}. Chuyển sang key tiếp theo. Đợi 2s.")
                time.sleep(2)
        except Exception as e:
            print(f"Lỗi khi yêu cầu API: {e}. Chuyển sang key tiếp theo. Đợi 2s.")
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            time.sleep(2)
    return False

# Hàm chính để lấy và hiển thị dữ liệu thời tiết, có vòng lặp và kiểm tra nút thoát
def lay_du_lieu_thoi_tiet(lcd_obj, button_select_pin, lcd_cols, lcd_rows, city_index):
    global current_city_index
    current_city_index = city_index # Cập nhật thành phố được chọn
    
    if not do_connect_wifi():
        lcd_obj.clear()
        lcd_obj.print("Khong ket noi mang")
        time.sleep(2)
        return False # Trả về False để báo hiệu thất bại
    
    # Lấy dữ liệu lần đầu
    success = get_weather_data(lcd_obj, button_select_pin, lcd_cols, lcd_rows)
    if not success:
        lcd_obj.clear()
        lcd_obj.print("Khong lay du lieu")
        print("Không thể lấy dữ liệu thời tiết sau nhiều lần thử.")
        time.sleep(3) 
        return False # Trả về False để báo hiệu thất bại
    thoi_tiet_running = True
    while thoi_tiet_running:
        # Kiểm tra nút bấm để thoát
        if button_select_pin.value() == 0:
            time.sleep_ms(50) # Chống dội phím
            if button_select_pin.value() == 0:
                while button_select_pin.value() == 0: # Chờ nhả nút
                    time.sleep_ms(50)
                thoi_tiet_running = False
                continue 

    lcd_obj.clear()
    lcd_obj.print("Dang thoat...") 
    time.sleep(1)
    return True 