import json
import math
import os
from typing import Any, Dict, List, Optional

CONFIG_FILE = "/home/wr-radio/wr-radio/config.json"

# 주요 타임존 대표 좌표 (위도, 경도, 타임존)
TIMEZONE_LOOKUP = [
    # 아시아
    (37.5, 127.0, "Asia/Seoul"),
    (35.7, 139.7, "Asia/Tokyo"),
    (39.9, 116.4, "Asia/Shanghai"),
    (22.3, 114.2, "Asia/Hong_Kong"),
    (1.3, 103.8, "Asia/Singapore"),
    (13.7, 100.5, "Asia/Bangkok"),
    (28.6, 77.2, "Asia/Kolkata"),
    (25.0, 121.5, "Asia/Taipei"),
    (31.2, 121.5, "Asia/Shanghai"),
    (23.1, 113.3, "Asia/Hong_Kong"),
    
    # 유럽
    (51.5, -0.1, "Europe/London"),
    (48.9, 2.3, "Europe/Paris"),
    (52.5, 13.4, "Europe/Berlin"),
    (41.9, 12.5, "Europe/Rome"),
    (40.4, -3.7, "Europe/Madrid"),
    (59.3, 18.1, "Europe/Stockholm"),
    (55.8, 37.6, "Europe/Moscow"),
    (50.1, 8.7, "Europe/Berlin"),
    (45.5, 9.2, "Europe/Rome"),
    
    # 북미
    (40.7, -74.0, "America/New_York"),
    (41.9, -87.6, "America/Chicago"),
    (39.7, -105.0, "America/Denver"),
    (34.0, -118.2, "America/Los_Angeles"),
    (37.8, -122.4, "America/Los_Angeles"),
    (49.3, -123.1, "America/Vancouver"),
    (43.7, -79.4, "America/Toronto"),
    (42.4, -71.1, "America/New_York"),
    (33.4, -112.1, "America/Phoenix"),
    (29.8, -95.4, "America/Chicago"),
    
    # 남미
    (-23.5, -46.6, "America/Sao_Paulo"),
    (-34.6, -58.4, "America/Argentina/Buenos_Aires"),
    (19.4, -99.1, "America/Mexico_City"),
    (-12.0, -77.0, "America/Lima"),
    (4.7, -74.1, "America/Bogota"),
    
    # 오세아니아
    (-33.9, 151.2, "Australia/Sydney"),
    (-37.8, 144.9, "Australia/Melbourne"),
    (-41.3, 174.8, "Pacific/Auckland"),
    (-27.5, 153.0, "Australia/Brisbane"),
    
    # 아프리카
    (-26.2, 28.0, "Africa/Johannesburg"),
    (30.0, 31.2, "Africa/Cairo"),
    (6.5, 3.4, "Africa/Lagos"),
    (-1.3, 36.8, "Africa/Nairobi"),
]

DEFAULT_STATIONS: List[Dict[str, Any]] = [
    {
        "name": "Jeju Georo",
        "url": "https://locus.creacast.com:9443/jeju_georo.mp3",
        "location": "Jeju, South Korea",
        "lat": 33.509306,
        "lon": 126.562000,
        "color": [100, 200, 255],
    },
    {
        "name": "London Stave Hill",
        "url": "https://locus.creacast.com:9443/london_stave_hill.mp3",
        "location": "London, UK",
        "lat": 51.502111,
        "lon": -0.040278,
        "color": [255, 100, 100],
    },
    {
        "name": "New York Wave Farm",
        "url": "https://locus.creacast.com:9443/acra_wave_farm.mp3",
        "location": "Acra, New York",
        "lat": 42.319111,
        "lon": -74.076611,
        "color": [255, 200, 50],
    },
    {
        "name": "Jasper Ridge",
        "url": "https://locus.creacast.com:9443/jasper_ridge_birdcast.mp3",
        "location": "California, USA",
        "lat": 37.403611,
        "lon": -122.238000,
        "color": [100, 255, 100],
    },
    {
        "name": "Mt. Fuji Forest",
        "url": "http://mp3s.nc.u-tokyo.ac.jp/Fuji_CyberForest.mp3",
        "location": "Yamanashi, Japan",
        "lat": 35.4088,
        "lon": 138.86,
        "color": [200, 100, 255],
    },
]


def find_timezone(lat: float, lon: float) -> str:
    """위경도로 가장 가까운 타임존 찾기"""
    min_dist = float('inf')
    best_tz = "UTC"
    
    for tz_lat, tz_lon, tz_name in TIMEZONE_LOOKUP:
        # 간단한 유클리드 거리 (정확하진 않지만 충분함)
        dist = math.sqrt((lat - tz_lat)**2 + (lon - tz_lon)**2)
        if dist < min_dist:
            min_dist = dist
            best_tz = tz_name
    
    return best_tz


def load_config() -> Optional[Dict[str, Any]]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  설정 파일 로드 실패: {e}")
    return None


def save_config(config: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 설정 저장 실패: {e}")
        return False


def create_default_config() -> Optional[Dict[str, Any]]:
    config: Dict[str, Any] = {
        "openweather_api_key": "",
        "last_station": 0,
        "last_volume": 50,
        "last_brightness": 100,
        "stations": DEFAULT_STATIONS,
    }
    if save_config(config):
        print("✅ 기본 config.json 생성 완료")
        return config
    return None


def setup_config_interactive() -> Optional[Dict[str, Any]]:
    """
    config.json이 없을 때만 1회 실행되는 인터랙티브 설정.
    (이미 존재하면 그냥 로드 결과를 반환)
    """
    config = load_config()

    if config is None:
        print("\n" + "=" * 60)
        print("📻 WR-Radio 첫 실행 설정")
        print("=" * 60)
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
            config["openweather_api_key"] = api_key
            save_config(config)
            print("✅ API 키 저장 완료!")
        else:
            print("⚠️  날씨 기능이 비활성화됩니다.")

        print()
        print("=" * 60)
        print("💡 스테이션 목록 수정: nano ~/wr-radio/wr-radio/config.json")
        print("=" * 60)
        print()

    # 검증/정규화
    if "stations" not in config or not config["stations"]:
        print("⚠️  스테이션 목록이 비어있습니다. 기본 목록 사용")
        config["stations"] = DEFAULT_STATIONS

    for st in config["stations"]:
        if isinstance(st.get("color"), list):
            st["color"] = tuple(st["color"])
        elif "color" not in st:
            st["color"] = (100, 200, 255)
        
        # timezone 자동 찾기
        if "timezone" not in st or not st["timezone"]:
            st["timezone"] = find_timezone(st["lat"], st["lon"])
            print(f"🌍 {st['name']}: {st['timezone']}")

    return config


def save_settings(index: int, volume: int, brightness: int) -> None:
    try:
        config = load_config()
        if config:
            config["last_station"] = index
            config["last_volume"] = volume
            config["last_brightness"] = brightness
            save_config(config)
            print(f"💾 저장 완료 (스테이션:{index+1}, 볼륨:{volume}%, 밝기:{brightness}%)")
    except Exception as e:
        print(f"저장 실패: {e}")
