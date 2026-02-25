#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import ImageDraw
import os
import sys
import time

import RPi.GPIO as GPIO
import spidev
from PIL import Image

from .state import AppState
from .config import setup_config_interactive, save_settings
from . import player
from . import weather
from . import display
from .input import InputConfig, ButtonState, read_rotary, handle_button
from .battery import BatteryMonitor

LOCK_FILE = "/tmp/wr_radio.lock"

# BCM pins
PIN_S1 = 17
PIN_S2 = 27
PIN_KEY = 22

PIN_CS = 26
PIN_DC = 13
PIN_RST = 6
PIN_BL = 5


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


def pwm_safe_close(state: AppState):
    """PWM 객체 stop + del + None (종료시 __del__ 예외 방지 목적)"""
    try:
        if state.pwm_backlight is not None:
            try:
                state.pwm_backlight.stop()
            except Exception:
                pass
            try:
                del state.pwm_backlight
            except Exception:
                pass
    finally:
        state.pwm_backlight = None


def set_brightness(state: AppState, level: int, bl_pin: int) -> int:
    level = max(10, min(100, level))
    if state.pwm_backlight is None:
        state.pwm_backlight = GPIO.PWM(bl_pin, 1000)
        state.pwm_backlight.start(level)
        state.current_brightness = level
        return level

    try:
        state.pwm_backlight.ChangeDutyCycle(level)
        state.current_brightness = level
        return level
    except Exception:
        pwm_safe_close(state)
        state.pwm_backlight = GPIO.PWM(bl_pin, 1000)
        state.pwm_backlight.start(level)
        state.current_brightness = level
        return level


def main():
    cfg = setup_config_interactive()
    if cfg is None:
        print("❌ 설정 초기화 실패")
        return

    state = AppState()
    state.openweather_api_key = cfg.get("openweather_api_key", "")
    state.enable_weather = bool(state.openweather_api_key)
    state.radio_stations = cfg["stations"]
    state.current_index = cfg.get("last_station", 0)
    if not (0 <= state.current_index < len(state.radio_stations)):
        state.current_index = 0

    # 저장된 볼륨/밝기 로드
    state.current_volume = cfg.get("last_volume", 50)
    state.current_brightness = cfg.get("last_brightness", 100)
    print(f"🔊 볼륨: {state.current_volume}%  💡 밝기: {state.current_brightness}%")

    print("🌤️  날씨 기능 " + ("활성화" if state.enable_weather else "비활성화 (API 키 없음)"))
    print(f"📻 스테이션 {len(state.radio_stations)}개 로드")

    acquire_lock()

    # SPI init
    state.spi = spidev.SpiDev()
    state.spi.open(0, 0)
    state.spi.max_speed_hz = 64_000_000
    state.spi.mode = 0

    # GPIO init
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(PIN_S1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_S2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_KEY, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.setup(PIN_CS, GPIO.OUT)
    GPIO.setup(PIN_DC, GPIO.OUT)
    GPIO.setup(PIN_RST, GPIO.OUT)
    GPIO.setup(PIN_BL, GPIO.OUT)

    pins = {
        "S1": PIN_S1,
        "S2": PIN_S2,
        "KEY": PIN_KEY,
        "CS": PIN_CS,
        "DC": PIN_DC,
        "RST": PIN_RST,
        "BL": PIN_BL,
    }

    # LCD init
    print("LCD 초기화 중...")
    display.init_display(GPIO, {"CS": PIN_CS, "DC": PIN_DC, "RST": PIN_RST}, state, rotation=90)

    # PWM init (저장된 밝기값 적용)
    pwm_safe_close(state)
    try:
        state.pwm_backlight = GPIO.PWM(PIN_BL, 1000)
        state.pwm_backlight.start(state.current_brightness)
        print(f"백라이트 초기화 완료 ({state.current_brightness}%)")
    except Exception as e:
        print(f"백라이트 초기화 실패: {e}")
        state.pwm_backlight = None

    # clear screen
    clear_image = Image.new("RGB", (240, 240), (0, 0, 0))
    display.display_image(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, clear_image)
    print("화면 클리어 완료")

    # mpv init
    if not player.ensure_mpv_running(state):
        print("mpv를 시작할 수 없어 종료합니다.")
        try:
            pwm_safe_close(state)
        except Exception:
            pass
        try:
            GPIO.cleanup()
        except Exception:
            pass
        release_lock()
        return

    # 저장된 볼륨 적용
    player.set_volume(state, state.current_volume)

    # 오디오 모니터링 스레드 시작
    player.start_audio_monitor(state)
    print("🎧 오디오 모니터 시작")

    # 배터리 모니터 시작
    bat_mon = BatteryMonitor()
    if bat_mon.start():
        state.battery_monitor = bat_mon
    else:
        print("⚠️  배터리 모니터 없이 진행")
        state.battery_monitor = None

    # initial render
    wd = weather.get_cached_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"])
    display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=True)

    # auto play
    player.play_station(state, state.current_index)
    state.is_playing = True

    # 초기 날씨 요청
    weather.start_weather_update(state, state.current_index)

    # input loop vars
    input_cfg = InputConfig(
        rotation_debounce_sec=0.02,
        play_switch_delay_sec=0.40,
        display_update_delay=0.01,
        mode_timeout_sec=3.0,
        save_delay_sec=1.0,
        short_press_min_sec=0.05,
        long_press_sec=1.0,
    )
    btn_state = ButtonState()

    s1_last = GPIO.input(PIN_S1)
    key_last = GPIO.input(PIN_KEY)
    last_rotation_time = 0.0
    last_animation_update = 0.0
    last_battery_update = 0.0
    last_weather_check = 0.0

    print("=" * 50)
    print("📻 WR-Radio (Modular)")
    print("=" * 50)
    print("로터리: 방송국 선택")
    print("버튼 짧게: 볼륨 조절 모드")
    print("버튼 길게: 밝기 조절 모드")
    print("모드에서 버튼: 일반 모드 복귀")
    print("Ctrl+C: 종료")
    print("=" * 50)

    try:
        while True:
            now = time.time()

            # mode timeout auto return
            if state.current_mode != "normal" and (now - state.mode_enter_time) >= input_cfg.mode_timeout_sec:
                state.current_mode = "normal"
                print("→ 일반 모드 (자동)")
                wd = weather.get_cached_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"])
                display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=True)

            # rotary
            s1_last, direction, last_rotation_time = read_rotary(
                GPIO, pins, s1_last, now, last_rotation_time, input_cfg
            )
            if direction != 0:
                if state.current_mode == "normal":
                    state.current_index = (state.current_index + direction) % len(state.radio_stations)
                    print(f"→ {state.radio_stations[state.current_index]['name']}")
                    state.last_input_time = now
                    state.needs_save = True
                    state.last_change_time = now
                    state.pending_play = True
                    state.last_station_change_time = now
                    state.last_displayed_weather = None
                elif state.current_mode == "volume":
                    player.set_volume(state, state.current_volume + direction * 5)
                    state.needs_save = True
                    state.last_change_time = now
                    state.mode_enter_time = now
                    display.display_mode_indicator(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, "volume", state.current_volume)
                elif state.current_mode == "brightness":
                    set_brightness(state, state.current_brightness + direction * 10, PIN_BL)
                    state.needs_save = True
                    state.last_change_time = now
                    state.mode_enter_time = now
                    display.display_mode_indicator(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, "brightness", state.current_brightness)

            # button events
            key_last, ev = handle_button(GPIO, pins, state, now, key_last, btn_state, input_cfg)
            if ev == "exit_mode":
                state.current_mode = "normal"
                print("→ 일반 모드")
                wd = weather.get_cached_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"])
                display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=True)

            elif ev == "enter_brightness":
                state.current_mode = "brightness"
                state.mode_enter_time = now
                print("💡 밝기 조절 모드")
                display.display_mode_indicator(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, "brightness", state.current_brightness)

            elif ev == "enter_volume":
                state.current_mode = "volume"
                state.mode_enter_time = now
                print("🔊 볼륨 조절 모드")
                display.display_mode_indicator(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, "volume", state.current_volume)

            # display update after input settled (normal mode)
            if state.current_mode == "normal":
                if state.last_input_time > 0 and state.current_index != state.last_updated_index:
                    if (now - state.last_input_time) >= input_cfg.display_update_delay:
                        if weather.should_update_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"]):
                            weather.start_weather_update(state, state.current_index)
                        wd = weather.get_cached_weather(state, state.radio_stations[state.current_index]["lat"], state.radio_stations[state.current_index]["lon"])
                        display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=False)
                        state.last_updated_index = state.current_index

            # play switch after rotary stop
            if state.pending_play and (now - state.last_station_change_time) >= input_cfg.play_switch_delay_sec:
                player.play_station(state, state.current_index)
                state.pending_play = False
                # 부하 변동 → 배터리 샘플링 일시 정지
                if state.battery_monitor:
                    state.battery_monitor.pause_sampling()
                # 채널 변경 시 애니메이션 영역 즉시 지우기
                img = Image.new("RGB", (240, 240), (0, 0, 0))
                display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                state.animation_frame = 0
                state.animation_cleared = True

            # 애니메이션: audio_playing 플래그 기반 (normal 모드에서만)
            if state.is_playing and state.current_mode == "normal":
                if state.audio_playing:
                    # 실제 소리 나는 중 → 사인파 애니메이션 (볼륨 기반 진폭)
                    state.animation_cleared = False
                    if (now - last_animation_update) >= 0.2:
                        img = Image.new("RGB", (240, 240), (0, 0, 0))
                        draw = ImageDraw.Draw(img)
                        display.draw_sine_wave_animation(draw, state.animation_frame, state.current_volume)
                        state.animation_frame = (state.animation_frame + 1) % 100
                        display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                        last_animation_update = now
                else:
                    # 재생 명령 보냈지만 아직 소리 안 남 → Loading
                    state.animation_cleared = False
                    if (now - last_animation_update) >= 0.2:
                        img = Image.new("RGB", (240, 240), (0, 0, 0))
                        draw = ImageDraw.Draw(img)
                        display.draw_loading_indicator(draw, state.animation_frame)
                        state.animation_frame = (state.animation_frame + 1) % 100
                        display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                        last_animation_update = now

            elif not state.is_playing and not state.animation_cleared:
                # 재생 중지 → 영역 지우기
                img = Image.new("RGB", (240, 240), (0, 0, 0))
                display.display_image_region(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, img, 0, 125, 239, 165)
                state.animation_frame = 0
                state.animation_cleared = True

            # 배터리 상태 주기적 업데이트 (normal 모드에서만)
            # 저전력 시 1초 간격 (점멸), 그 외 30초 간격
            if state.current_mode == "normal" and state.battery_monitor is not None:
                bat_interval = 1.0 if state.battery_monitor.is_low else 30.0
                if (now - last_battery_update) >= bat_interval:
                    display.display_battery_only(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state)
                    last_battery_update = now

            # 날씨 데이터 도착 시 화면 갱신 (2초마다 체크)
            if state.current_mode == "normal" and (now - last_weather_check) >= 2.0:
                last_weather_check = now
                st = state.radio_stations[state.current_index]
                wd = weather.get_cached_weather(state, st["lat"], st["lon"])
                if wd and state.last_displayed_weather != wd:
                    display.display_radio_info(GPIO, {"CS": PIN_CS, "DC": PIN_DC}, state, weather_data=wd, force_full=True)
                    state.last_displayed_weather = wd

            # save (station, volume, brightness 통합)
            if state.needs_save and (now - state.last_change_time) >= input_cfg.save_delay_sec:
                save_settings(state.current_index, state.current_volume, state.current_brightness)
                state.needs_save = False

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n프로그램 종료")
        if state.needs_save:
            save_settings(state.current_index, state.current_volume, state.current_brightness)
        try:
            player.stop_playback(state)
        except Exception:
            pass

    finally:
        print("\n정리 중...")

        player.shutdown_player(state)

        if state.battery_monitor:
            state.battery_monitor.stop()

        try:
            pwm_safe_close(state)
        except Exception:
            pass

        try:
            GPIO.cleanup()
        except Exception:
            pass

        try:
            if state.spi:
                state.spi.close()
        except Exception:
            pass

        release_lock()
        print("종료 완료")


if __name__ == "__main__":
    main()
