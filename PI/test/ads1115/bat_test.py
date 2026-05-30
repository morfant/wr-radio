import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
chan = AnalogIn(ads, 0)  # P0 = 0

while True:
    raw_voltage = chan.voltage
    battery_voltage = raw_voltage * 2
    print(f"A0: {raw_voltage:.3f}V | 배터리: {battery_voltage:.3f}V")
    time.sleep(1)
