import smbus
import time

class DS1307:
    def __init__(self, bus_number=1):
        self.bus = smbus.SMBus(bus_number)
        self.address = 0x68

    def _bcd_to_int(self, bcd):
        """Chuyển đổi số BCD sang số thập phân."""
        return ((bcd & 0xf0) >> 4) * 10 + (bcd & 0x0f)

    def _int_to_bcd(self, val):
        """Chuyển đổi số thập phân sang số BCD."""
        return ((val // 10) << 4) | (val % 10)

    def read_time(self):
        """Đọc thời gian hiện tại từ RTC."""
        # Đọc 7 bytes dữ liệu từ thanh ghi 0x00
        data = self.bus.read_i2c_block_data(self.address, 0x00, 7)
        
        seconds = self._bcd_to_int(data[0] & 0x7f)
        minutes = self._bcd_to_int(data[1])
        hours = self._bcd_to_int(data[2] & 0x3f) # Chế độ 24h
        day_of_week = data[3]
        day = self._bcd_to_int(data[4])
        month = self._bcd_to_int(data[5])
        year = self._bcd_to_int(data[6]) + 2000
        
        return {
            "hour": hours, "minute": minutes, "second": seconds,
            "day": day, "month": month, "year": year
        }

    def write_time(self, hour, minute, second, day, month, year):
        """Thiết lập thời gian cho RTC."""
        data = [
            self._int_to_bcd(second),
            self._int_to_bcd(minute),
            self._int_to_bcd(hour),
            0x01, # Thứ trong tuần (tạm để 1)
            self._int_to_bcd(day),
            self._int_to_bcd(month),
            self._int_to_bcd(year - 2000)
        ]
        self.bus.write_i2c_block_data(self.address, 0x00, data)
        print("Đã cập nhật thời gian mới cho DS1307!")

# --- Chương trình chính ---
if __name__ == "__main__":
    rtc = DS1307()

    # Ví dụ: Cài đặt thời gian (Chỉ chạy 1 lần nếu cần chỉnh giờ)
    # rtc.write_time(hour=14, minute=30, second=0, day=13, month=1, year=2026)

    try:
        print("Đang đọc thời gian từ DS1307 (Nhấn Ctrl+C để dừng)...")
        while True:
            t = rtc.read_time()
            print(f"Thời gian: {t['hour']:02d}:{t['minute']:02d}:{t['second']:02d} | "
                  f"Ngày: {t['day']:02d}/{t['month']:02d}/{t['year']}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")
