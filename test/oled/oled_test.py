from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
import time
import math
from PIL import Image, ImageDraw


# I2C 설정
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)


def create_weather_icon(weather_type, size=32):
    icon = Image.new('1', (size, size), 0)
    draw = ImageDraw.Draw(icon)
    
    if weather_type == "Clear":
        # 태양: 중앙 원 + 8방향 광선
        center = size // 2
        radius = size // 4
        # 중앙 원
        draw.ellipse((center-radius, center-radius, 
                     center+radius, center+radius), fill=1)
        # 광선 (8방향)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = center + int((radius + 2) * math.cos(rad))
            y1 = center + int((radius + 2) * math.sin(rad))
            x2 = center + int((radius + 8) * math.cos(rad))
            y2 = center + int((radius + 8) * math.sin(rad))
            draw.line((x1, y1, x2, y2), fill=1, width=2)
    
    elif weather_type == "Clouds":
        # 구름: 여러 원을 겹쳐서 뭉게구름 형태
        y_base = size // 2 + 2
        # 아래쪽 큰 원들
        draw.ellipse((4, y_base, 14, y_base+10), fill=1)
        draw.ellipse((10, y_base-2, 22, y_base+8), fill=1)
        draw.ellipse((18, y_base, 28, y_base+10), fill=1)
        # 위쪽 작은 원들
        draw.ellipse((8, y_base-6, 16, y_base+2), fill=1)
        draw.ellipse((14, y_base-8, 24, y_base), fill=1)
    
    elif weather_type == "Rain":
        # 구름 (작게)
        y_cloud = 8
        draw.ellipse((6, y_cloud, 14, y_cloud+6), fill=1)
        draw.ellipse((12, y_cloud-2, 22, y_cloud+4), fill=1)
        draw.ellipse((18, y_cloud, 26, y_cloud+6), fill=1)
        # 빗방울 (명확한 사선)
        for x_offset in [8, 14, 20]:
            draw.line((x_offset, y_cloud+10, x_offset-2, y_cloud+16), fill=1, width=2)
            draw.line((x_offset, y_cloud+18, x_offset-2, y_cloud+24), fill=1, width=2)
    
    elif weather_type == "Drizzle":
        # 구름 + 작은 빗방울
        y_cloud = 8
        draw.ellipse((6, y_cloud, 14, y_cloud+6), fill=1)
        draw.ellipse((12, y_cloud-2, 22, y_cloud+4), fill=1)
        draw.ellipse((18, y_cloud, 26, y_cloud+6), fill=1)
        # 작은 점들
        for x_offset in [8, 14, 20]:
            for y_offset in [16, 22]:
                draw.ellipse((x_offset-1, y_cloud+y_offset-1, 
                            x_offset+1, y_cloud+y_offset+1), fill=1)
    
    elif weather_type == "Snow":
        # 구름
        y_cloud = 8
        draw.ellipse((6, y_cloud, 14, y_cloud+6), fill=1)
        draw.ellipse((12, y_cloud-2, 22, y_cloud+4), fill=1)
        draw.ellipse((18, y_cloud, 26, y_cloud+6), fill=1)
        # 눈송이 (별 모양)
        def draw_snowflake(cx, cy, r):
            # 6방향 선
            for angle in [0, 60, 120]:
                import math
                rad = math.radians(angle)
                x1 = cx + int(r * math.cos(rad))
                y1 = cy + int(r * math.sin(rad))
                x2 = cx - int(r * math.cos(rad))
                y2 = cy - int(r * math.sin(rad))
                draw.line((x1, y1, x2, y2), fill=1, width=1)
        
        draw_snowflake(10, y_cloud+18, 3)
        draw_snowflake(22, y_cloud+18, 3)
        draw_snowflake(16, y_cloud+25, 3)
    
    elif weather_type == "Thunderstorm":
        # 구름 (어둡게)
        y_cloud = 6
        draw.ellipse((4, y_cloud, 12, y_cloud+6), fill=1)
        draw.ellipse((10, y_cloud-2, 20, y_cloud+4), fill=1)
        draw.ellipse((16, y_cloud, 24, y_cloud+6), fill=1)
        draw.ellipse((22, y_cloud, 28, y_cloud+6), fill=1)
        # 번개 (지그재그)
        lightning = [(16, y_cloud+8), (14, y_cloud+14), 
                    (16, y_cloud+14), (12, y_cloud+22),
                    (14, y_cloud+22), (10, y_cloud+28)]
        draw.line(lightning, fill=1, width=2)
    
    elif weather_type == "Mist" or weather_type == "Fog":
        # 수평선들 (안개)
        for y in range(8, 28, 4):
            draw.line((4, y, 28, y), fill=1, width=2)
            if y + 2 < 28:
                draw.line((8, y+2, 24, y+2), fill=1, width=1)
    
    else:
        # 기본 (물음표)
        draw.text((8, 8), "?", fill=1)
    
    return icon


# 1. 여러 아이콘 순서대로 표시
weather_list = [
        "Clear", "Clouds", "Drizzle",
        "Snow", "Thunderstorm", "Mist", "Rain"]
for weather in weather_list:
    icon = create_weather_icon(weather, size=48)
    with canvas(device) as draw:
        draw.bitmap((48, 10), icon, fill="white")
        draw.text((48, 50), weather, fill="white")
    time.sleep(0.1)



with canvas(device) as draw:
    draw.text((10, 10), "Jeju, Georo", fill="white")
time.sleep(2)






device.clear()
