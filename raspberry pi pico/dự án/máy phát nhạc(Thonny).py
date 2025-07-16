from dfplayermini import DFPlayerMini
import time
player1 = DFPlayerMini(1, 4, 5)
player1.select_source('sdcard')
player1.set_volume(30)	# Đặt âm lượng (0-30)
file_to_play = 2 
player1.play(file_to_play)
