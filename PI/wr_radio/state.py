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
    current_mode: str = "normal"  # 'normal', 'volume', 'brightness', 'system_menu'

    # mode values
    current_volume: int = 50
    current_brightness: int = 100
    mode_enter_time: float = 0.0

    # weather
    enable_weather: bool = False
    openweather_api_key: str = ""
    weather_cache: Dict[str, Tuple[float, Dict[str, int]]] = field(default_factory=dict)

    # display cache
    last_displayed_index: int = -1
    last_displayed_playing: Optional[bool] = None
    animation_frame: int = 0
    animation_cleared: bool = False

    # audio monitoring
    audio_playing: bool = False
    shutting_down: bool = False

    # battery
    battery_monitor: Any = None
    last_battery_percent: int = -1

    # weather display
    last_displayed_weather: Any = None

    # save
    needs_save: bool = False
    last_change_time: float = 0.0

    # pending actions
    pending_play: bool = False
    last_station_change_time: float = 0.0

    # 웹 관리에서 스테이션 목록이 바뀌면 True. 메인 루프가 안전한 시점에 reload 후 클리어.
    stations_dirty: bool = False

    # input bookkeeping
    last_input_time: float = 0.0
    last_updated_index: int = -1

    # handles
    spi: Any = None
    pwm_backlight: Any = None
    player_process: Any = None

    # mpv socket path
    mpv_sock: str = "/tmp/wr_mpv.sock"

    # ── Bluetooth ──────────────────────────────────────────
    # 현재 출력 모드: "speaker" | "bluetooth"
    output_mode: str = "speaker"
    # 연결된 BT 장치 MAC (연결 중일 때만 값 있음)
    bt_mac: str = ""
    # PulseAudio BT sink 이름 (연결 중일 때만 값 있음)
    bt_sink: str = ""
