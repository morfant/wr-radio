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
import requests
import threading
from PIL import Image, ImageDraw, ImageFont

# ===============================
# GPIO 핀 번호 설정 (BCM)
# ===============================
S1 = 17   # 로터리 CLK
S2 = 27   # 로터리 DT
KEY = 22  # 로터리 버튼

CS_PIN = 26   # LCD
DC_PIN = 19
RST_PIN = 13
BL_PIN = 6

# ===============================
# 설정 파일
# ===============================
CONFIG_FILE = "/home/wr-radio/wr-radio/config.json"
LOCK_FILE = "/tmp/wr_radio.lock"

# 기본 스테이션 목록
DEFAULT_STATIONS = [
    {
        "name": "Jeju Georo",
        "url": "https://locus.creacast.com:9443/jeju_georo.mp3",
        "location": "Jeju, South Korea",
        "lat": 33.509306,
        "lon": 126.562000,
        "color": [100, 200, 255]
    },
    {
        "name": "London Stave Hill",
        "url": "https://locus.creacast.com:9443/london_stave_hill.mp3",
        "location": "London, UK",
        "lat": 51.502111,
        "lon": -0.040278,
        "color": [255, 100, 100]
    },
    {
        "name": "New York Wave Farm",
        "url": "https://locus.creacast.com:9443/acra_wave_farm.mp3",
        "location": "Acra, New York",
        "lat": 42.319111,
        "lon": -74.076611,
        "color": [255, 200, 50]
    },
    {
        "name": "Jasper Ridge",
        "url": "https://locus.creacast.com:9443/jasper_ridge_birdcast.mp3",
        "location": "California, USA",
        "lat": 37.403611,
        "lon": -122.238000,
        "color": [100, 255, 100]
    },
    {
        "name": "Mt. Fuji Forest",
        "url": "http://mp3s.nc.u-tokyo.ac.jp/Fuji_CyberForest.mp3",
        "location": "Yamanashi, Japan",
        "lat": 35.4088,
        "lon": 138.86,
        "color": [200, 100, 255]
    }
]

# ===============================
# 전역 변수
# ===============================
weather_cache = {}
WEATHER_CACHE_TIME = 600  # 10분
weather_lock = threading.Lock()

OPENWEATHER_API_KEY = ""
ENABLE_WEATHER = False
radio_stations = []

spi = None
pwm_backlight = None
player_process = None
is_playing = False

MPV_SOCK = "/tmp/wr_mpv.sock"
ROTATION_DEBOUNCE_SEC = 0.10
PLAY_SWITCH_DELAY_SEC = 0.40
LCD_UPDATE_DELAY = 0.50
SAVE_DELAY_SEC = 1.0

# ===============================
# 설정 관리
# ===============================
def load_config():
    """설정 파일 로드"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  설정 파일 로드 실패: {e}")
    return None

def save_config(config):
    """설정 파일 저장"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 설정 저장 실패: {e}")
        return False

def create_default_config():
    """기본 설정 파일 생성"""
    config = {
        "openweather_api_key": "",
        "last_station": 0,
        "stations": DEFAULT_STATIONS
    }
    
    if save_config(config):
        print("✅ 기본 config.json 생성 완료")
        return config
    return None

def setup_config():
    """설정 초기화 또는 로드"""
    config = load_config()
    
    if config is None:
        print("\n" + "="*60)
        print("📻 WR-Radio 첫 실행 설정")
        print("="*60)
        print()
        print("config.json 파일이 없습니다. 기본 설정을 생성합니다.")
        print()
        
        config = create_default_config()
        if config is None:
            print("❌ 설정 파일 생성 실패")
            return None
        
        print()
        print("🌤️  OpenWeatherMap API 키 설정 (선택사항)")
        print("-" * 60)
        print("무료 API 키 발급: https://openweathermap.org/appid")
        print("(엔터만 누르면 날씨 기능 비활성화)")
        print()
        
        api_key = input("API 키 입력: ").strip()
        
        if api_key:
            config['openweather_api_key'] = api_key
            save_config(config)
            print("✅ API 키 저장 완료!")
        else:
            print("⚠️  날씨 기능이 비활성화됩니다.")
        
        print()
        print("="*60)
        print("💡 스테이션 목록 수정: nano ~/wr-radio/wr-radio/config.json")
        print("="*60)
        print()
    
    # 검증
    if 'stations' not in config or not config['stations']:
        print("⚠️  스테이션 목록이 비어있습니다. 기본 목록 사용")
        config['stations'] = DEFAULT_STATIONS
    
    # color를 tuple로 변환
    for station in config['stations']:
        if isinstance(station.get('color'), list):
            station['color'] = tuple(station['color'])
        elif 'color' not in station:
            station['color'] = (100, 200, 255)
    
    return config

def save_last_station(index):
    """마지막 스테이션 저장"""
    try:
        config = load_config()
        if config:
            config['last_station'] = index
            save_config(config)
            print("💾 저장 완료")
    except Exception as e:
        print(f"저장 실패: {e}")

def acquire_lock():
    """프로세스 잠금"""
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
    """프로세스 잠금 해제"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

# ===============================
# 날씨 정보
# ===============================
def fetch_weather_background(lat, lon, location_name):
    """백그라운드에서 날씨 가져오기"""
    if not ENABLE_WEATHER:
        return
    
    cache_key = f"{lat},{lon}"
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'lang': 'kr'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            temp = int(data['main']['temp'])
            
            icon_map = {
                '01': '☀️', '02': '🌤️', '03': '☁️', '04': '☁️',
                '09': '🌧️', '10': '🌦️', '11': '⛈️', '13': '🌨️', '50': '🌫️'
            }
            
            icon_code = data['weather'][0]['icon'][:2]
            icon = icon_map.get(icon_code, '🌤️')
            weather_text = f"{icon} {temp}°C"
            
            with weather_lock:
                weather_cache[cache_key] = (time.time(), weather_text)
            print(f"🌤️  날씨 업데이트: {location_name} - {weather_text}")
        else:
            print(f"⚠️  날씨 HTTP {response.status_code}: {location_name}")
            
    except Exception as e:
        print(f"⚠️  날씨 실패: {location_name} - {str(e)[:50]}")

def get_cached_weather(lat, lon):
    """캐시된 날씨 가져오기"""
    if not ENABLE_WEATHER:
        return ""
    
    cache_key = f"{lat},{lon}"
    with weather_lock:
        if cache_key in weather_cache:
            cached_time, cached_data = weather_cache[cache_key]
            return cached_data
    return ""

def should_update_weather(lat, lon):
    """날씨 업데이트 필요 여부"""
    if not ENABLE_WEATHER:
        return False
    
    cache_key = f"{lat},{lon}"
    with weather_lock:
        if cache_key not in weather_cache:
            return True
        cached_time, _ = weather_cache[cache_key]
        return (time.time() - cached_time) >= WEATHER_CACHE_TIME

def start_weather_update(station_index):
    """백그라운드 날씨 업데이트"""
    if not ENABLE_WEATHER:
        return
    
    station = radio_stations[station_index]
    if should_update_weather(station["lat"], station["lon"]):
        thread = threading.Thread(
            target=fetch_weather_background,
            args=(station["lat"], station["lon"], station["location"]),
            daemon=True
        )
        thread.start()

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
    
    # 백그라운드 날씨 업데이트
    start_weather_update(current_index)
    
    # 캐시된 날씨 가져오기
    weather = get_cached_weather(station["lat"], station["lon"])
    
    image = Image.new('RGB', (240, 240), (15, 15, 15))
    draw = ImageDraw.Draw(image)
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    
    # 상단 바 (스테이션 색상)
    draw.rectangle([0, 0, 239, 50], fill=station["color"])
    
    # 스테이션 이름
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
    
    # 위치 정보
    bbox = draw.textbbox((0, 0), station["location"], font=font_tiny)
    text_width = bbox[2] - bbox[0]
    x = (240 - text_width) // 2
    draw.text((x, 60), station["location"], font=font_tiny, fill=(150, 150, 150))
    
    # 날씨 정보
    if weather:
        bbox = draw.textbbox((0, 0), weather, font=font_small)
        text_width = bbox[2] - bbox[0]
        x = (240 - text_width) // 2
        draw.text((x, 80), weather, font=font_small, fill=(100, 200, 255))
        status_y = 110
    else:
        status_y = 90
    
    # 재생 상태
    status = "▶ PLAYING" if is_playing else "⏸ PAUSED"
    status_color = (100, 255, 100) if is_playing else (255, 100, 100)
    bbox = draw.textbbox((0, 0), status, font=font_medium)
    text_width = bbox[2] - bbox[0]
    x = (240 - text_width) // 2
    draw.text((x, status_y), status, font=font_medium, fill=status_color)
    
    # 음파 애니메이션
    if is_playing:
        center_y = status_y + 40
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
    draw.text((x, 190), station_num, font=font_medium, fill=(150, 150, 150))
    
    # 하단 안내
    draw.text((30, 215), "Turn to switch", font=font_small, fill=(100, 100, 100))
    
    display_image(image)

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
    
    display_radio_info(index)

# ===============================
# 메인
# ===============================
def main():
    global is_playing, OPENWEATHER_API_KEY, ENABLE_WEATHER, radio_stations, spi
    
    # 설정 로드
    config = setup_config()
    if config is None:
        print("❌ 설정 초기화 실패")
        return
    
    # 전역 변수 설정
    OPENWEATHER_API_KEY = config.get('openweather_api_key', '')
    ENABLE_WEATHER = bool(OPENWEATHER_API_KEY)
    radio_stations = config['stations']
    current_index = config.get('last_station', 0)
    
    if not (0 <= current_index < len(radio_stations)):
        current_index = 0
    
    if ENABLE_WEATHER:
        print(f"🌤️  날씨 기능 활성화")
    else:
        print(f"⚠️  날씨 기능 비활성화 (API 키 없음)")
    
    print(f"📻 스테이션 {len(radio_stations)}개 로드")
    
    acquire_lock()
    
    # SPI 초기화
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 8000000
    spi.mode = 0
    
    # GPIO 초기화
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(S1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(S2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    GPIO.setup(CS_PIN, GPIO.OUT)
    GPIO.setup(DC_PIN, GPIO.OUT)
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.setup(BL_PIN, GPIO.OUT)
    
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
                        current_index = (current_index - 1) % len(radio_stations)
                    else:
                        current_index = (current_index + 1) % len(radio_stations)

                    print(f"→ {radio_stations[current_index]['name']}")

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

            # 로터리 멈춘 후 LCD 업데이트
            if needs_save and (time.time() - last_change_time) >= LCD_UPDATE_DELAY:
                if not hasattr(main, 'lcd_updated') or not main.lcd_updated:
                    display_radio_info(current_index)
                    main.lcd_updated = True

            # 저장
            if needs_save and (time.time() - last_change_time) >= SAVE_DELAY_SEC:
                save_last_station(current_index)
                needs_save = False
                if hasattr(main, 'lcd_updated'):
                    main.lcd_updated = False

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
        if spi:
            spi.close()
        release_lock()

if __name__ == "__main__":
    main()
