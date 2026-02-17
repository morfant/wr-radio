import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class InputConfig:
    rotation_debounce_sec: float = 0.02
    play_switch_delay_sec: float = 0.40
    display_update_delay: float = 0.01
    mode_timeout_sec: float = 3.0
    save_delay_sec: float = 1.0

    short_press_min_sec: float = 0.05
    long_press_sec: float = 1.0


@dataclass
class ButtonState:
    press_start: float = 0.0
    long_press_fired: bool = False  # 누르는 중 brightness 진입 여부


def read_rotary(GPIO, pins, s1_last: int, now: float, last_rotation_time: float, cfg: InputConfig):
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
      - "enter_volume"      : 짧게 눌렀다 뗄 때
      - "enter_brightness"  : 누른 채로 long_press_sec 경과 시 (뗄 때가 아님)
      - "exit_mode"         : 모드 중 버튼 뗄 때
      - None
    """
    key = GPIO.input(pins["KEY"])

    event: Optional[str] = None

    # 누르는 순간
    if key == 0 and key_last == 1:
        btn.press_start = now
        btn.long_press_fired = False

    # 누르고 있는 중: long press 감지
    elif key == 0 and key_last == 0:
        if (
            not btn.long_press_fired
            and btn.press_start > 0
            and (now - btn.press_start) >= cfg.long_press_sec
        ):
            if state.current_mode == "normal":
                btn.long_press_fired = True
                event = "enter_brightness"

    # 뗄 때
    elif key == 1 and key_last == 0:
        press_dur = now - btn.press_start

        if btn.long_press_fired:
            # 길게 눌러서 brightness 진입한 경우 → 떼도 모드 유지
            pass
        elif state.current_mode != "normal":
            event = "exit_mode"
        elif press_dur >= cfg.short_press_min_sec:
            event = "enter_volume"

        btn.press_start = 0.0
        btn.long_press_fired = False

    return key, event
