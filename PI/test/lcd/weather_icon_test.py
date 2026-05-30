#!/usr/bin/env python3
"""LCD에 모든 날씨 아이콘을 3×3 그리드로 표시하는 테스트."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import spidev
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
from wr_radio import display
from wr_radio.state import AppState

PIN_CS  = 26
PIN_DC  = 13
PIN_RST = 6
PIN_BL  = 12

ICONS = [
    ("01", "Clear"),
    ("02", "Few clouds"),
    ("03", "Clouds"),
    ("04", "Overcast"),
    ("09", "Drizzle"),
    ("10", "Rain"),
    ("11", "Thunder"),
    ("13", "Snow"),
    ("50", "Mist"),
]

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

    pins = {"CS": PIN_CS, "DC": PIN_DC, "RST": PIN_RST}
    display.init_display(GPIO, pins, state, rotation=90)

    img  = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except Exception:
        font = ImageFont.load_default()

    COLS, ROWS = 3, 3
    CELL_W = 240 // COLS   # 80
    CELL_H = 240 // ROWS   # 80

    for i, (code, label) in enumerate(ICONS):
        col = i % COLS
        row = i // COLS
        cx = col * CELL_W + CELL_W // 2
        cy = row * CELL_H + CELL_H // 2

        # 아이콘 (24×18 정도 크기, 중앙 위쪽)
        icon_x = cx - 12
        icon_y = cy - 18
        display.draw_weather_icon(draw, icon_x, icon_y, code)

        # 코드 + 이름
        draw.text((cx, cy + 8),  code,  fill=(180, 180, 180), font=font, anchor="mm")
        draw.text((cx, cy + 20), label, fill=(100, 100, 120), font=font, anchor="mm")

    # 격자선
    for c in range(1, COLS):
        draw.line([(c * CELL_W, 0), (c * CELL_W, 239)], fill=(30, 30, 30))
    for r in range(1, ROWS):
        draw.line([(0, r * CELL_H), (239, r * CELL_H)], fill=(30, 30, 30))

    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img)
    print("날씨 아이콘 표시 완료. Ctrl+C로 종료.")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        state.spi.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
