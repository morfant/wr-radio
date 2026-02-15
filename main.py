#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import time
import json
import os
import subprocess
import socket
import sys
import spidev
from PIL import Image, ImageDraw, ImageFont

# ===============================
# GPIO 핀 번호 설정 (BCM)
# ===============================
# 로터리 엔코더
S1 = 17   # CLK
S2 = 27   # DT
KEY = 22  # 버튼

# LCD
CS_PIN = 26
DC_PIN = 19
RST_PIN = 13
BL_PIN = 6

# ===============================
# 설정 파일
# ===============================
CONFIG_FILE = "/home/wr-radio/wr-radio/last_station.json"

radio_stations = [
    {"name": "Jeju Georo",        "url": "https://locus.creacast.com:9443/jeju_georo.mp3",             "color": (100, 200, 255)},
    {"name": "London Stave Hill", "url": "https://locus.creacast.com:9443/london_stave_hill.mp3",      "color": (255, 100, 100)},
    {"name": "Wicken Fen",        "url": "https://locus.creacast.com:9443/wicken_wicken_fen.mp3",      "color": (100, 255, 100)},
    {"name": "New York Wave Farm","url": "https://locus.creacast.com:9443/acra_wave_farm.mp3",         "color": (255, 200, 50)},
    {"name": "Marseille",         "url": "https://locus.creacast.com:9443/marseille_frioul.mp3",       "color": (200, 100, 255)},
]

# ===============================
# SPI 초기화
# ===============================
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 8000000
spi.mode = 0

# ===============================
# GPIO 초기화
# ===============================
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# 로터리 엔코더
GPIO.setup(S1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(S2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# LCD
GPIO.setup(CS_PIN, GPIO.OUT)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)

# PWM 객체
pwm_backlight = None

# ===============================
# mpv IPC 설정
# ===============================
MPV_SOCK = "/tmp/wr_mpv.sock"
player_process = None
is_playing = False

# ===============================
# 튜닝 파라미터
# ===============================
ROTATION_DEBOUNCE_SEC = 0.10
PLAY_SWITCH_DELAY_SEC = 0.40
SAVE_DELAY_SEC = 5.0
LOCK_FILE = "/tmp/wr_radio.lock"

# ===============================
# 백라이트 제어
# ===============================
def backlight_on():
    global pwm_backlight
    if pwm_backlight:
        pwm_backlight.stop()
        pwm_backlight = None
    GPIO.output(BL_PIN, GPIO.HIGH)

def backlight_off():
    global pwm_backlight
    if pwm_backlight:
        pwm_backlight.stop()
        pwm_backlight = None
    GPIO.output(BL_PIN, GPIO.LOW)

def set_brightness(level):
    global pwm_backlight
    if pwm_backlight:
        pwm_backlight.ChangeDutyCycle(level)
    else:
        pwm_backlight = GPIO.PWM(BL_PIN, 1000)
        pwm_backlight.start(level)

# ===============================
# LCD 저수준 제어
# ===============================
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
    write_cmd(0x36)
    if rotation == 0:
        write_data(0x00)
    elif rotation == 90:
        write_data(0x60)
    elif rotation == 180:
        write_data(0xC0)
    elif rotation == 270:
        write_data(0xA0)
    else:
        write_data(0x00)

def init_display(rotation=90):
    reset()
    write_cmd(0x01)
    time.sleep(0.15)
    write_cmd(0x11)
    time.sleep(0.12)
    write_cmd(0x3A)
    write_data(0x05)
    set_rotation(rotation)
    write_cmd(0x21)
    write_cmd(0x13)
    write_cmd(0x29)
    time.sleep(0.01)

# ===============================
# 그래픽 함수
# ===============================
def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def set_window(x0, y0, x1, y1):
    write_cmd(0x2A)
    write_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
    write_cmd(0x2B)
    write_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
    write_cmd(0x2C)

def display_image(image):
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

# ===============================
# UI 표시
# ===============================
def display_radio_info(current_index):
    """현재 라디오 스테이션 정보 표시"""
    station = radio_stations[current_index]
    
    image = Image.new('RGB', (240, 240), (15, 15, 15))
    draw = ImageDraw.Draw(image)
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 상단 바 (스테이션 색상)
    draw.rectangle([0, 0, 239, 50], fill=station["color"])
    
    # 스테이션 이름 (상단)
    # 긴 이름 처리
    name_parts = station["name"].split()
    if len(name_parts) > 2:
        line1 = " ".join(name_parts[:2])
        line2 = " ".join(name_parts[2:])
        draw.text((10, 8), line1, font=font_large, fill=(255, 255, 255))
        draw.text((10, 35), line2, font=font_small, fill=(255, 255, 255))
    else:
        bbox = draw.textbbox((0, 0), station["name"], font=font_large)
        text_width = bbox[2] - bbox[0]
        if text_width > 220:
            draw.text((10, 15), station["name"], font=font_medium, fill=(255, 255, 255))
        else:
            x = (240 - text_width) // 2
            draw.text((x, 12), station["name"], font=font_large, fill=(255, 255, 255))
    
    # 재생 상태
    status = "▶ PLAYING" if is_playing else "⏸ PAUSED"
    status_color = (100, 255, 100) if is_playing else (255, 100, 100)
    bbox = draw.textbbox((0, 0), status, font=font_medium)
    text_width = bbox[2] - bbox[0]
    x = (240 - text_width) // 2
    draw.text((x, 90), status, font=font_medium, fill=status_color)
    
    # 음파 애니메이션 (재생 중일 때)
    if is_playing:
        center_y = 140
        for i in range(5):
            height = 10 + (i % 3) * 8
            x_pos = 60 + i * 25
            draw.rectangle([x_pos, center_y - height, x_pos + 15, center_y + height], 
                         fill=(station["color"][0]//2, station["color"][1]//2, station["color"][2]//2))
    
    # 스테이션 번호
    station_num = f"{current_index + 1} / {len(radio_stations)}"
    bbox = draw.textbbox((0, 0), station_num, font=font_medium)
    text_width = bbox[2] - bbox[0]
    x = (240 - text_width) // 2
    draw.text((x, 180), station_num, font=font_medium, fill=(150, 150, 150))
    
    # 하단 안내
    draw.text((30, 215), "Turn to switch", font=font_small, fill=(100, 100, 100))
    
    display_image(image)

# ===============================
# 설정 로드/저장
# ===============================
def load_last_station():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                index = int(data.get('last_index', 0))
                if 0 <= index < len(radio_stations):
                    return index
        except Exception:
            pass
    return 0

def save_last_station(index):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'last_index': index}, f)
        print("💾 저장 완료")
    except Exception as e:
        print(f"저장 실패: {e}")

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

# ===============================
# mpv IPC 유틸
# ===============================
def _can_connect_mpv(sock_path=MPV_SOCK, timeout=0.2):
    if not os.path.exists(sock_path):
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(sock_path)
        s.close()
        return True
    except Exception:
        return False

def _wait_for_mpv_sock(timeout_sec=8.0):
    start = time.time()
    while time.time() - start < timeout_sec:
        if _can_connect_mpv(MPV_SOCK, timeout=0.2):
            return True
        time.sleep(0.05)
    return False

def mpv_cmd(payload):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(MPV_SOCK)
        s.send((json.dumps(payload) + "\n").encode("utf-8"))
        s.close()
        return True
    except Exception:
        return False

def ensure_mpv_running():
    global player_process

    if _can_connect_mpv(MPV_SOCK):
        return True

    try:
        if os.path.exists(MPV_SOCK):
            os.remove(MPV_SOCK)
    except Exception:
        pass

    cmd = [
        "mpv",
        "--no-video",
        "--idle=yes",
        "--no-terminal",
        "--no-config",
        "--load-scripts=no",
        "--osc=no",
        "--input-default-bindings=no",
        "--input-ipc-server=" + MPV_SOCK,
        "--volume=50",
        "--cache=yes",
        "--cache-secs=0.3",
        "--demuxer-readahead-secs=0.3",
        "--network-timeout=3",
    ]

    try:
        player_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"❌ mpv 실행 실패: {e}")
        player_process = None
        return False

    ok = _wait_for_mpv_sock(timeout_sec=8.0)
    if not ok:
        print("❌ mpv IPC 소켓 생성 실패")
        return False

    return True

def stop_playback():
    global is_playing
    if mpv_cmd({"command": ["stop"]}):
        is_playing = False
        print("⏹️  재생 중지")
    else:
        print("⚠️  stop 실패")

def play_station(index):
    global is_playing
    station = radio_stations[index]
    print(f"\n🎵 재생: {station['name']}")
    
    ok = mpv_cmd({"command": ["loadfile", station["url"], "replace"]})
    if ok:
        is_playing = True
    else:
        print("❌ 재생 실패")
        is_playing = False
    
    # LCD 업데이트
    display_radio_info(index)

# ===============================
# 메인
# ===============================
def main():
    global is_playing

    acquire_lock()

    current_index = load_last_station()

    # LCD 초기화
    print("LCD 초기화 중...")
    init_display(rotation=90)
    backlight_on()

    # mpv 초기화
    if not ensure_mpv_running():
        print("mpv를 시작할 수 없어 종료합니다.")
        GPIO.cleanup()
        release_lock()
        return

    # 초기 화면 표시
    display_radio_info(current_index)

    s1LastState = GPIO.input(S1)
    keyLastState = GPIO.input(KEY)

    last_rotation_time = 0.0
    needs_save = False
    last_change_time = 0.0
    pending_play = False
    last_station_change_time = 0.0

    print("=" * 50)
    print("📻 라디오 시작!")
    print("=" * 50)
    print("회전: 방송국 선택")
    print("버튼: 재생/정지")
    print("Ctrl+C: 종료")
    print("=" * 50)

    try:
        while True:
            # 로터리 처리
            s1State = GPIO.input(S1)
            s2State = GPIO.input(S2)

            if s1State != s1LastState:
                now = time.time()
                if now - last_rotation_time > ROTATION_DEBOUNCE_SEC:
                    if s2State != s1State:
                        current_index = (current_index + 1) % len(radio_stations)
                    else:
                        current_index = (current_index - 1) % len(radio_stations)

                    print(f"→ {radio_stations[current_index]['name']}")
                    
                    # LCD 업데이트
                    display_radio_info(current_index)

                    needs_save = True
                    last_change_time = now

                    if is_playing:
                        pending_play = True
                        last_station_change_time = now

                    last_rotation_time = now

            s1LastState = s1State

            # 버튼 처리
            keyState = GPIO.input(KEY)
            if keyState == 0 and keyLastState == 1:
                if is_playing:
                    stop_playback()
                else:
                    play_station(current_index)

                display_radio_info(current_index)

                now = time.time()
                needs_save = True
                last_change_time = now
                time.sleep(0.3)

            keyLastState = keyState

            # 로터리 멈춘 후 재생 전환
            if pending_play and (time.time() - last_station_change_time) >= PLAY_SWITCH_DELAY_SEC:
                play_station(current_index)
                pending_play = False

            # 저장
            if needs_save and (time.time() - last_change_time) >= SAVE_DELAY_SEC:
                save_last_station(current_index)
                needs_save = False

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n프로그램 종료")
        if needs_save:
            save_last_station(current_index)

        try:
            stop_playback()
        except Exception:
            pass

    finally:
        try:
            if player_process:
                player_process.terminate()
                player_process.wait(timeout=2)
        except Exception:
            pass

        if player_process:
            try:
                if os.path.exists(MPV_SOCK):
                    os.remove(MPV_SOCK)
            except Exception:
                pass

        if pwm_backlight:
            pwm_backlight.stop()

        GPIO.cleanup()
        spi.close()
        release_lock()

if __name__ == "__main__":
    main()
