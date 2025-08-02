import utime
import time
import network
import config

def do_connect_wifi(max_wait=10):
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

def hien_thi_ket_qua(lcd_obj, button_select_pin, lcd_cols, lcd_rows):
    is_wifi_connected = do_connect_wifi() 
    lcd_obj.clear()
    if is_wifi_connected:
        lcd_obj.print("Ket noi thanh cong!")
    else:
        lcd_obj.print("Khong ket noi mang!")

    # Vòng lặp để giữ màn hình hiển thị và chờ nút thoát
    display_active = True
    while display_active:
        if button_select_pin.value() == 0:
            lcd_obj.clear()
            lcd_obj.print("Dang thoat...")
            utime.sleep(1) 
            while button_select_pin.value() == 0:
                utime.sleep(0.05)
            display_active = False 
            lcd_obj.clear() 
            return True
        utime.sleep(0.1) 
    