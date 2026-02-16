import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class InputConfig:
    rotation_debounce_sec: float = 0.02
    play_switch_delay_sec: float = 0.40
    display_update_delay: float = 0.01
    mode_timeout_sec: float = 3.0
    save_delay_sec: float = 1.0

    # 버튼 동작
    short_press_min_sec: float = 0.05
    long_press_sec: float = 1.0  # (현재 네 코드 기준)
    # (원하면 “누르고 있는 중 3초” 같은 것도 여기로 확장 가능)


@dataclass
class ButtonState:
    press_start: float = 0.0


def read_rotary(GPIO, pins, s1_last: int, now: float, last_rotation_time: float, cfg: InputConfig):
    """
    S1 falling edge 기반. (네 코드 방식)
    반환: (s1_state, direction or 0, new_last_rotation_time)
    direction: -1 or +1 or 0
    """
    s1 = GPIO.input(pins["S1"])
    s2 = GPIO.input(pins["S2"])

    direction = 0
    if s1 == 0 and s1_last == 1:
        if now - last_rotation_time > cfg.rotation_debounce_sec:
            direction = -1 if s2 == 1 else 1
            last_rotation_time = now

    return s1, direction, last_rotation_time


def handle_button(
    GPIO,
    pins,
    state,
    now: float,
    key_last: int,
    btn: ButtonState,
    cfg: InputConfig,
):
    """
    반환: (new_key_last, event_str or None)
    event_str:
      - "enter_volume"
      - "enter_brightness"
      - "exit_mode"
      - None
    """
    key = GPIO.input(pins["KEY"])

    event: Optional[str] = None

    if key == 0 and key_last == 1:
        btn.press_start = now

    elif key == 1 and key_last == 0:
        press_dur = now - btn.press_start

        if state.current_mode != "normal":
            event = "exit_mode"
        else:
            if press_dur >= cfg.long_press_sec:
                event = "enter_brightness"
            elif press_dur >= cfg.short_press_min_sec:
                event = "enter_volume"

        btn.press_start = 0.0

    return key, event
