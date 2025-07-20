# Khai Baó thư viện 
import network
import time
import urequests 
import json
from machine import I2C, Pin
from DIYables_MicroPython_LCD_I2C import LCD_I2C
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
# Thiết lập màn hình LCD 20x4
I2C_ADDR = 0x27  
LCD_COLS = 20
LCD_ROWS = 4
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
lcd = LCD_I2C(i2c, I2C_ADDR, LCD_ROWS, LCD_COLS)
lcd.backlight_on()
lcd.clear()

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

                if lcd:
                    lcd.clear()
                    lcd.set_cursor(0, 0)
                    lcd.print(f"City: {weather_data['name']}")
                    lcd.set_cursor(0, 1)
                    lcd.print(f"Temp: {temperature:.1f}C")
                    lcd.set_cursor(0, 2)
                    lcd.print(f"Humid: {humidity}%")
                    lcd.set_cursor(0, 3)
                    lcd.print(f"Wind: {wind_speed:.1f} m/s")
                time.sleep(1)
                return True # Lấy thành công

            elif response.status_code == 429: # Too Many Requests
                response.close()
                # Chuyển sang key tiếp theo ngay trong hàm này
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                time.sleep(5) # Chờ một chút trước khi thử lại với key mới
            else:
                response.close()
                current_key_index = (current_key_index + 1) % len(API_KEYS)
                time.sleep(2) # Chờ một chút trước khi thử key tiếp theo
        except Exception as e:
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            time.sleep(2) # Chờ một chút trước khi thử key tiếp theo
    return False # Không lấy được dữ liệu sau khi thử hết các key

if __name__ == '__main__':
    connect_to_wifi()
    get_weather_data()
