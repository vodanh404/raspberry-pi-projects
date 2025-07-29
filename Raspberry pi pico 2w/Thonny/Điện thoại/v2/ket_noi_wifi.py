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