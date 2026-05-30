#!/usr/bin/env python3
"""실제 display_radio_info 레이아웃으로 모든 날씨 아이콘을 5초 간격으로 순환."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import time
import spidev
import RPi.GPIO as GPIO
from wr_radio import display
from wr_radio.state import AppState

PIN_CS  = 26
PIN_DC  = 13
PIN_RST = 6
PIN_BL  = 12

ICONS = [
    ("01", "Clear",      22),
    ("02", "Few clouds", 18),
    ("03", "Clouds",     15),
    ("04", "Overcast",   12),
    ("09", "Drizzle",     9),
    ("10", "Rain",        7),
    ("11", "Thunder",     6),
    ("13", "Snow",       -2),
    ("50", "Mist",       11),
]

STATION = {
    "name": "London Stave Hill",
    "location": "London, UK",
    "lat": 51.5,
    "lon": -0.04,
    "color": (255, 100, 100),
    "timezone": "Europe/London",
}

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_CS,  GPIO.OUT)
    GPIO.setup(PIN_DC,  GPIO.OUT)
    GPIO.setup(PIN_RST, GPIO.OUT)
    GPIO.setup(PIN_BL,  GPIO.OUT)
    GPIO.output(PIN_BL, GPIO.HIGH)

    state = AppState()
    state.spi = spidev.SpiDev()
    state.spi.open(0, 0)
    state.spi.max_speed_hz = 16_000_000
    state.spi.mode = 0
    state.radio_stations = [STATION]
    state.current_index = 0
    state.is_playing = True

    display.init_display(GPIO, {"CS": PIN_CS, "DC": PIN_DC, "RST": PIN_RST}, state, rotation=90)

    print("5초 간격으로 순환. Ctrl+C로 종료.")
    try:
        i = 0
        while True:
            code, label, temp = ICONS[i % len(ICONS)]
            print(f"[{i+1}/{len(ICONS)}] {code} {label} {temp}°C")
            display.display_radio_info(
                GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state,
                weather_data={"icon": code, "temp": temp},
                force_full=True,
            )
            i += 1
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        state.spi.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
