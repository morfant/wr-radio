#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Optional


@dataclass
class InputConfig:
    rotation_debounce_sec: float = 0.02
    play_switch_delay_sec: float = 0.40
    display_update_delay: float = 0.01
    mode_timeout_sec: float = 3.0
    save_delay_sec: float = 1.0
    short_press_min_sec: float = 0.05
    long_press_sec: float = 1.0         # 시스템 메뉴 진입


@dataclass
class ButtonState:
    press_start: float = 0.0
    long_press_fired: bool = False      # 시스템 메뉴 진입 여부


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
      - "enter_volume"      : 짧게 눌렀다 뗄 때 (normal 모드)
      - "enter_system_menu" : long_press_sec 누르는 중 (normal 모드)
      - "menu_select"       : system_menu 모드에서 짧게 눌렀다 뗄 때
      - "exit_mode"         : volume 모드에서 버튼 뗄 때
      - None
    """
    key = GPIO.input(pins["KEY"])
    event: Optional[str] = None

    # 누르는 순간
    if key == 0 and key_last == 1:
        btn.press_start = now
        btn.long_press_fired = False

    # 누르고 있는 중
    elif key == 0 and key_last == 0:
        hold_sec = now - btn.press_start if btn.press_start > 0 else 0.0

        if state.current_mode == "normal":
            if (
                not btn.long_press_fired
                and hold_sec >= cfg.long_press_sec
            ):
                btn.long_press_fired = True
                event = "enter_system_menu"

    # 뗄 때
    elif key == 1 and key_last == 0:
        press_dur = now - btn.press_start if btn.press_start > 0 else 0.0

        if btn.long_press_fired:
            # 길게 눌러서 system_menu 진입 직후 뗀 경우 → 무시
            pass
        elif state.current_mode == "system_menu":
            if press_dur >= cfg.short_press_min_sec:
                event = "menu_select"
        elif state.current_mode != "normal":
            event = "exit_mode"
        elif press_dur >= cfg.short_press_min_sec:
            event = "enter_volume"

        btn.press_start = 0.0
        btn.long_press_fired = False

    return key, event
