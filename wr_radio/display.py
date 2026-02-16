import math
import time
from PIL import Image, ImageDraw, ImageFont

# LCD 핀은 main에서 GPIO setup 후 사용
# SPI 객체는 state.spi 사용

# LCD 컨트롤 커맨드들(현재 네 코드 그대로)
def reset(GPIO, RST_PIN):
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.01)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.12)


def write_cmd(GPIO, DC_PIN, CS_PIN, spi, cmd: int):
    GPIO.output(DC_PIN, GPIO.LOW)
    GPIO.output(CS_PIN, GPIO.LOW)
    spi.writebytes([cmd])
    GPIO.output(CS_PIN, GPIO.HIGH)


def write_data(GPIO, DC_PIN, CS_PIN, spi, data):
    GPIO.output(DC_PIN, GPIO.HIGH)
    GPIO.output(CS_PIN, GPIO.LOW)
    if isinstance(data, list):
        spi.writebytes(data)
    else:
        spi.writebytes([data])
    GPIO.output(CS_PIN, GPIO.HIGH)


def set_rotation(GPIO, DC_PIN, CS_PIN, spi, rotation=90):
    write_cmd(GPIO, DC_PIN, CS_PIN, spi, 0x36)
    if rotation == 0:
        write_data(GPIO, DC_PIN, CS_PIN, spi, 0x00)
    elif rotation == 90:
        write_data(GPIO, DC_PIN, CS_PIN, spi, 0x60)
    elif rotation == 180:
        write_data(GPIO, DC_PIN, CS_PIN, spi, 0xC0)
    elif rotation == 270:
        write_data(GPIO, DC_PIN, CS_PIN, spi, 0xA0)
    else:
        write_data(GPIO, DC_PIN, CS_PIN, spi, 0x00)


def init_display(GPIO, pins, state, rotation=90):
    reset(GPIO, pins["RST"])
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x01)
    time.sleep(0.15)
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x11)
    time.sleep(0.12)
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x3A)
    write_data(GPIO, pins["DC"], pins["CS"], state.spi, 0x05)
    set_rotation(GPIO, pins["DC"], pins["CS"], state.spi, rotation)
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x21)
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x13)
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x29)
    time.sleep(0.01)


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def set_window(GPIO, pins, state, x0, y0, x1, y1):
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x2A)
    write_data(GPIO, pins["DC"], pins["CS"], state.spi, [x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x2B)
    write_data(GPIO, pins["DC"], pins["CS"], state.spi, [y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
    write_cmd(GPIO, pins["DC"], pins["CS"], state.spi, 0x2C)


def display_image(GPIO, pins, state, image: Image.Image):
    if image.size != (240, 240):
        image = image.resize((240, 240))
    image = image.convert("RGB")
    set_window(GPIO, pins, state, 0, 0, 239, 239)

    pixels = []
    for y in range(240):
        for x in range(240):
            r, g, b = image.getpixel((x, y))
            c = rgb565(r, g, b)
            pixels.append((c >> 8) & 0xFF)
            pixels.append(c & 0xFF)

    GPIO.output(pins["DC"], GPIO.HIGH)
    GPIO.output(pins["CS"], GPIO.LOW)

    chunk = 4096
    for i in range(0, len(pixels), chunk):
        state.spi.writebytes(pixels[i:i + chunk])

    GPIO.output(pins["CS"], GPIO.HIGH)


def display_image_region(GPIO, pins, state, image: Image.Image, x0, y0, x1, y1):
    if image.size != (240, 240):
        image = image.resize((240, 240))
    image = image.convert("RGB")
    set_window(GPIO, pins, state, x0, y0, x1, y1)

    pixels = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            r, g, b = image.getpixel((x, y))
            c = rgb565(r, g, b)
            pixels.append((c >> 8) & 0xFF)
            pixels.append(c & 0xFF)

    GPIO.output(pins["DC"], GPIO.HIGH)
    GPIO.output(pins["CS"], GPIO.LOW)

    chunk = 4096
    for i in range(0, len(pixels), chunk):
        state.spi.writebytes(pixels[i:i + chunk])

    GPIO.output(pins["CS"], GPIO.HIGH)


def draw_weather_icon(draw: ImageDraw.ImageDraw, x: int, y: int, icon_code: str):
    if icon_code == "01":
        draw.ellipse([x, y, x + 14, y + 14], fill=(255, 200, 0))
        cx, cy = x + 7, y + 7
        rays = [
            (cx, y - 3, cx, y),
            (cx, y + 14, cx, y + 17),
            (x - 3, cy, x, cy),
            (x + 14, cy, x + 17, cy),
            (x - 2, y - 2, x + 1, y + 1),
            (x + 13, y - 2, x + 16, y + 1),
            (x - 2, y + 13, x + 1, y + 16),
            (x + 13, y + 13, x + 16, y + 16),
        ]
        for ray in rays:
            draw.line(ray, fill=(255, 200, 0), width=1)

    elif icon_code == "02":
        draw.ellipse([x, y, x + 10, y + 10], fill=(255, 200, 0))
        draw.ellipse([x + 8, y + 6, x + 20, y + 16], fill=(180, 180, 180))
        draw.ellipse([x + 12, y + 4, x + 24, y + 14], fill=(200, 200, 200))

    elif icon_code in ["03", "04"]:
        draw.ellipse([x, y + 4, x + 12, y + 14], fill=(160, 160, 160))
        draw.ellipse([x + 6, y, x + 18, y + 10], fill=(180, 180, 180))
        draw.ellipse([x + 10, y + 4, x + 22, y + 14], fill=(200, 200, 200))

    elif icon_code in ["09", "10"]:
        draw.ellipse([x, y, x + 12, y + 8], fill=(120, 120, 120))
        draw.ellipse([x + 6, y - 2, x + 18, y + 6], fill=(140, 140, 140))
        for i in range(4):
            xp = x + 2 + i * 4
            draw.line([xp, y + 10, xp - 2, y + 16], fill=(100, 150, 255), width=1)

    elif icon_code == "11":
        draw.ellipse([x, y, x + 12, y + 8], fill=(80, 80, 80))
        draw.ellipse([x + 6, y - 2, x + 18, y + 6], fill=(100, 100, 100))
        draw.line([x + 10, y + 8, x + 8, y + 12], fill=(255, 255, 0), width=2)
        draw.line([x + 8, y + 12, x + 10, y + 16], fill=(255, 255, 0), width=2)

    elif icon_code == "13":
        draw.ellipse([x, y, x + 12, y + 8], fill=(180, 180, 180))
        draw.ellipse([x + 6, y - 2, x + 18, y + 6], fill=(200, 200, 200))
        for i in range(3):
            xp = x + 4 + i * 4
            yp = y + 11 + i * 2
            draw.line([xp - 2, yp, xp + 2, yp], fill=(255, 255, 255), width=1)
            draw.line([xp, yp - 2, xp, yp + 2], fill=(255, 255, 255), width=1)

    elif icon_code == "50":
        for i in range(5):
            yp = y + i * 3
            draw.line([x, yp, x + 18, yp], fill=(150, 150, 150), width=1)


def draw_sine_wave_animation(draw: ImageDraw.ImageDraw, frame: int):
    center_y = 145
    amplitude = 12
    wavelength = 40
    num_points = 200

    pts = []
    for i in range(num_points):
        x = i + 20
        phase = (i + frame * 3) * 2 * math.pi / wavelength
        y = center_y + amplitude * math.sin(phase)
        pts.append((x, y))

    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(80, 150, 200), width=2)


def display_mode_indicator(GPIO, pins, state, mode: str, value: int):
    image = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font_small = ImageFont.load_default()

    if mode == "volume":
        text = f"VOL {value}%"
        color = (100, 200, 255)
    elif mode == "brightness":
        text = f"BRT {value}%"
        color = (255, 200, 100)
    else:
        return

    bbox = draw.textbbox((0, 0), text, font=font_small)
    text_width = bbox[2] - bbox[0]
    x = 240 - text_width - 10
    draw.text((x, 8), text, font=font_small, fill=color)

    display_image_region(GPIO, pins, state, image, 160, 0, 239, 25)


def display_radio_info(GPIO, pins, state, weather_data=None, force_full=False):
    """
    weather_data: {'icon': '01', 'temp': 15} or None
    """
    station = state.radio_stations[state.current_index]
    station_changed = (state.current_index != state.last_displayed_index)
    playing_changed = (state.is_playing != state.last_displayed_playing)

    image = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    try:
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    if force_full or station_changed:
        station_name = station["name"]

        bbox = draw.textbbox((0, 0), station_name, font=font_small)
        tw = bbox[2] - bbox[0]

        if tw > 230:
            bbox = draw.textbbox((0, 0), station_name, font=font_tiny)
            tw = bbox[2] - bbox[0]
            if tw > 230:
                try:
                    font_mini = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                except Exception:
                    font_mini = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), station_name, font=font_mini)
                tw = bbox[2] - bbox[0]
                x = max(5, (240 - tw) // 2)
                draw.text((x, 32), station_name, font=font_mini, fill=(220, 220, 220))
                location_y = 50
            else:
                x = max(5, (240 - tw) // 2)
                draw.text((x, 30), station_name, font=font_tiny, fill=(220, 220, 220))
                location_y = 50
        else:
            x = (240 - tw) // 2
            draw.text((x, 28), station_name, font=font_small, fill=(220, 220, 220))
            location_y = 50

        bbox = draw.textbbox((0, 0), station["location"], font=font_tiny)
        tw = bbox[2] - bbox[0]
        x = (240 - tw) // 2
        draw.text((x, location_y + 5), station["location"], font=font_tiny, fill=(120, 120, 120))

        if weather_data:
            icon_x = 90
            icon_y = location_y + 25
            draw_weather_icon(draw, icon_x, icon_y, str(weather_data.get("icon", "")))
            temp_text = f"{int(weather_data.get('temp', 0))}°C"
            draw.text((icon_x + 28, location_y + 27), temp_text, font=font_small, fill=(100, 200, 255))

        display_image_region(GPIO, pins, state, image, 0, 0, 239, 110)

        station_num = f"{state.current_index + 1} / {len(state.radio_stations)}"
        bbox = draw.textbbox((0, 0), station_num, font=font_medium)
        tw = bbox[2] - bbox[0]
        x = (240 - tw) // 2
        draw.text((x, 200), station_num, font=font_medium, fill=(120, 120, 120))
        display_image_region(GPIO, pins, state, image, 0, 195, 239, 239)

        state.last_displayed_index = state.current_index

    if force_full or station_changed or playing_changed:
        draw_sine_wave_animation(draw, state.animation_frame)
        state.animation_frame = (state.animation_frame + 1) % 100
        display_image_region(GPIO, pins, state, image, 0, 125, 239, 165)
        state.last_displayed_playing = state.is_playing
