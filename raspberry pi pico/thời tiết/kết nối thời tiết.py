# Khai Baó thư viện 
import network
import time
import urequests 
import json  
# Địa chỉ và mật khẩu wifi
WIFI_CREDENTIALS = [
    ("TP-Link_8A5C", "84493378"),
    ("Phuc Dat", "anhtuan00"),
    ("Trang Tuan", "12345678"),
    ("Mywifi", "codefunny"),]
# API thời tiết
API_KEYS = [
    "383c5c635c88590b37c698bc100f6377",
    "fe8d8c65cf345889139d8e545f57819a",
    "68c51539817878022c5315a3b403165c",]
current_key_index = 0
MAX_KEY_INDEX = len(API_KEYS) - 1
CITY_NAME = "Hanoi"   
UNITS = "metric" 
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

def connect_to_wifi(): # Hàm kết nối wifi 
    wlan = network.WLAN(network.STA_IF)	# Khởi tạo đối tượng WLAN ở chế độ Station (STA_IF)
    wlan.active(True)	# Kích hoạt giao diện Wi-Fi
    
    for ssid, password in WIFI_CREDENTIALS:	 # Vòng lặp này sẽ duyệt qua từng cặp SSID và Password trong danh sách WIFI_CREDENTIALS
        wlan.connect(ssid, password)	# Gửi lệnh kết nối Wi-Fi tới SSID và Password hiện tại
        wait = 15	# Đặt thời gian chờ tối đa là 15 giây cho mỗi lần thử kết nối
        while wait > 0 and wlan.status() != network.STAT_GOT_IP:
            time.sleep(1)	 # Tạm dừng 1 giây để chờ kết nối
            wait -= 1	# Giảm bộ đếm thời gian chờ
        if wlan.status() == network.STAT_GOT_IP:
            print("Kết nối thành công")
            return	# Thoát khỏi hàm ngay lập tức 
    print("Kết nối thất bại")
    
def get_weather_data():	# Hàm thời tiết
    global current_key_index
    
    # Lấy API Key hiện tại
    api_key_to_use = API_KEYS[current_key_index]
    request_url = f"{BASE_URL}?q={CITY_NAME}&appid={api_key_to_use}&units={UNITS}"
    
    # Số lần thử lại với các API Key khác nhau
    retries = len(API_KEYS) # Thử mỗi key một lần   

    for _ in range(retries):
        try:
            response = urequests.get(request_url)
            if response.status_code == 200:
                weather_data = json.loads(response.text)
                
                # Trích xuất và in dữ liệu
                temperature = weather_data['main']['temp']
                humidity = weather_data['main']['humidity']
                wind_speed = weather_data['wind']['speed']

                print(f"Thành phố: {weather_data['name']}")
                print(f"Nhiệt độ: {temperature}°C")
                print(f"Độ ẩm: {humidity}%")
                print(f"Tốc độ gió: {wind_speed} m/s")
                
                response.close()
                return True # Lấy thành công
            elif response.status_code == 429: # Too Many Requests - vượt quá giới hạn API
                response.close()
                api_key_to_use = switch_api_key() # Chuyển sang key tiếp theo
                request_url = f"{BASE_URL}?q={CITY_NAME}&appid={api_key_to_use}&units={UNITS}" # Cập nhật URL
                time.sleep(1) # Chờ một chút trước khi thử lại
            else:
                break 
        except Exception as e:
            time.sleep(1)
    return False # Không lấy được dữ liệu sau khi thử hết các key

if __name__ == '__main__':
    connect_to_wifi()
    get_weather_data()

