import board
import time
from mfrc522 import MFRC522
# thiết lập kết nối
sck = board.GP2
mosi = board.GP3
miso = board.GP4
cs = board.GP5
rst = board.GP28
###
rfid = MFRC522(sck, mosi, miso, cs, rst)
prev_data = None
while True:
    (status, tag_type) = rfid.request(rfid.REQALL)

    if status == rfid.OK:
        print("Đã phát hiện thẻ, loại thẻ:", tag_type)

        (status, raw_uid) = rfid.anticoll()

        if status == rfid.OK:
            rfid_data = "{:02x}{:02x}{:02x}{:02x}".format(*raw_uid)
            if rfid_data != prev_data:
                prev_data = rfid_data
                print("UID thẻ :", rfid_data)
    time.sleep(0.2)
