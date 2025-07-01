import RPi.GPIO as GPIO
import time
 
class Dong_co(object):
    def __init__(self,in1=17,in2=18,in3=27,in4=22,ena=12,enb=13):   # Khởi tạo các chân GPIO cho động cơ
    
        self.IN1 = in1
        self.IN2 = in2
        self.IN3 = in3
        self.IN4 = in4
        self.ENA = ena
        self.ENB = enb
        # Thiết lập GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.IN1,GPIO.OUT)
        GPIO.setup(self.IN2,GPIO.OUT)
        GPIO.setup(self.IN3,GPIO.OUT)
        GPIO.setup(self.IN4,GPIO.OUT)
        GPIO.setup(self.ENA,GPIO.OUT)
        GPIO.setup(self.ENB,GPIO.OUT)
 
        self.stop()
 
        self.PWMA = GPIO.PWM(self.ENA,500)
        self.PWMB = GPIO.PWM(self.ENB,500)
 
        self.PWMA.start(50)
        self.PWMB.start(50)
 
    def backward(self): # Di chuyển lùi
        GPIO.output(self.IN1,GPIO.HIGH) 
        GPIO.output(self.IN2,GPIO.LOW)  
        GPIO.output(self.IN3,GPIO.LOW)  
        GPIO.output(self.IN4,GPIO.HIGH)

    def stop(self): # Dừng xe
        GPIO.output(self.IN1,GPIO.LOW)
        GPIO.output(self.IN2,GPIO.LOW)
        GPIO.output(self.IN3,GPIO.LOW)
        GPIO.output(self.IN4,GPIO.LOW)
 
    def forward(self):  # Di chuyển tiến
        GPIO.output(self.IN1,GPIO.LOW)
        GPIO.output(self.IN2,GPIO.HIGH)
        GPIO.output(self.IN3,GPIO.HIGH)
        GPIO.output(self.IN4,GPIO.LOW)

    def right(self):    # Quay phải
        GPIO.output(self.IN1,GPIO.LOW)
        GPIO.output(self.IN2,GPIO.LOW)
        GPIO.output(self.IN3,GPIO.LOW)
        GPIO.output(self.IN4,GPIO.HIGH)

    def left(self):     # Quay trái
 
        GPIO.output(self.IN1,GPIO.HIGH)
        GPIO.output(self.IN2,GPIO.LOW)
        GPIO.output(self.IN3,GPIO.LOW)
        GPIO.output(self.IN4,GPIO.LOW)

    def setPWMA(self,value):    # Thiết lập tốc độ động cơ A
        self.PWMA.ChangeDutyCycle(value)

    def setPWMB(self,value):    # Thiết lập tốc độ động cơ B
        self.PWMB.ChangeDutyCycle(value)  

    def setMotor(self, left, right):    # Thiết lập tốc độ động cơ trái và phải
 
        if((right >= 0) and (right <= 100)):
            GPIO.output(self.IN1,GPIO.HIGH)
            GPIO.output(self.IN2,GPIO.LOW)
            self.PWMA.ChangeDutyCycle(right)
        elif((right < 0) and (right >= -100)):
            GPIO.output(self.IN1,GPIO.LOW)
            GPIO.output(self.IN2,GPIO.HIGH)
            self.PWMA.ChangeDutyCycle(0 - right)
        if((left >= 0) and (left <= 100)):
            GPIO.output(self.IN3,GPIO.HIGH)
            GPIO.output(self.IN4,GPIO.LOW)
            self.PWMB.ChangeDutyCycle(left)
        elif((left < 0) and (left >= -100)):
            GPIO.output(self.IN3,GPIO.LOW)
            GPIO.output(self.IN4,GPIO.HIGH)
            self.PWMB.ChangeDutyCycle(0 - left)
