import utime
import random
from machine import Pin
from DIYables_Pico_Keypad import Keypad
from st7735 import TFT, sysfont, TFTColor

NUM_ROWS = 4
NUM_COLS = 4
ROW_PINS = [9, 8, 7, 6]
COLUMN_PINS = [5, 4, 3, 2]
KEYMAP = ['1', '2', '3', '+','4', '5', '6', '-','7', '8', '9', 'x','AC', '0', '=', ':']
keypad = Keypad(KEYMAP, ROW_PINS, COLUMN_PINS, NUM_ROWS, NUM_COLS)
keypad.set_debounce_time(200)

def run_pong_game(tft_obj, button_select_pin, bg_color, text_color):
    RUN_GAME1 = True
    SCREEN_WIDTH = tft_obj.size()[0]
    SCREEN_HEIGHT = tft_obj.size()[1]
        
    def display_centered_text(tft_obj, text, y_pos, color, aSize=1):
        """Hiển thị văn bản được căn giữa trên màn hình."""
        text_len = len(text) * sysfont.sysfont["Width"] * aSize
        x_pos = (SCREEN_WIDTH - text_len) // 2
        if x_pos < 0:  x_pos = 0
        tft_obj.text((x_pos, y_pos), text, color, sysfont.sysfont, aSize=aSize)

    def show_start_screen():
        tft_obj.fill(bg_color)
        display_centered_text(tft_obj, "PONG", 20, TFT.YELLOW, aSize=3)
        display_centered_text(tft_obj, "4: Trai | 6: Phai", 60, text_color, aSize=1)
        display_centered_text(tft_obj, "Nhan 'A'", 80, text_color, aSize=2)
        display_centered_text(tft_obj, "De Bat Dau", 100, text_color, aSize=2)
        
        start_screen_active = True
        while start_screen_active:
            key = keypad.get_key()
            if key == '+':
                return True
            if button_select_pin.value() == 0:
                while button_select_pin.value() == 0:
                    utime.sleep_ms(10)
                return False
            utime.sleep_ms(10)

    def show_game_over_screen(winner):
        tft_obj.fill(bg_color)
        display_centered_text(tft_obj, "GAME OVER", 20, TFT.RED, aSize=2)
        win_text = "Ban Thang!" if winner == "Player" else "May Thang!"
        win_color = TFT.GREEN if winner == "Player" else TFT.ORANGE
        display_centered_text(tft_obj, win_text, 50, win_color, aSize=2)
        display_centered_text(tft_obj, "Nhan 'A' de choi lai", 90, text_color, aSize=1)
        utime.sleep(0.5)
        
        game_over_active = True
        while game_over_active:
            key = keypad.get_key()
            if key == '=':
                return True
            if button_select_pin.value() == 0:
                while button_select_pin.value() == 0:
                    utime.sleep_ms(10)
                return False
            utime.sleep_ms(10)

    def play_game():
        WINNING_SCORE = 5
        player_score = 0
        computer_score = 0

        paddle_width = 30
        paddle_height = 5
        paddle_speed = 10
        paddle_x = SCREEN_WIDTH // 2 - paddle_width // 2
        PLAYER_PADDLE_Y = SCREEN_HEIGHT - paddle_height

        computer_paddle_width = 30
        computer_paddle_height = 5
        computer_paddle_speed = 2.5
        computer_paddle_x = SCREEN_WIDTH // 2 - computer_paddle_width // 2
        COMPUTER_PADDLE_Y = 0

        ball_radius = 4
        ball_x = SCREEN_WIDTH // 2
        ball_y = SCREEN_HEIGHT // 2
        ball_speed_x = 2
        ball_speed_y = 2
        ball_direction_x = random.choice([-1, 1])
        ball_direction_y = random.choice([-1, 1])

        prev_paddle_x = paddle_x
        prev_computer_paddle_x = computer_paddle_x
        prev_ball_x, prev_ball_y = ball_x, ball_y

        tft_obj.fill(bg_color)
        
        score_y = 10
        score_y_player = SCREEN_HEIGHT - 20
        tft_obj.text((5, score_y), str(computer_score), TFT.WHITE, sysfont.sysfont, aSize=2)
        tft_obj.text((5, score_y_player), str(player_score), TFT.WHITE, sysfont.sysfont, aSize=2)

        game_playing = True
        while game_playing:
            # Kiểm tra nút thoát ngay lập tức
            if button_select_pin.value() == 0:
                tft_obj.fill(bg_color)
                while button_select_pin.value() == 0:
                    utime.sleep(0.05)
                return "Thoat"

            key = keypad.get_key()
            
            if key == '4':
                paddle_x -= paddle_speed
            elif key == '6':
                paddle_x += paddle_speed

            paddle_x = max(0, min(SCREEN_WIDTH - paddle_width, paddle_x))

            if ball_x > computer_paddle_x + computer_paddle_width / 2:
                computer_paddle_x += min(computer_paddle_speed, ball_x - (computer_paddle_x + computer_paddle_width / 2))
            elif ball_x < computer_paddle_x + computer_paddle_width / 2:
                computer_paddle_x -= min(computer_paddle_speed, (computer_paddle_x + computer_paddle_width / 2) - ball_x)

            ball_x += ball_speed_x * ball_direction_x
            ball_y += ball_speed_y * ball_direction_y

            if ball_x <= ball_radius or ball_x >= SCREEN_WIDTH - ball_radius:
                ball_direction_x *= -1

            if (PLAYER_PADDLE_Y - 2 <= ball_y + ball_radius <= PLAYER_PADDLE_Y + 2 and
                paddle_x <= ball_x <= paddle_x + paddle_width):
                ball_direction_y = -1

            if (COMPUTER_PADDLE_Y + computer_paddle_height - 2 <= ball_y - ball_radius <= COMPUTER_PADDLE_Y + computer_paddle_height + 2 and
                computer_paddle_x <= ball_x <= computer_paddle_x + computer_paddle_width):
                ball_direction_y = 1

            if ball_y > SCREEN_HEIGHT:
                computer_score += 1
                tft_obj.fillrect((5, score_y), (40, 20), bg_color)
                tft_obj.text((5, score_y), str(computer_score), TFT.WHITE, sysfont.sysfont, aSize=2)
                if computer_score >= WINNING_SCORE:
                    return "Computer"
                ball_x, ball_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                ball_direction_y = -1
                utime.sleep(0.5)

            if ball_y < 0:
                player_score += 1
                tft_obj.fillrect((5, score_y_player), (40, 20), bg_color)
                tft_obj.text((5, score_y_player), str(player_score), TFT.WHITE, sysfont.sysfont, aSize=2)
                if player_score >= WINNING_SCORE:
                    return "Player"
                ball_x, ball_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                ball_direction_y = 1
                utime.sleep(0.5)
            
            tft_obj.fillrect((int(prev_paddle_x), PLAYER_PADDLE_Y), (paddle_width, paddle_height), bg_color)
            tft_obj.fillrect((int(prev_computer_paddle_x), COMPUTER_PADDLE_Y), (computer_paddle_width, computer_paddle_height), bg_color)
            tft_obj.fillcircle((int(prev_ball_x), int(prev_ball_y)), ball_radius, bg_color)
            
            prev_paddle_x = paddle_x
            prev_computer_paddle_x = computer_paddle_x
            prev_ball_x, prev_ball_y = ball_x, ball_y

            tft_obj.fillrect((int(paddle_x), PLAYER_PADDLE_Y), (paddle_width, paddle_height), TFT.GREEN)
            tft_obj.fillrect((int(computer_paddle_x), COMPUTER_PADDLE_Y), (computer_paddle_width, computer_paddle_height), TFT.CYAN)
            tft_obj.fillcircle((int(ball_x), int(ball_y)), ball_radius, TFT.RED)

            utime.sleep_ms(15)
            
    running = True
    while running:
        start_game = show_start_screen()
        if not start_game:
            running = False
            continue
            
        winner = play_game()

        if winner == "Thoat":
            running = False
            continue
        
        play_again = show_game_over_screen(winner)
        if not play_again:
            running = False
            continue

    tft_obj.fill(bg_color)
    tft_obj.text((10, 10), "Dang thoat...", text_color, sysfont.sysfont, 1)
    utime.sleep(1)