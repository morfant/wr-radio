import RPi.GPIO as GPIO
import time

# GPIO 핀 번호 설정
S1 = 17
S2 = 22
KEY = 23

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(S1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(S2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY, GPIO.IN, pull_up_down=GPIO.PUD_UP)

counter = 0
s1LastState = GPIO.input(S1)
keyLastState = GPIO.input(KEY)

print("로터리 엔코더 테스트 시작 (Ctrl+C로 종료)")

try:
    while True:
        # 로터리 엔코더 회전 감지
        s1State = GPIO.input(S1)
        s2State = GPIO.input(S2)
        
        if s1State != s1LastState:
            if s2State != s1State:
                counter += 1
                print(f"↑ 시계방향: {counter}")
            else:
                counter -= 1
                print(f"↓ 반시계방향: {counter}")
        
        s1LastState = s1State
        
        # 버튼 눌림 감지
        keyState = GPIO.input(KEY)
        if keyState == 0 and keyLastState == 1:  # 버튼 눌림 (HIGH → LOW)
            print(f"🔘 버튼 눌림! 현재 값: {counter}")
            time.sleep(0.2)  # 디바운스 (중복 입력 방지)
        
        keyLastState = keyState
        
        time.sleep(0.001)  # CPU 부하 감소

except KeyboardInterrupt:
    print("\n프로그램 종료")
finally:
    GPIO.cleanup()
