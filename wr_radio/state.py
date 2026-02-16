from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class AppState:
    # config / stations
    radio_stations: List[Dict[str, Any]] = field(default_factory=list)
    current_index: int = 0

    # runtime flags
    is_playing: bool = False
    current_mode: str = "normal"  # 'normal', 'volume', 'brightness'

    # mode values
    current_volume: int = 50
    current_brightness: int = 100
    mode_enter_time: float = 0.0

    # weather
    enable_weather: bool = False
    openweather_api_key: str = ""
    weather_cache: Dict[str, Tuple[float, Dict[str, int]]] = field(default_factory=dict)  # key -> (ts, {'icon': '01', 'temp': 15})

    # display cache
    last_displayed_index: int = -1
    last_displayed_playing: Optional[bool] = None
    animation_frame: int = 0
    animation_active: bool = False
    animation_start_time: float = 0.0

    # save
    needs_save: bool = False
    last_change_time: float = 0.0

    # pending actions
    pending_play: bool = False
    last_station_change_time: float = 0.0

    # input bookkeeping
    last_input_time: float = 0.0
    last_updated_index: int = -1

    # handles
    spi: Any = None
    pwm_backlight: Any = None
    player_process: Any = None

    # mpv socket path
    mpv_sock: str = "/tmp/wr_mpv.sock"
