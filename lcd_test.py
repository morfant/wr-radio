import spidev
import RPi.GPIO as GPIO
import time
from PIL import Image, ImageDraw, ImageFont

# GPIO 핀 설정
CS_PIN = 26
DC_PIN = 19
RST_PIN = 13
BL_PIN = 6

# SPI 설정
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 8000000
spi.mode = 0

# GPIO 초기화
GPIO.setmode(GPIO.BCM)
GPIO.setup(CS_PIN, GPIO.OUT)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)

# PWM 객체 저장용
pwm_backlight = None

# ==================== 백라이트 제어 ====================

def backlight_on():
    """백라이트 켜기"""
    global pwm_backlight
    if pwm_backlight:
        pwm_backlight.stop()
        pwm_backlight = None
    GPIO.output(BL_PIN, GPIO.HIGH)

def backlight_off():
    """백라이트 끄기"""
    global pwm_backlight
    if pwm_backlight:
        pwm_backlight.stop()
        pwm_backlight = None
    GPIO.output(BL_PIN, GPIO.LOW)

def set_brightness(level):
    """PWM으로 밝기 조절 (0~100)"""
    global pwm_backlight
    if pwm_backlight:
        pwm_backlight.ChangeDutyCycle(level)
    else:
        pwm_backlight = GPIO.PWM(BL_PIN, 1000)
        pwm_backlight.start(level)

# ==================== LCD 저수준 제어 ====================

def reset():
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.01)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.12)

def write_cmd(cmd):
    GPIO.output(DC_PIN, GPIO.LOW)
    GPIO.output(CS_PIN, GPIO.LOW)
    spi.writebytes([cmd])
    GPIO.output(CS_PIN, GPIO.HIGH)

def write_data(data):
    GPIO.output(DC_PIN, GPIO.HIGH)
    GPIO.output(CS_PIN, GPIO.LOW)
    if isinstance(data, list):
        spi.writebytes(data)
    else:
        spi.writebytes([data])
    GPIO.output(CS_PIN, GPIO.HIGH)

def set_rotation(rotation):
    """
    화면 회전 설정
    rotation: 0, 90, 180, 270 (도)
    """
    write_cmd(0x36)  # MADCTL
    
    if rotation == 0:
        write_data(0x00)  # 0도 (기본)
    elif rotation == 90:
        write_data(0x60)  # 90도 (오른쪽/시계방향)
    elif rotation == 180:
        write_data(0xC0)  # 180도
    elif rotation == 270:
        write_data(0xA0)  # 270도 (왼쪽/반시계방향)
    else:
        write_data(0x00)  # 기본값

def init_display(rotation=0):
    """ST7789 초기화"""
    reset()
    write_cmd(0x01)
    time.sleep(0.15)
    write_cmd(0x11)
    time.sleep(0.12)
    write_cmd(0x3A)
    write_data(0x05)
    
    # 회전 설정
    set_rotation(rotation)
    
    write_cmd(0x21)
    write_cmd(0x13)
    write_cmd(0x29)
    time.sleep(0.01)

# ==================== 그래픽 함수 ====================

def rgb565(r, g, b):
    """RGB888을 RGB565로 변환"""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def set_window(x0, y0, x1, y1):
    """화면 영역 설정"""
    write_cmd(0x2A)
    write_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
    write_cmd(0x2B)
    write_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
    write_cmd(0x2C)

def fill_screen(r, g, b):
    """전체 화면을 한 색으로 채우기"""
    color = rgb565(r, g, b)
    set_window(0, 0, 239, 239)
    
    GPIO.output(DC_PIN, GPIO.HIGH)
    GPIO.output(CS_PIN, GPIO.LOW)
    color_bytes = [(color >> 8) & 0xFF, color & 0xFF]
    pixel_data = color_bytes * 240
    for _ in range(240):
        spi.writebytes(pixel_data)
    GPIO.output(CS_PIN, GPIO.HIGH)

def display_image(image):
    """PIL Image를 화면에 표시"""
    if image.size != (240, 240):
        image = image.resize((240, 240))
    
    image = image.convert('RGB')
    set_window(0, 0, 239, 239)
    
    pixels = []
    for y in range(240):
        for x in range(240):
            r, g, b = image.getpixel((x, y))
            color = rgb565(r, g, b)
            pixels.append((color >> 8) & 0xFF)
            pixels.append(color & 0xFF)
    
    GPIO.output(DC_PIN, GPIO.HIGH)
    GPIO.output(CS_PIN, GPIO.LOW)
    
    chunk_size = 4096
    for i in range(0, len(pixels), chunk_size):
        spi.writebytes(pixels[i:i+chunk_size])
    
    GPIO.output(CS_PIN, GPIO.HIGH)

# ==================== 텍스트 함수 ====================

def draw_text(text, x=10, y=100, font_size=32, text_color=(255, 255, 255), bg_color=(0, 0, 0)):
    """텍스트를 화면에 표시"""
    image = Image.new('RGB', (240, 240), bg_color)
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    draw.text((x, y), text, font=font, fill=text_color)
    display_image(image)

def draw_text_centered(text, font_size=32, text_color=(255, 255, 255), bg_color=(0, 0, 0)):
    """중앙 정렬 텍스트 표시"""
    image = Image.new('RGB', (240, 240), bg_color)
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (240 - text_width) // 2
    y = (240 - text_height) // 2
    
    draw.text((x, y), text, font=font, fill=text_color)
    display_image(image)

# ==================== 테스트 코드 ====================

try:
    print("디스플레이 초기화 (90도 회전)...")
    init_display(rotation=90)  # ← 오른쪽으로 90도 회전!
    backlight_on()
    
    # 회전 테스트
    print("회전 테스트")
    draw_text_centered("90 deg", font_size=48, 
                       text_color=(255, 255, 0), bg_color=(0, 0, 100))
    time.sleep(3)
    
    # 여러 방향 테스트
    print("0도")
    set_rotation(0)
    draw_text_centered("0 deg", font_size=48, 
                       text_color=(255, 0, 0), bg_color=(0, 0, 0))
    time.sleep(2)
    
    print("90도")
    set_rotation(90)
    draw_text_centered("90 deg", font_size=48, 
                       text_color=(0, 255, 0), bg_color=(0, 0, 0))
    time.sleep(2)
    
    print("180도")
    set_rotation(180)
    draw_text_centered("180 deg", font_size=48, 
                       text_color=(0, 0, 255), bg_color=(0, 0, 0))
    time.sleep(2)
    
    print("270도")
    set_rotation(270)
    draw_text_centered("270 deg", font_size=48, 
                       text_color=(255, 255, 0), bg_color=(0, 0, 0))
    time.sleep(2)
    
    # 다시 90도로 설정
    print("90도로 고정")
    set_rotation(90)
    draw_text_centered("Fixed!", font_size=48, 
                       text_color=(0, 255, 255), bg_color=(0, 0, 0))
    
    print("완료!")

except KeyboardInterrupt:
    print("\n종료")
finally:
    if pwm_backlight:
        pwm_backlight.stop()
    GPIO.cleanup()
    spi.close()
