import math
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pytz

# LCD 핀은 main에서 GPIO setup 후 사용
# SPI 객체는 state.spi 사용

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

    elif icon_code == "03":
        draw.ellipse([x, y + 4, x + 12, y + 14], fill=(160, 160, 160))
        draw.ellipse([x + 6, y, x + 18, y + 10], fill=(180, 180, 180))
        draw.ellipse([x + 10, y + 4, x + 22, y + 14], fill=(200, 200, 200))

    elif icon_code in ["03", "04"]:
        draw.ellipse([x, y + 4, x + 12, y + 14], fill=(160, 160, 160))
        draw.ellipse([x + 6, y, x + 18, y + 10], fill=(180, 180, 180))
        draw.ellipse([x + 10, y + 4, x + 22, y + 14], fill=(200, 200, 200))

    elif icon_code == "09":
        draw.ellipse([x, y, x + 12, y + 8], fill=(120, 120, 120))
        draw.ellipse([x + 6, y - 2, x + 18, y + 6], fill=(140, 140, 140))
        # 점선 2줄 (이슬비)
        # 흩어진 점들 (이슬비)
        for dx, dy in [(4, 11), (10, 10), (15, 12)]:
            draw.ellipse([x+dx-1, y+dy-1, x+dx+1, y+dy+1], fill=(100, 150, 255))

    elif icon_code == "10":
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
        # 안개: 구름보다 작은 원 5개가 살짝 겹치며 가로로 나열
        for dx, dy in [(2, 5), (6, 2), (10, 7), (14, 3), (18, 6), (22, 2),
                       (4, 11), (12, 13), (20, 10), (8, 14)]:
            draw.ellipse([x+dx-1, y+dy-1, x+dx+1, y+dy+1], fill=(100, 150, 255))


def draw_battery_icon(draw: ImageDraw.ImageDraw, x: int, y: int, percent: int, charging: bool = False):
    if charging:
        outline_color = (100, 220, 100)
    elif percent <= 15:
        outline_color = (255, 50, 50)
    elif percent >= 80:
        outline_color = (100, 200, 100)
    else:
        outline_color = (100, 100, 100)
    draw.rectangle([x, y + 2, x + 20, y + 12], outline=outline_color)
    draw.rectangle([x + 20, y + 5, x + 22, y + 9], fill=outline_color)

    fill_width = max(0, int(18 * percent / 100))
    if fill_width > 0:
        if charging:
            fill_color = (100, 220, 100)
        elif percent <= 15:
            fill_color = (255, 50, 50)
        elif percent <= 30:
            fill_color = (255, 180, 50)
        elif percent >= 80:
            fill_color = (100, 200, 100)
        else:
            fill_color = (200, 200, 200)
        draw.rectangle([x + 1, y + 3, x + fill_width, y + 11], fill=fill_color)

    if charging:
        # lightning bolt (배터리 외곽선 안쪽 y+3~y+11에 맞춤)
        bolt = [(x+10, y+3), (x+7, y+8), (x+10, y+8), (x+8, y+11), (x+13, y+7), (x+10, y+7), (x+12, y+3)]
        draw.polygon(bolt, fill=(255, 220, 50))


def draw_bt_indicator(draw: ImageDraw.ImageDraw, connected: bool):
    """배터리 아이콘 우측에 BT 아이콘. 연결 시에만 표시."""
    if not connected:
        return
    x, y = 36, 4
    color = (100, 160, 255)
    # 원 (지름 14px, 배터리 높이와 맞춤)
    draw.ellipse([x, y, x + 13, y + 13], outline=color, width=1)
    # 원 안에 B
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
    except Exception:
        font = ImageFont.load_default()
    draw.text((x + 7, y + 7), "B", font=font, fill=color, anchor="mm")


def draw_bt_indicator(draw: ImageDraw.ImageDraw, connected: bool):
    """배터리 아이콘 우측에 BT 아이콘. 연결 시에만 표시."""
    if not connected:
        return
    x, y = 36, 4
    color = (100, 160, 255)
    # 원 + B
    draw.ellipse([x, y, x + 13, y + 13], outline=color, width=1)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
    except Exception:
        font = ImageFont.load_default()
    draw.text((x + 7, y + 7), "B", font=font, fill=color, anchor="mm")


def draw_battery_status(draw: ImageDraw.ImageDraw, percent: int, blink_on: bool = True, charging: bool = False):
    if percent <= 15 and not blink_on and not charging:
        return
    draw_battery_icon(draw, 4, 4, percent, charging=charging)


def draw_sine_wave_animation(draw: ImageDraw.ImageDraw, frame: int, volume: int = 100):
    center_y = 145
    amplitude = max(2, int(volume * 12 / 100))
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


def draw_loading_indicator(draw: ImageDraw.ImageDraw, frame: int):
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()

    dots = "." * ((frame // 5) % 4)
    text = f"Loading{dots}   "

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (240 - tw) // 2
    draw.text((x, 140), text, font=font, fill=(120, 120, 120))


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
    x = max(5, 240 - text_width - 8)
    draw.text((x, 8), text, font=font_small, fill=color)

    display_image_region(GPIO, pins, state, image, 0, 0, 239, 25)


def display_battery_only(GPIO, pins, state):
    if state.battery_monitor is None:
        return
    voltage, percent = state.battery_monitor.get_status()
    blink_on = state.battery_monitor.is_blink_on()

    charging = state.battery_monitor.is_charging
    last_charging = getattr(state, '_last_displayed_charging', None)
    if (not state.battery_monitor.is_low
        and percent == state.last_battery_percent
        and charging == last_charging):
        return

    image = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_battery_status(draw, percent, blink_on, charging=state.battery_monitor.is_charging)
    display_image_region(GPIO, pins, state, image, 0, 0, 35, 18)

    state.last_battery_percent = percent
    state._last_displayed_charging = charging


def _draw_button_hint(draw: ImageDraw.ImageDraw):
    """normal 모드 하단 상시 힌트 — press: 점, hold: 선"""
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except Exception:
        font = ImageFont.load_default()

    color = (110, 110, 130)

    # press: 점 + 텍스트
    draw.ellipse([50, 224, 56, 230], fill=color)
    draw.text((62, 227), "Vol", fill=color, font=font, anchor="lm")

    # hold: 선 + 텍스트
    draw.line([(130, 227), (148, 227)], fill=color, width=2)
    draw.text((154, 227), "System", fill=color, font=font, anchor="lm")


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
                location_y = 47
            else:
                x = max(5, (240 - tw) // 2)
                draw.text((x, 30), station_name, font=font_tiny, fill=(220, 220, 220))
                location_y = 47
        else:
            x = (240 - tw) // 2
            draw.text((x, 28), station_name, font=font_small, fill=(220, 220, 220))
            location_y = 47

        bbox = draw.textbbox((0, 0), station["location"], font=font_tiny)
        tw = bbox[2] - bbox[0]
        x = (240 - tw) // 2
        draw.text((x, location_y + 2), station["location"], font=font_tiny, fill=(120, 120, 120))

        # 현지 시간 표시
        if "timezone" in station:
            try:
                tz = pytz.timezone(station["timezone"])
                local_time = datetime.now(tz)
                utc_offset = local_time.strftime("%z")
                utc_offset_str = f"UTC{utc_offset[:3]}:{utc_offset[3:]}"
                time_str = f"{local_time.strftime('%H:%M')} ({utc_offset_str})"

                bbox = draw.textbbox((0, 0), time_str, font=font_tiny)
                tw = bbox[2] - bbox[0]
                x = (240 - tw) // 2
                draw.text((x, location_y + 21), time_str, font=font_tiny, fill=(100, 200, 255))
            except Exception as e:
                print(f"⚠️  타임존 처리 실패: {e}")

        # 날씨 아이콘
        if weather_data:
            icon_x = 86
            icon_y = location_y + 43
            draw_weather_icon(draw, icon_x, icon_y, str(weather_data.get("icon", "")))
            temp_text = f"{int(weather_data.get('temp', 0))}°C"
            draw.text((icon_x + 30, location_y + 42), temp_text, font=font_small, fill=(100, 200, 255))

        # 배터리 + BT 상태 (상단)
        if state.battery_monitor is not None:
            voltage, percent = state.battery_monitor.get_status()
            draw_battery_status(draw, percent, state.battery_monitor.is_blink_on(), charging=state.battery_monitor.is_charging)
            state.last_battery_percent = percent

        bt_connected = getattr(state, "output_mode", "speaker") == "bluetooth"
        draw_bt_indicator(draw, bt_connected)

        display_image_region(GPIO, pins, state, image, 0, 0, 239, 115)

        # station 번호 + 힌트 (y=168~239)
        station_num = f"{state.current_index + 1} / {len(state.radio_stations)}"
        bbox = draw.textbbox((0, 0), station_num, font=font_medium)
        tw = bbox[2] - bbox[0]
        x = (240 - tw) // 2
        draw.text((x, 178), station_num, font=font_medium, fill=(120, 120, 120))

        _draw_button_hint(draw)

        display_image_region(GPIO, pins, state, image, 0, 168, 239, 239)

        state.last_displayed_index = state.current_index

    if force_full or station_changed or playing_changed:
        draw_sine_wave_animation(draw, state.animation_frame, state.current_volume)
        state.animation_frame = (state.animation_frame + 1) % 100
        display_image_region(GPIO, pins, state, image, 0, 125, 239, 165)
        state.last_displayed_playing = state.is_playing


def display_time_only(GPIO, pins, state):
    """시간 텍스트 영역만 갱신 (y=68 고정 strip). 분 단위 호출용."""
    station = state.radio_stations[state.current_index]
    if "timezone" not in station:
        return

    try:
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font_tiny = ImageFont.load_default()

    try:
        tz = pytz.timezone(station["timezone"])
        local_time = datetime.now(tz)
        utc_offset = local_time.strftime("%z")
        utc_offset_str = f"UTC{utc_offset[:3]}:{utc_offset[3:]}"
        time_str = f"{local_time.strftime('%H:%M')} ({utc_offset_str})"
    except Exception:
        return

    TIME_Y = 68
    image = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), time_str, font=font_tiny)
    tw = bbox[2] - bbox[0]
    x = (240 - tw) // 2
    draw.text((x, TIME_Y), time_str, font=font_tiny, fill=(100, 200, 255))
    display_image_region(GPIO, pins, state, image, 0, TIME_Y, 239, TIME_Y + 18)


def _prov_fonts():
    try:
        bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        bold = ImageFont.load_default()
    try:
        reg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        reg = ImageFont.load_default()
    return bold, reg


def display_provisioning_screen(GPIO, pins, state,
                                 ap_ssid="WR-Radio Setup", ap_url="10.42.0.1"):
    font_bold, font_reg = _prov_fonts()
    img  = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.text((120, 28),  "WiFi Setup",      font=font_bold, fill=(255, 255, 255), anchor="mm")
    draw.line([(20, 50), (220, 50)],          fill=(40, 40, 60), width=1)
    draw.text((120, 85),  f"Connect to:",    font=font_reg,  fill=(140, 140, 160), anchor="mm")
    draw.text((120, 110), f"'{ap_ssid}'",    font=font_reg,  fill=(255, 220, 80),  anchor="mm")
    draw.text((120, 150), "then open:",      font=font_reg,  fill=(140, 140, 160), anchor="mm")
    draw.text((120, 178), ap_url,            font=font_bold, fill=(100, 200, 255), anchor="mm")
    draw.text((120, 208), "in browser",      font=font_reg,  fill=(140, 140, 160), anchor="mm")

    display_image(GPIO, pins, state, img)


def display_provisioning_connecting(GPIO, pins, state, ssid: str):
    font_bold, font_reg = _prov_fonts()
    img  = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.text((120, 90),  "Connecting...", font=font_bold, fill=(255, 220, 80),  anchor="mm")
    draw.text((120, 130), ssid[:28],      font=font_reg,  fill=(200, 200, 200), anchor="mm")

    display_image(GPIO, pins, state, img)


def display_provisioning_success(GPIO, pins, state):
    font_bold, _ = _prov_fonts()
    img  = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((120, 110), "Connected!", font=font_bold, fill=(100, 220, 100), anchor="mm")
    display_image(GPIO, pins, state, img)


def display_provisioning_failed(GPIO, pins, state):
    font_bold, font_reg = _prov_fonts()
    img  = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((120, 90),  "Failed",        font=font_bold, fill=(220, 80, 80),   anchor="mm")
    draw.text((120, 130), "Retrying...",   font=font_reg,  fill=(140, 140, 160), anchor="mm")
    display_image(GPIO, pins, state, img)
