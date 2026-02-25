import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
bat = AnalogIn(ads, 0)   # A0: 배터리
usb = AnalogIn(ads, 1)   # A1: USB

while True:
    bat_v = bat.voltage * 2        # 1/2 분압 보정
    usb_v = usb.voltage * 3        # 1/3 분압 보정
    charging = usb_v > 4.5
    print(f"BAT: {bat_v:.3f}V | USB: {usb_v:.3f}V | {'충전중' if charging else '배터리'}")
    time.sleep(1)
