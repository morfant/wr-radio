import json
import os
import socket
import subprocess
import threading
import time

import RPi.GPIO as GPIO

HEADPHONE_PIN = 23
AMP_STBY_PIN = 24
SPEAKER_MAX_VOLUME = 150

GPIO.setmode(GPIO.BCM)
GPIO.setup(HEADPHONE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(AMP_STBY_PIN, GPIO.OUT, initial=GPIO.HIGH)


def is_headphone_inserted() -> bool:
    return bool(GPIO.input(HEADPHONE_PIN))


def set_amp_power(enable: bool) -> None:
    GPIO.output(AMP_STBY_PIN, GPIO.HIGH if enable else GPIO.LOW)


def _can_connect(sock_path: str, timeout: float = 0.2) -> bool:
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


def _wait_for_sock(sock_path: str, timeout_sec: float = 8.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        if _can_connect(sock_path, timeout=0.2):
            return True
        time.sleep(0.05)
    return False


def mpv_cmd(state, payload: dict) -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(state.mpv_sock)
        s.send((json.dumps(payload) + "\n").encode("utf-8"))
        s.close()
        return True
    except Exception:
        return False


def _get_core_idle(state) -> bool:
    """core-idle 값 반환. True = 재생 안 됨. 실패 시 True 반환."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.3)
        s.connect(state.mpv_sock)
        s.send((json.dumps({"command": ["get_property", "core-idle"]}) + "\n").encode("utf-8"))
        resp = b""
        while True:
            chunk = s.recv(256)
            if not chunk:
                break
            resp += chunk
            if b"\n" in resp:
                break
        s.close()
        data = json.loads(resp.split(b"\n")[0])
        return bool(data.get("data", True))
    except Exception:
        return True


def _is_bt_sink_alive(state) -> bool:
    """현재 BT sink가 PulseAudio에 아직 등록되어 있는지 확인"""
    if not state.bt_sink:
        return False
    try:
        r = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            capture_output=True, text=True, timeout=3
        )
        return state.bt_sink in r.stdout
    except Exception:
        return False


def _audio_monitor_thread(state) -> None:
    last_hp = is_headphone_inserted()
    # BT 모드일 때는 앰프 끔
    if state.output_mode == "bluetooth":
        set_amp_power(False)
    else:
        set_amp_power(not last_hp)

    bt_check_interval = 3.0   # BT 연결 상태 체크 주기
    last_bt_check = 0.0

    while not state.shutting_down:
        now = time.time()

        # BT 모드에서는 헤드폰 감지 무시, 앰프 항상 OFF
        if state.output_mode == "bluetooth":
            set_amp_power(False)
            last_hp = is_headphone_inserted()

            # 주기적으로 BT sink 살아있는지 확인
            if (now - last_bt_check) >= bt_check_interval:
                last_bt_check = now
                if not _is_bt_sink_alive(state):
                    print("🔵 BT 장치 연결 끊김 감지 → 스피커 전환")
                    state.output_mode = "speaker"
                    state.bt_mac      = ""
                    state.bt_sink     = ""
                    hp = is_headphone_inserted()
                    set_amp_power(not hp)
                    last_hp = hp
                    restart_mpv(state)
                    if state.is_playing:
                        play_station(state, state.current_index)
        else:
            hp = is_headphone_inserted()
            if hp != last_hp:
                time.sleep(0.5)
                hp = is_headphone_inserted()
                if hp != last_hp:
                    set_amp_power(not hp)
                    last_hp = hp
                    print(f"🎧 헤드폰 {'삽입' if hp else '제거'} → 앰프 {'OFF' if hp else 'ON'}")

        if state.is_playing:
            idle = _get_core_idle(state)
            state.audio_playing = not idle
        else:
            state.audio_playing = False
        time.sleep(0.5)


def start_audio_monitor(state) -> threading.Thread:
    t = threading.Thread(target=_audio_monitor_thread, args=(state,), daemon=True)
    t.start()
    return t


def _build_mpv_cmd(state) -> list[str]:
    """현재 output_mode에 맞는 mpv 실행 명령 생성"""
    cmd = [
        "mpv",
        "--no-video",
        "--idle=yes",
        "--no-terminal",
        "--no-config",
        "--load-scripts=no",
        "--osc=no",
        "--input-default-bindings=no",
        "--input-ipc-server=" + state.mpv_sock,
        "--volume=50",
        "--cache=yes",
        "--cache-secs=0.3",
        "--demuxer-readahead-secs=0.3",
        "--network-timeout=3",
    ]

    if state.output_mode == "bluetooth" and state.bt_sink:
        # PulseAudio BT sink로 출력
        cmd.append(f"--audio-device=pulse/{state.bt_sink}")
        print(f"🔵 mpv 출력 장치: pulse/{state.bt_sink}")
    else:
        # 기본 ALSA (I2S DAC)
        print("🔊 mpv 출력 장치: ALSA 기본")

    return cmd


def ensure_mpv_running(state) -> bool:
    """mpv가 실행 중이면 그대로 반환. 아니면 현재 output_mode로 새로 시작."""
    if _can_connect(state.mpv_sock):
        return True

    try:
        if os.path.exists(state.mpv_sock):
            os.remove(state.mpv_sock)
    except Exception:
        pass

    cmd = _build_mpv_cmd(state)

    try:
        state.player_process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"❌ mpv 실행 실패: {e}")
        state.player_process = None
        return False

    if not _wait_for_sock(state.mpv_sock, timeout_sec=8.0):
        print("❌ mpv IPC 소켓 생성 실패")
        return False

    return True


def restart_mpv(state) -> bool:
    """
    mpv를 완전히 종료 후 현재 output_mode로 재시작.
    출력 장치 전환(BT ↔ 스피커) 시 호출.
    """
    print("🔄 mpv 재시작 중...")

    # 기존 프로세스 종료
    try:
        if state.player_process:
            state.player_process.terminate()
            state.player_process.wait(timeout=3)
    except Exception:
        pass

    try:
        if os.path.exists(state.mpv_sock):
            os.remove(state.mpv_sock)
    except Exception:
        pass

    state.player_process = None
    time.sleep(0.3)

    # 새 output_mode로 재시작
    ok = ensure_mpv_running(state)
    if ok:
        set_volume(state, state.current_volume)
        print("✅ mpv 재시작 완료")
    else:
        print("❌ mpv 재시작 실패")
    return ok


def stop_playback(state) -> None:
    if mpv_cmd(state, {"command": ["stop"]}):
        state.is_playing = False
        state.audio_playing = False
        print("⏹️  재생 중지")
    else:
        print("⚠️  stop 실패")


def play_station(state, index: int) -> None:
    st = state.radio_stations[index]
    print(f"\n🎵 재생: {st['name']}")
    state.audio_playing = False
    ok = mpv_cmd(state, {"command": ["loadfile", st["url"], "replace"]})
    state.is_playing = bool(ok)
    if not ok:
        print("❌ 재생 실패")


def set_volume(state, volume: int) -> int:
    volume = max(0, min(150, volume))
    state.current_volume = volume
    actual = min(volume, SPEAKER_MAX_VOLUME) if not is_headphone_inserted() else volume
    mpv_cmd(state, {"command": ["set_property", "volume", actual]})
    return volume


def shutdown_player(state) -> None:
    state.shutting_down = True
    state.audio_playing = False

    try:
        if state.player_process:
            state.player_process.terminate()
            state.player_process.wait(timeout=2)
    except Exception:
        pass

    try:
        if os.path.exists(state.mpv_sock):
            os.remove(state.mpv_sock)
    except Exception:
        pass

    try:
        GPIO.cleanup(HEADPHONE_PIN)
        GPIO.cleanup(AMP_STBY_PIN)
    except Exception:
        pass
