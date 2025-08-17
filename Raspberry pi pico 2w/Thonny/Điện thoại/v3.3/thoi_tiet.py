# thoi_tiet.py
import urequests
import json
import utime
from ket_noi_wifi import do_connect_wifi
from st7735 import sysfont

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

# Hàm lấy dữ liệu thời tiết
def get_weather_data(tft_obj, bg_color, text_color):
    """
    Lấy dữ liệu thời tiết từ OpenWeatherMap API và hiển thị lên màn hình TFT.
    Hàm này sẽ thử với các API key khác nhau nếu key hiện tại bị lỗi hoặc hết lượt yêu cầu.
    Trả về True nếu thành công, ngược lại False.
    """
    global current_key_index
    city_info = CITIES_DATA[current_city_index]
    city_display_name = city_info["display_name"]
    city_lat = city_info["lat"]
    city_lon = city_info["lon"]
    retries = len(API_KEYS)
    
    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), "Dang tai du lieu...", text_color, sysfont.sysfont, 1)
    for i in range(retries):
        api_key_to_use = API_KEYS[current_key_index]
        request_url = f"{BASE_URL}?lat={city_lat}&lon={city_lon}&appid={api_key_to_use}&units={UNITS}&lang=en"

        try:
            response = urequests.get(request_url)
            if response.status_code == 200:
                data_str = response.text  # Đọc toàn bộ dữ liệu trước khi đóng
                response.close()          # Đóng kết nối sau khi đã đọc
                weather_data = json.loads(data_str)

                temperature = weather_data['main']['temp']
                humidity = weather_data['main']['humidity']
                wind_speed = weather_data['wind']['speed']
                description = weather_data['weather'][0]['description']

                tft_obj.fill(bg_color)
                tft_obj.text((10, 10), f"City: {city_display_name}", text_color, sysfont.sysfont, 1)
                tft_obj.text((10, 30), f"Temp: {temperature:.1f} C" , text_color, sysfont.sysfont, 1)
                tft_obj.text((10, 50), f"Humid: {humidity}%", text_color, sysfont.sysfont, 1)
                tft_obj.text((10, 70), f"Wind: {wind_speed:.1f} m/s", text_color, sysfont.sysfont, 1)
                tft_obj.text((10, 90), f"Status: {description}", text_color, sysfont.sysfont, 1)
                
                return True
            
            elif response.status_code == 429: # Lỗi giới hạn rate
                response.close()
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                tft_obj.fill(bg_color)
                tft_obj.text((10, 10), "API Key het luot.", text_color, sysfont.sysfont, 1)
                tft_obj.text((10, 30), "Chuyen sang key tiep theo", text_color, sysfont.sysfont, 1)
                utime.sleep(3)
                continue
            
            else: # Các lỗi khác
                response.close()
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                tft_obj.fill(bg_color)
                tft_obj.text((10, 10), f"Loi HTTP {response.status_code}.", text_color, sysfont.sysfont, 1)
                tft_obj.text((10, 30), "Chuyen sang key tiep theo.", text_color, sysfont.sysfont, 1)
                utime.sleep(2)
                continue
                
        except Exception as e:
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Loi khi yeu cau API.", text_color, sysfont.sysfont, 1)
            tft_obj.text((10, 30), "Chuyen sang key tiep theo", text_color, sysfont.sysfont, 1)
            utime.sleep(2)
            continue
            
    # Nếu tất cả các lần thử đều thất bại
    return False

# Hàm chính để lấy và hiển thị dữ liệu thời tiết
def lay_du_lieu_thoi_tiet(tft_obj, button_select_pin, bg_color, text_color, city_index):
    """
    Hàm chính để quản lý việc hiển thị dữ liệu thời tiết và thoát.
    Vòng lặp sẽ cập nhật dữ liệu và kiểm tra nút bấm để thoát.
    """
    global current_city_index
    current_city_index = city_index # Cập nhật thành phố được chọn
    
    if not do_connect_wifi():
        tft_obj.fill(bg_color)
        tft_obj.text((10, 10), "Khong ket noi mang", text_color, sysfont.sysfont, 1)
        utime.sleep(3)
        return False
    
    # Cập nhật dữ liệu lần đầu
    success = get_weather_data(tft_obj, bg_color, text_color)
    if not success:
        tft_obj.fill(bg_color)
        tft_obj.text((10, 10), "Khong the lay du lieu.", text_color, sysfont.sysfont, 1)
        tft_obj.text((10, 30), "Vui long thu lai sau.", text_color, sysfont.sysfont, 1)
        print("Khong the lay du lieu thoi tiet sau nhieu lan thu.")
        utime.sleep(3)
        return False

    thoi_tiet_running = True
    last_update_time = utime.time()
    UPDATE_INTERVAL = 900 # Cập nhật sau mỗi 15 phút (900 giây)

    while thoi_tiet_running:
        # Kiểm tra nút bấm để thoát
        if button_select_pin.value() == 0:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
            utime.sleep(1)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            thoi_tiet_running = False
            continue

        # Cập nhật dữ liệu thời tiết sau một khoảng thời gian
        current_time = utime.time()
        if current_time - last_update_time >= UPDATE_INTERVAL:
            tft_obj.fill(bg_color)
            tft_obj.text((10, 10), "Dang cap nhat du lieu...", text_color, sysfont.sysfont, 1)
            success = get_weather_data(tft_obj, bg_color, text_color)
            if success:
                last_update_time = current_time
            else:
                # Nếu không thể cập nhật, giữ nguyên dữ liệu cũ và chờ lần cập nhật tiếp theo
                print("Cap nhat du lieu that bai. Giu nguyen du lieu cu.")
                last_update_time = current_time # Đặt lại thời gian để thử lại sau 15 phút
        
        utime.sleep(1)
    
    return True