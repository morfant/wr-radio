import json
import os
from typing import Any, Dict, List, Optional

CONFIG_FILE = "/home/wr-radio/wr-radio/config.json"

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

    return config


def save_last_station(index: int) -> None:
    try:
        config = load_config()
        if config:
            config["last_station"] = index
            save_config(config)
            print("💾 저장 완료")
    except Exception as e:
        print(f"저장 실패: {e}")
