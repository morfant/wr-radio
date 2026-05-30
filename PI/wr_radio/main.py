#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import ImageDraw, ImageFont
import os
import signal
import sys
import time

import RPi.GPIO as GPIO
import spidev
from PIL import Image

from .state import AppState
from .config import setup_config_interactive, save_settings
from . import player
from . import weather
from . import display
from .input import InputConfig, ButtonState, read_rotary, handle_button
from .battery import BatteryMonitor
from . import bluetooth
from . import wifi

LOCK_FILE = "/tmp/wr_radio.lock"

# BCM pins
PIN_S1 = 17
PIN_S2 = 27
PIN_KEY = 22

PIN_CS = 26
PIN_DC = 13
PIN_RST = 6
PIN_BL = 12

# 시스템 메뉴 항목
SYSTEM_MENU_ITEMS = [
    {"label": "Brightness", "action": "brightness"},
    {"label": "Bluetooth",  "action": "bluetooth"},
    {"label": "WiFi Setup", "action": "wifi_setup"},
    {"label": "Power Off",  "action": "shutdown"},
    {"label": "Back",       "action": "back"},
]

# 폰트 경로
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_PATH_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        path = FONT_PATH if bold else FONT_PATH_REGULAR
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int((f.read() or "0").strip())
            if pid > 0:
                os.kill(pid, 0)
                print(f"❌ 이미 실행 중입니다 (pid={pid}).")
                sys.exit(1)
        except ProcessLookupError:
            pass
        except Exception:
            pass

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


def pwm_safe_close(state: AppState):
    try:
        if state.pwm_backlight is not None:
            try:
                state.pwm_backlight.stop()
            except Exception:
                pass
            try:
                del state.pwm_backlight
            except Exception:
                pass
    finally:
        state.pwm_backlight = None


def set_brightness(state: AppState, level: int, bl_pin: int) -> int:
    level = max(10, min(100, level))
    if state.pwm_backlight is None:
        state.pwm_backlight = GPIO.PWM(bl_pin, 1000)
        state.pwm_backlight.start(level)
        state.current_brightness = level
        return level
    try:
        state.pwm_backlight.ChangeDutyCycle(level)
        state.current_brightness = level
        return level
    except Exception:
        pwm_safe_close(state)
        state.pwm_backlight = GPIO.PWM(bl_pin, 1000)
        state.pwm_backlight.start(level)
        state.current_brightness = level
        return level


def draw_system_menu(state: AppState, selected_index: int) -> Image.Image:
    """시스템 메뉴 화면 렌더링"""
    img = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_title = load_font(13, bold=False)
    font_item  = load_font(15, bold=False)

    # 타이틀
    draw.text((20, 18), "System", fill=(80, 80, 100), font=font_title)
    draw.line([(20, 38), (220, 38)], fill=(40, 40, 50), width=1)

    # 메뉴 항목 — 항목 수에 따라 간격 자동 조정
    n = len(SYSTEM_MENU_ITEMS)
    start_y = 50
    item_h = min(40, (240 - start_y) // n)

    for i, item in enumerate(SYSTEM_MENU_ITEMS):
        y = start_y + i * item_h
        is_selected = (i == selected_index)

        if is_selected:
            draw.rounded_rectangle([(16, y - 1), (224, y + item_h - 3)],
                                   radius=6, fill=(25, 25, 40))
            label_color = (230, 230, 255)
        else:
            label_color = (100, 100, 120)

        draw.text((32, y + max(2, (item_h - 18) // 2)),
                  item["label"], fill=label_color, font=font_item)

    return img


def draw_brightness_menu(state: AppState) -> Image.Image:
    """밝기 조절 화면"""
    img = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_title = load_font(13, bold=False)
    font_value = load_font(22, bold=False)

    draw.text((20, 18), "Brightness", fill=(80, 80, 100), font=font_title)
    draw.line([(20, 38), (220, 38)], fill=(40, 40, 50), width=1)
    draw.text((120, 120), f"{state.current_brightness}%", fill=(230, 230, 255), font=font_value, anchor="mm")

    return img


def return_to_normal(state: AppState, gpio_pins: dict, radio_stations: list, current_index: int):
    """시스템 메뉴에서 normal 복귀 시 화면 완전 초기화 후 재렌더"""
    try:
        blank = Image.new("RGB", (240, 240), (0, 0, 0))
        display.display_image(GPIO, {"CS": gpio_pins["CS"], "DC": gpio_pins["DC"]}, state, blank)
    except Exception:
        pass
    wd = weather.get_cached_weather(state, radio_stations[current_index]["lat"], radio_stations[current_index]["lon"])
    display.display_radio_info(GPIO, {"CS": gpio_pins["CS"], "DC": gpio_pins["DC"]}, state, weather_data=wd, force_full=True)
    state.last_displayed_weather = wd


def do_shutdown(state: AppState, gpio_pins: dict):
    """설정 저장 → LCD 메시지 → mpv 종료 → halt"""
    print("\n🔴 종료 시작...")

    if state.needs_save:
        save_settings(state.current_index, state.current_volume, state.current_brightness)
        state.needs_save = False

    try:
        img = Image.new("RGB", (240, 240), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = load_font(16, bold=False)
        draw.text((120, 100), "Shutting down...", fill=(140, 140, 160), font=font, anchor="mm")
        draw.text((120, 135), "Wait 15 sec before", fill=(200, 60, 60), font=font, anchor="mm")
        draw.text((120, 158), "switching off", fill=(200, 60, 60), font=font, anchor="mm")
        display.display_image(GPIO, {"CS": gpio_pins["CS"], "DC": gpio_pins["DC"]}, state, img)
    except Exception:
        pass

    time.sleep(3.0)

    try:
        player.stop_playback(state)
    except Exception:
        pass

    # BT 연결 해제
    if state.bt_mac:
        try:
            bluetooth.disconnect(state.bt_mac)
            state.bt_mac  = ""
            state.bt_sink = ""
        except Exception:
            pass

    try:
        img = Image.new("RGB", (240, 240), (0, 0, 0))
        display.display_image(GPIO, {"CS": gpio_pins["CS"], "DC": gpio_pins["DC"]}, state, img)
    except Exception:
        pass

    os.system("sudo halt")


def _show_bt_msg(state: AppState, gpio_pins: dict, msg: str, color: tuple):
    img  = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((20, 18), "Bluetooth", fill=(80, 80, 100), font=load_font(13))
    draw.line([(20, 38), (220, 38)], fill=(40, 40, 50), width=1)
    for i, line in enumerate(msg.split("\n")):
        draw.text((120, 110 + i * 28), line, fill=color,
                  font=load_font(15), anchor="mm")
    display.display_image(GPIO, {"CS": gpio_pins["CS"], "DC": gpio_pins["DC"]},
                          state, img)


def _bt_connect(state: AppState, gpio_pins: dict,
                mac: str, name: str, is_paired: bool) -> bool:
    # 기존 연결 정보 저장 (실패 시 복구용)
    prev_mac  = state.bt_mac  if state.bt_mac != mac else ""

    if not is_paired:
        _show_bt_msg(state, gpio_pins, f"Pairing...\n{name[:20]}", (255, 200, 80))
        if not bluetooth.pair(mac):
            _show_bt_msg(state, gpio_pins, "Pairing failed", (200, 80, 80))
            time.sleep(2.0)
            _bt_ensure_output(state, gpio_pins, prev_mac)
            return False

    _show_bt_msg(state, gpio_pins, f"Connecting...\n{name[:20]}", (255, 200, 80))
    if not bluetooth.connect(mac):
        _show_bt_msg(state, gpio_pins, "Connect failed", (200, 80, 80))
        time.sleep(2.0)
        _bt_ensure_output(state, gpio_pins, prev_mac)
        return False

    sink = bluetooth.find_bt_sink()
    if not sink:
        _show_bt_msg(state, gpio_pins, "Sink not found", (200, 80, 80))
        bluetooth.disconnect(mac)
        time.sleep(2.0)
        _bt_ensure_output(state, gpio_pins, prev_mac)
        return False

    # 성공 → 기존 연결 해제 후 sink 재확인
    if prev_mac:
        bluetooth.disconnect(prev_mac)
        time.sleep(0.5)
        # 기존 sink가 사라졌으니 새 sink 다시 탐색
        sink = bluetooth.find_bt_sink(retries=4, wait=0.5)
        if not sink:
            _show_bt_msg(state, gpio_pins, "Sink lost", (200, 80, 80))
            time.sleep(2.0)
            _bt_ensure_output(state, gpio_pins, "")
            return False

    state.bt_mac      = mac
    state.bt_sink     = sink
    state.output_mode = "bluetooth"
    was_playing = state.is_playing
    player.stop_playback(state)
    player.restart_mpv(state)
    if was_playing:
        player.play_station(state, state.current_index)
    _show_bt_msg(state, gpio_pins, f"Connected\n{name[:20]}", (100, 200, 100))
    time.sleep(1.5)
    return True


def _bt_ensure_output(state: AppState, gpio_pins: dict, prev_mac: str):
    """
    연결 실패 후 출력 복구.
    - 이전 BT 장치가 살아있으면 그대로 유지
    - 아니면 스피커로 fallback
    """
    was_playing = state.is_playing

    # 이전 BT 장치 확인
    if prev_mac and bluetooth.is_device_connected(prev_mac):
        sink = bluetooth.get_current_bt_sink()
        if sink:
            # 기존 BT 연결 정상 → 유지
            state.bt_mac      = prev_mac
            state.bt_sink     = sink
            state.output_mode = "bluetooth"
            return

    # 이전 연결도 없음 → 스피커 fallback
    state.output_mode = "speaker"
    state.bt_mac      = ""
    state.bt_sink     = ""
    player.stop_playback(state)
    player.restart_mpv(state)
    if was_playing:
        player.play_station(state, state.current_index)


def _bt_disconnect(state: AppState, gpio_pins: dict):
    _show_bt_msg(state, gpio_pins, "Disconnecting...", (180, 180, 180))
    bluetooth.disconnect(state.bt_mac)
    state.output_mode = "speaker"
    state.bt_mac = state.bt_sink = ""
    was_playing = state.is_playing
    player.stop_playback(state)
    player.restart_mpv(state)
    if was_playing:
        player.play_station(state, state.current_index)
    _show_bt_msg(state, gpio_pins, "Disconnected", (100, 200, 100))
    time.sleep(1.2)


def _draw_bt_list(state, devices, selected, scanning, scan_elapsed):
    SCAN_DURATION = 15
    img  = Image.new("RGB", (240, 240), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    ft   = load_font(13)
    fi   = load_font(14)
    fs   = load_font(11)

    draw.text((20, 18),
              "Bluetooth" + ("  Scanning..." if scanning else ""),
              fill=(80, 80, 100), font=ft)
    draw.line([(20, 38), (220, 38)], fill=(40, 40, 50), width=1)
    if scanning:
        bw = int(200 * min(scan_elapsed, SCAN_DURATION) / SCAN_DURATION)
        draw.rectangle([(20, 34), (20 + bw, 37)], fill=(60, 100, 180))

    scan_label = "  Scanning..." if scanning else "  Scan for devices"
    specials   = [scan_label]
    if state.bt_mac:
        specials.append("  Disconnect")
    specials.append("  Back")
    all_items = devices + specials

    item_h  = 36
    start_y = 48
    visible = 5
    offset  = max(0, selected - visible + 1)

    for slot, item in enumerate(all_items[offset: offset + visible]):
        ridx = slot + offset
        y    = start_y + slot * item_h
        sel  = (ridx == selected)
        if sel and not scanning:
            draw.rounded_rectangle([(16, y), (224, y + 28)],
                                   radius=5, fill=(25, 25, 40))
        if isinstance(item, tuple):
            mac, name, paired = item
            conn  = (mac == state.bt_mac)
            dot   = (100, 160, 255) if conn else (70, 70, 90) if paired else (50, 50, 50)
            if scanning:
                dot = tuple(c // 3 for c in dot)
            draw.ellipse([22, y+9, 30, y+17], fill=dot)
            if scanning:
                nc = (60, 60, 70)
            elif sel:
                nc = (230, 230, 255)
            else:
                nc = (160, 160, 200)
            draw.text((36, y+5), name[:22], fill=nc, font=fi)
            if not paired and not scanning:
                draw.text((198, y+5), "New", fill=(100, 200, 100), font=fs)
        else:
            if scanning:
                c = (50, 50, 50)   # 스캔 중 특수 항목도 dim
            elif "Disconnect" in item:
                c = (255, 120, 120) if sel else (180, 80, 80)
            elif "Scan" in item:
                c = (200, 200, 100) if sel else (120, 120, 60)
            else:
                c = (180, 180, 200) if sel else (100, 100, 120)
            draw.text((20, y+5), item, fill=c, font=fi)

    total = len(all_items)
    if total > visible:
        bh  = max(10, int(190 * visible / total))
        by  = 48 + int(190 * offset / total)
        draw.rectangle([(235, 48), (237, 238)], fill=(30, 30, 30))
        draw.rectangle([(235, by), (237, by + bh)], fill=(80, 80, 100))

    return img


def do_bluetooth(state: AppState, gpio_pins: dict):
    SCAN_DURATION  = 15    # 초
    POST_SCAN_WAIT = 8     # 스캔 종료 후 이름 조회 대기 (초)
    REFRESH_SEC    = 0.5
    DEBOUNCE       = 0.02
    pins_disp = {"CS": gpio_pins["CS"], "DC": gpio_pins["DC"]}

    scanner      = None
    scanning     = False
    scan_start   = 0.0
    scan_ended   = 0.0    # 스캔 종료 시각 (0=종료 안 됨)
    selected     = 0
    last_refresh = 0.0
    scan_was_playing = False  # 스캔 시작 전 재생 상태

    devices = [(mac, name, True)
               for mac, name in bluetooth.get_paired_devices()]

    if state.bt_mac:
        for i, (mac, _, _) in enumerate(devices):
            if mac == state.bt_mac:
                selected = i
                break

    def specials():
        s = ["  Scanning..." if scanning else "  Scan for devices"]
        if state.bt_mac:
            s.append("  Disconnect")
        s.append("  Back")
        return s

    def all_items():
        return devices + specials()

    def render():
        el  = (time.time() - scan_start) if scanning else 0
        img = _draw_bt_list(state, devices, selected, scanning, el)
        display.display_image(GPIO, pins_disp, state, img)

    render()

    s1_last  = GPIO.input(gpio_pins["S1"])
    key_last = GPIO.input(gpio_pins["KEY"])
    last_rot = time.time()

    try:
        while True:
            now = time.time()

            # ── 스캔 중: 진행 바만 갱신, 입력 무시 ────────
            if scanning:
                elapsed = now - scan_start
                if elapsed >= SCAN_DURATION:
                    scanner.stop()
                    scanning   = False
                    scan_ended = now
                    devices[:] = scanner.get_devices()
                    render()
                elif (now - last_refresh) >= REFRESH_SEC:
                    devices[:] = scanner.get_devices()
                    render()
                    last_refresh = now
                # 입력 상태만 읽어서 버림 (눌림 누적 방지)
                s1_last  = GPIO.input(gpio_pins["S1"])
                key_last = GPIO.input(gpio_pins["KEY"])
                time.sleep(0.05)
                continue

            # ── grace period: 이름 조회 완료 대기 ──────────
            elif scan_ended and scanner:
                if (now - last_refresh) >= REFRESH_SEC:
                    devices[:] = scanner.get_devices()
                    render()
                    last_refresh = now
                if not scanner.has_pending() or (now - scan_ended) >= POST_SCAN_WAIT:
                    devices[:] = scanner.get_devices()
                    render()
                    scanner    = None
                    scan_ended = 0.0
                    if scan_was_playing:
                        player.play_station(state, state.current_index)
                        scan_was_playing = False

            # ── 로터리 ─────────────────────────────────────
            s1 = GPIO.input(gpio_pins["S1"])
            s2 = GPIO.input(gpio_pins["S2"])
            if s1 == 0 and s1_last == 1 and (now - last_rot) > DEBOUNCE:
                direction = -1 if s2 == 1 else 1
                selected  = (selected + direction) % len(all_items())
                last_rot  = now
                render()
            s1_last = s1

            # ── 버튼 ───────────────────────────────────────
            key = GPIO.input(gpio_pins["KEY"])
            if key == 1 and key_last == 0:
                items = all_items()
                item  = items[selected]

                if isinstance(item, tuple):
                    mac, name, is_paired = item
                    if scanner:
                        scanner.stop()
                        scanning = False
                        scanner  = None
                    if mac == state.bt_mac:
                        _bt_disconnect(state, gpio_pins)
                    else:
                        _bt_connect(state, gpio_pins, mac, name, is_paired)
                    break

                elif "Scan" in item and not scanning:
                    if scanner:
                        scanner.stop()
                    # 스캔 중 오디오 정지 (BT 간섭 방지)
                    scan_was_playing = state.is_playing
                    if scan_was_playing:
                        player.stop_playback(state)
                    scanner      = bluetooth.Scanner()
                    scanning     = True
                    scan_start   = now
                    scan_ended   = 0.0
                    last_refresh = 0.0
                    scanner.start()
                    print("🔵 BT 스캔 시작")

                elif "Disconnect" in item:
                    if scanner:
                        scanner.stop()
                        scanning = False
                        scanner  = None
                    _bt_disconnect(state, gpio_pins)
                    break

                elif "Back" in item:
                    break

            key_last = key
            time.sleep(0.005)

    finally:
        if scanner:
            scanner.stop()


def main():
    cfg = setup_config_interactive()
    if cfg is None:
        print("❌ 설정 초기화 실패")
        return

    state = AppState()
    state.openweather_api_key = cfg.get("openweather_api_key", "")
    state.enable_weather = bool(state.openweather_api_key)
    state.radio_stations = cfg["stations"]
    state.current_index = cfg.get("last_station", 0)
    if not (0 <= state.current_index < len(state.radio_stations)):
        state.current_index = 0

    state.current_volume = cfg.get("last_volume", 50)
    state.current_brightness = cfg.get("last_brightness", 100)
    print(f"🔊 볼륨: {state.current_volume}%  💡 밝기: {state.current_brightness}%")

    print("🌤️  날씨 기능 " + ("활성화" if state.enable_weather else "비활성화 (API 키 없음)"))
    print(f"📻 스테이션 {len(state.radio_stations)}개 로드")

    acquire_lock()

    # SPI init
    state.spi = spidev.SpiDev()
    state.spi.open(0, 0)
    state.spi.max_speed_hz = 16_000_000
    state.spi.mode = 0

    # GPIO init
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(PIN_S1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_S2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_KEY, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.setup(PIN_CS, GPIO.OUT)
    GPIO.setup(PIN_DC, GPIO.OUT)
    GPIO.setup(PIN_RST, GPIO.OUT)
    GPIO.setup(PIN_BL, GPIO.OUT)

    pins = {
        "S1": PIN_S1,
        "S2": PIN_S2,
        "KEY": PIN_KEY,
        "CS": PIN_CS,
        "DC": PIN_DC,
        "RST": PIN_RST,
        "BL": PIN_BL,
    }

    # LCD init
    print("LCD 초기화 중...")
    display.init_display(GPIO, {"CS": PIN_CS, "DC": PIN_DC, "RST": PIN_RST}, state, rotation=90)

    # PWM init
    pwm_safe_close(state)
    try:
        state.pwm_backlight = GPIO.PWM(PIN_BL, 1000)
        state.pwm_backlight.start(state.current_brightness)
        print(f"백라이트 초기화 완료 ({state.current_brightness}%)")
    except Exception as e:
        print(f"백라이트 초기화 실패: {e}")
        state.pwm_backlight = None

    # splash screen
    splash_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'splash.png')
    try:
        splash_img = Image.open(splash_path).convert('RGB')
        splash_canvas = Image.new('RGB', (240, 240), (0, 0, 0))
        y_offset = (240 - splash_img.height) // 2
        splash_canvas.paste(splash_img, (0, y_offset))
        display.display_image(GPIO, {'CS': PIN_CS, 'DC': PIN_DC}, state, splash_canvas)
        print('스플래시 화면 표시')
    except Exception as e:
        print(f'스플래시 로드 실패: {e}')
        clear_image = Image.new('RGB', (240, 240), (0, 0, 0))
        display.display_image(GPIO, {'CS': PIN_CS, 'DC': PIN_DC}, state, clear_image)

    # ── WiFi 체크 (연결 없으면 프로비저닝 모드) ────────────
    if not wifi.is_wifi_connected():
        print("WiFi 연결 없음 → 프로비저닝 모드")
        wifi.provision_wifi(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state)

    # ── 시작 시 BT 상태 감지 (mpv 시작 전) ────────────────
    devices = bluetooth.get_paired_devices()
    connected_mac = next(
        (mac for mac, _ in devices if bluetooth.is_device_connected(mac)), ""
    )
    if connected_mac:
        existing_sink = bluetooth.find_bt_sink(retries=6, wait=1.0)
        if existing_sink:
            state.output_mode = "bluetooth"
            state.bt_sink = existing_sink
            state.bt_mac = connected_mac
            print(f"🔵 BT 장치 감지됨: {connected_mac} → BT 모드로 시작")
        else:
            print(f"⚠️  BT 연결됨({connected_mac}) 하지만 sink 없음 → 스피커 모드")

    # mpv init (BT 감지 결과에 따라 출력 장치 결정)
    if not player.ensure_mpv_running(state):
        print("mpv를 시작할 수 없어 종료합니다.")
        try:
            pwm_safe_close(state)
        except Exception:
            pass
        try:
            GPIO.cleanup()
        except Exception:
            pass
        release_lock()
        return

    player.set_volume(state, state.current_volume)

    player.start_audio_monitor(state)
    print("🎧 오디오 모니터 시작")

    bat_mon = BatteryMonitor()
    if bat_mon.start():
        state.battery_monitor = bat_mon
    else:
        print("⚠️  배터리 모니터 없이 진행")
        state.battery_monitor = None

    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, Image.new("RGB", (240, 240), (0, 0, 0)))
    wd = weather.get_cached_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"])
    display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=True)

    player.play_station(state, state.current_index)
    state.is_playing = True

    weather.start_weather_update(state, state.current_index)

    input_cfg = InputConfig(
        rotation_debounce_sec=0.02,
        play_switch_delay_sec=0.40,
        display_update_delay=0.01,
        mode_timeout_sec=3.0,
        save_delay_sec=1.0,
        short_press_min_sec=0.05,
        long_press_sec=1.0,
    )
    btn_state = ButtonState()

    s1_last = GPIO.input(PIN_S1)
    key_last = GPIO.input(PIN_KEY)
    last_rotation_time = 0.0
    last_animation_update = 0.0
    last_battery_update = 0.0
    last_weather_check = 0.0
    last_time_minute = -1
    menu_index = 0

    print("=" * 50)
    print("📻 WR-Radio (Modular)")
    print("=" * 50)
    print("로터리: 방송국 선택")
    print("버튼 짧게: 볼륨 조절 모드")
    print("버튼 1초: 시스템 메뉴")
    print("모드에서 버튼: 일반 모드 복귀")
    print("Ctrl+C: 종료")
    print("=" * 50)

    def _sigterm_handler(signum, frame):
        print("\nSIGTERM 수신 → 종료 시작")
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _sigterm_handler)

    try:
        while True:
            now = time.time()

            # volume 모드 타임아웃 → normal 복귀
            if (
                state.current_mode == "volume"
                and (now - state.mode_enter_time) >= input_cfg.mode_timeout_sec
            ):
                state.current_mode = "normal"
                print("→ 일반 모드 (자동)")
                return_to_normal(state, pins, state.radio_stations, state.current_index)

            # system_menu 타임아웃 → normal 복귀
            elif (
                state.current_mode == "system_menu"
                and (now - state.mode_enter_time) >= input_cfg.mode_timeout_sec
            ):
                state.current_mode = "normal"
                menu_index = 0
                print("→ 일반 모드 (메뉴 타임아웃)")
                return_to_normal(state, pins, state.radio_stations, state.current_index)

            # brightness 모드 타임아웃 → system_menu 복귀
            elif (
                state.current_mode == "brightness"
                and (now - state.mode_enter_time) >= input_cfg.mode_timeout_sec
            ):
                state.current_mode = "system_menu"
                state.mode_enter_time = now
                print("→ 시스템 메뉴 (자동)")
                blank = Image.new("RGB", (240, 240), (0, 0, 0))
                display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, blank)
                img = draw_system_menu(state, menu_index)
                display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img)

            # rotary
            s1_last, direction, last_rotation_time = read_rotary(
                GPIO, pins, s1_last, now, last_rotation_time, input_cfg
            )
            if direction != 0:
                if state.current_mode == "normal":
                    state.current_index = (state.current_index + direction) % len(state.radio_stations)
                    print(f"→ {state.radio_stations[state.current_index]['name']}")
                    state.last_input_time = now
                    state.needs_save = True
                    state.last_change_time = now
                    state.pending_play = True
                    state.last_station_change_time = now
                    state.last_displayed_weather = None

                elif state.current_mode == "volume":
                    player.set_volume(state, state.current_volume + direction * 5)
                    state.needs_save = True
                    state.last_change_time = now
                    state.mode_enter_time = now
                    display.display_mode_indicator(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, "volume", state.current_volume)

                elif state.current_mode == "brightness":
                    set_brightness(state, state.current_brightness + direction * 10, PIN_BL)
                    state.needs_save = True
                    state.last_change_time = now
                    state.mode_enter_time = now
                    img = draw_brightness_menu(state)
                    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img)

                elif state.current_mode == "system_menu":
                    menu_index = (menu_index + direction) % len(SYSTEM_MENU_ITEMS)
                    state.mode_enter_time = now
                    print(f"→ 메뉴: {SYSTEM_MENU_ITEMS[menu_index]['label']}")
                    img = draw_system_menu(state, menu_index)
                    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img)

            # button events
            key_last, ev = handle_button(GPIO, pins, state, now, key_last, btn_state, input_cfg)

            if ev == "exit_mode":
                if state.current_mode == "brightness":
                    state.current_mode = "system_menu"
                    state.mode_enter_time = now
                    print("→ 시스템 메뉴")
                    blank = Image.new("RGB", (240, 240), (0, 0, 0))
                    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, blank)
                    img = draw_system_menu(state, menu_index)
                    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img)
                else:
                    state.current_mode = "normal"
                    print("→ 일반 모드")
                    wd = weather.get_cached_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"])
                    display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=True)

            elif ev == "enter_volume":
                state.current_mode = "volume"
                state.mode_enter_time = now
                print("🔊 볼륨 조절 모드")
                display.display_mode_indicator(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, "volume", state.current_volume)

            elif ev == "enter_system_menu":
                state.current_mode = "system_menu"
                state.mode_enter_time = now
                menu_index = 0
                print("⚙️  시스템 메뉴")
                img = draw_system_menu(state, menu_index)
                display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img)

            elif ev == "menu_select":
                action = SYSTEM_MENU_ITEMS[menu_index]["action"]
                print(f"✅ 선택: {SYSTEM_MENU_ITEMS[menu_index]['label']}")

                if action == "shutdown":
                    do_shutdown(state, pins)
                    break

                elif action == "bluetooth":
                    do_bluetooth(state, pins)
                    state.current_mode = "normal"
                    menu_index = 0
                    return_to_normal(state, pins, state.radio_stations, state.current_index)

                elif action == "brightness":
                    state.current_mode = "brightness"
                    state.mode_enter_time = now
                    print("💡 밝기 조절 모드")
                    blank = Image.new("RGB", (240, 240), (0, 0, 0))
                    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, blank)
                    img = draw_brightness_menu(state)
                    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img)

                elif action == "wifi_setup":
                    was_playing = state.is_playing
                    player.stop_playback(state)
                    wifi.provision_wifi(GPIO, pins, state)
                    state.current_mode = "normal"
                    menu_index = 0
                    if was_playing:
                        player.play_station(state, state.current_index)
                    return_to_normal(state, pins, state.radio_stations, state.current_index)

                elif action == "back":
                    state.current_mode = "normal"
                    menu_index = 0
                    print("→ 일반 모드 (메뉴 복귀)")
                    return_to_normal(state, pins, state.radio_stations, state.current_index)

            # display update after input settled (normal mode)
            if state.current_mode == "normal":
                if state.last_input_time > 0 and state.current_index != state.last_updated_index:
                    if (now - state.last_input_time) >= input_cfg.display_update_delay:
                        if weather.should_update_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"]):
                            weather.start_weather_update(state, state.current_index)
                        wd = weather.get_cached_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"])
                        display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=False)
                        state.last_updated_index = state.current_index

            # play switch after rotary stop
            if state.pending_play and (now - state.last_station_change_time) >= input_cfg.play_switch_delay_sec:
                player.play_station(state, state.current_index)
                state.pending_play = False
                if state.battery_monitor:
                    state.battery_monitor.pause_sampling()
                img = Image.new("RGB", (240, 240), (0, 0, 0))
                display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                state.animation_frame = 0
                state.animation_cleared = True

            # 애니메이션 (normal 모드에서만)
            if state.is_playing and state.current_mode == "normal":
                if state.audio_playing:
                    state.animation_cleared = False
                    if (now - last_animation_update) >= 1.0:
                        img = Image.new("RGB", (240, 240), (0, 0, 0))
                        draw = ImageDraw.Draw(img)
                        display.draw_sine_wave_animation(draw, state.animation_frame, state.current_volume)
                        state.animation_frame = (state.animation_frame + 1) % 100
                        display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                        last_animation_update = now
                else:
                    state.animation_cleared = False
                    if (now - last_animation_update) >= 0.2:
                        img = Image.new("RGB", (240, 240), (0, 0, 0))
                        draw = ImageDraw.Draw(img)
                        display.draw_loading_indicator(draw, state.animation_frame)
                        state.animation_frame = (state.animation_frame + 1) % 100
                        display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                        last_animation_update = now

            elif not state.is_playing and not state.animation_cleared:
                img = Image.new("RGB", (240, 240), (0, 0, 0))
                display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                state.animation_frame = 0
                state.animation_cleared = True

            # 배터리 업데이트 (normal 모드에서만)
            if state.current_mode == "normal" and state.battery_monitor is not None:
                bat_interval = 1.0 if (state.battery_monitor.is_low or state.battery_monitor.is_charging != getattr(state, "_last_displayed_charging", None)) else 10.0
                if (now - last_battery_update) >= bat_interval:
                    display.display_battery_only(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state)
                    last_battery_update = now

            # 날씨 데이터 도착 시 화면 갱신
            if state.current_mode == "normal" and (now - last_weather_check) >= 2.0:
                last_weather_check = now
                st = state.radio_stations[state.current_index]
                wd = weather.get_cached_weather(state, st["lat"], st["lon"])
                if wd and state.last_displayed_weather != wd:
                    display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=True)
                    state.last_displayed_weather = wd

            # 분 단위 시간 갱신
            if state.current_mode == "normal":
                cur_minute = int(now / 60)
                if cur_minute != last_time_minute:
                    last_time_minute = cur_minute
                    display.display_time_only(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state)

            # save
            if state.needs_save and (now - state.last_change_time) >= input_cfg.save_delay_sec:
                save_settings(state.current_index, state.current_volume, state.current_brightness)
                state.needs_save = False

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n프로그램 종료")
        if state.needs_save:
            save_settings(state.current_index, state.current_volume, state.current_brightness)
        try:
            player.stop_playback(state)
        except Exception:
            pass

    finally:
        print("\n정리 중...")

        player.shutdown_player(state)

        if state.battery_monitor:
            state.battery_monitor.stop()

        try:
            pwm_safe_close(state)
        except Exception:
            pass

        try:
            GPIO.cleanup()
        except Exception:
            pass

        try:
            if state.spi:
                state.spi.close()
        except Exception:
            pass

        release_lock()
        print("종료 완료")


if __name__ == "__main__":
    main()
