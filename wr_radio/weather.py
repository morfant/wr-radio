import threading
import time
from typing import Dict, Optional

import requests

WEATHER_CACHE_TIME = 600  # 10분
_weather_lock = threading.Lock()


def _cache_key(lat: float, lon: float) -> str:
    return f"{lat},{lon}"


def should_update_weather(state, lat: float, lon: float) -> bool:
    if not state.enable_weather:
        return False
    key = _cache_key(lat, lon)
    with _weather_lock:
        if key not in state.weather_cache:
            return True
        cached_time, _ = state.weather_cache[key]
        return (time.time() - cached_time) >= WEATHER_CACHE_TIME


def get_cached_weather(state, lat: float, lon: float) -> Optional[Dict[str, int]]:
    if not state.enable_weather:
        return None
    key = _cache_key(lat, lon)
    with _weather_lock:
        if key in state.weather_cache:
            _, data = state.weather_cache[key]
            return data
    return None


def _fetch_weather_background(state, lat: float, lon: float, location_name: str) -> None:
    if not state.enable_weather:
        return
    key = _cache_key(lat, lon)

    try:
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": state.openweather_api_key,
            "units": "metric",
            "lang": "kr",
        }
        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            temp = int(data["main"]["temp"])
            icon_code = data["weather"][0]["icon"][:2]
            weather_data = {"icon": icon_code, "temp": temp}

            with _weather_lock:
                state.weather_cache[key] = (time.time(), weather_data)
            print(f"🌤️  날씨 업데이트: {location_name} - {temp}°C")
        else:
            print(f"⚠️  날씨 HTTP {response.status_code}: {location_name}")

    except Exception as e:
        print(f"⚠️  날씨 실패: {location_name} - {str(e)[:50]}")


def start_weather_update(state, station_index: int) -> None:
    if not state.enable_weather:
        return
    st = state.radio_stations[station_index]
    lat, lon = st["lat"], st["lon"]
    if should_update_weather(state, lat, lon):
        th = threading.Thread(
            target=_fetch_weather_background,
            args=(state, lat, lon, st["location"]),
            daemon=True,
        )
        th.start()
