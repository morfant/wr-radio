import RPi.GPIO as GPIO
import time
import sys

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("핀 상태 모니터링 (Ctrl+C로 종료)")

try:
    while True:
        # 같은 줄에 계속 업데이트
        sys.stdout.write(f"\rS1:{GPIO.input(17)} S2:{GPIO.input(27)} KEY:{GPIO.input(22)}")
        sys.stdout.flush()
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n프로그램 종료")
finally:
    GPIO.cleanup()
