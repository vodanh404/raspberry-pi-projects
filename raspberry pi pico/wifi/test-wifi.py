# Khai Baó thư viện 
import network
import time
# Địa chỉ và mật khẩu wifi
WIFI_CREDENTIALS = [
    ("TP-Link_8A5C", "84493378"),
    ("Phuc Dat", "anhtuan00"),
    ("Trang Tuan", "12345678"),
    ("Mywifi", "codefunny"),]

def connect_to_wifi():
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

if __name__ == '__main__':
    connect_to_wifi()
