import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("핀 상태 모니터링 (Ctrl+C로 종료)")
try:
    while True:
        print(f"S1:{GPIO.input(17)} S2:{GPIO.input(22)} KEY:{GPIO.input(23)}")
        time.sleep(0.2)
except KeyboardInterrupt:
    GPIO.cleanup()
