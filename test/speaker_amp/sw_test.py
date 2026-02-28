import RPi.GPIO as GPIO
import time

AMP_STBY_PIN = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(AMP_STBY_PIN, GPIO.OUT, initial=GPIO.HIGH)

try:
    while True:
        print("HIGH (3.3V)")
        GPIO.output(AMP_STBY_PIN, GPIO.HIGH)
        time.sleep(2)
        
        print("LOW (0V)")
        GPIO.output(AMP_STBY_PIN, GPIO.LOW)
        time.sleep(2)
except KeyboardInterrupt:
    GPIO.cleanup(AMP_STBY_PIN)
    print("종료")
