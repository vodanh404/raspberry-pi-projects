import utime
import time
import network
import config
from st7735 import sysfont 

def do_connect_wifi(max_wait=10):
    """
    Kết nối với mạng Wi-Fi từ danh sách đã cho trong config.py.
    Trả về True nếu kết nối thành công, ngược lại là False.
    """
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)

    if sta_if.isconnected():
        print('Đã kết nối Wi-Fi. IP:', sta_if.ifconfig()[0])
        return True

    print('Đang tìm mạng Wi-Fi để kết nối...')
    for ssid, password in config.WIFI_NETWORKS:
        print(f'Thử kết nối với "{ssid}"...')
        sta_if.connect(ssid, password)

        # Chờ tối đa `max_wait` giây để kết nối
        timeout = time.time() + max_wait
        while time.time() < timeout:
            if sta_if.isconnected():
                print(f'Kết nối thành công với "{ssid}"!')
                print('Địa chỉ IP:', sta_if.ifconfig()[0])
                print(f'Tên Wi-Fi đã kết nối: {ssid}')
                return True
            time.sleep(0.5)

        print(f'Không thể kết nối với "{ssid}". Đang thử mạng tiếp theo...')
        sta_if.disconnect()
        time.sleep(1)

    print('Đã thử hết tất cả các mạng, không thể kết nối.')
    sta_if.active(False)
    return False

def hien_thi_ket_noi_wifi(tft_obj, button_select_pin, bg_color, text_color):
    """
    Hiển thị kết quả kết nối Wi-Fi trên màn hình TFT.
    """
    tft_obj.fill(bg_color)
    # Sử dụng sysfont.sysfont
    tft_obj.text((10, 10), "Dang ket noi...", text_color, sysfont.sysfont, 1)

    is_wifi_connected = do_connect_wifi()
    
    tft_obj.fill(bg_color)
    if is_wifi_connected:
        tft_obj.text((10, 10), "Ket noi thanh cong!", text_color, sysfont.sysfont, 1)
        # Lấy IP và hiển thị
        ip = network.WLAN(network.STA_IF).ifconfig()[0]
        tft_obj.text((10, 30), f"IP: {ip}", text_color, sysfont.sysfont, 1)
    else:
        tft_obj.text((10, 10), "Khong ket noi mang!", text_color, sysfont.sysfont, 1)

    # Vòng lặp để giữ màn hình hiển thị và chờ nút thoát
    tft_obj.text((10, 50), "Nhan Chon de thoat", text_color, sysfont.sysfont, 1)
    
    while True:
        if button_select_pin.value() == 0:
            utime.sleep(0.05)
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            return True
        utime.sleep(0.1)
