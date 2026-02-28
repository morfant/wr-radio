import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

last = None
try:
    while True:
        val = GPIO.input(23)
        if val != last:
            print(f"{time.strftime('%H:%M:%S')} GPIO23 = {val}")
            last = val
        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()
