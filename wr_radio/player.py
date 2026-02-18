import json
import os
import socket
import subprocess
import threading
import time


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
    """core-idle 값 반환. True = 재생 안 됨, False = 재생 중. 실패 시 True 반환."""
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


def _audio_monitor_thread(state) -> None:
    """폴링 스레드: 0.5초마다 core-idle 확인 후 state.audio_playing 세팅."""
    while not state.shutting_down:
        if state.is_playing:
            idle = _get_core_idle(state)
            state.audio_playing = not idle
            print(f"[Monitor] core-idle={idle}, audio_playing={state.audio_playing}") 
        else:
            state.audio_playing = False
        time.sleep(0.5)


def start_audio_monitor(state) -> threading.Thread:
    t = threading.Thread(target=_audio_monitor_thread, args=(state,), daemon=True)
    t.start()
    return t


def ensure_mpv_running(state) -> bool:
    if _can_connect(state.mpv_sock):
        return True

    try:
        if os.path.exists(state.mpv_sock):
            os.remove(state.mpv_sock)
    except Exception:
        pass

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
        "--ao=null",  # ← 이 줄 추가: 오디오 출력 없이 재생만 함
        "--cache=yes",
        "--cache-secs=0.3",
        "--demuxer-readahead-secs=0.3",
        "--network-timeout=3",
    ]

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
    # 채널 변경 시 audio_playing 즉시 False로
    state.audio_playing = False
    ok = mpv_cmd(state, {"command": ["loadfile", st["url"], "replace"]})
    state.is_playing = bool(ok)
    if not ok:
        print("❌ 재생 실패")


def set_volume(state, volume: int) -> int:
    volume = max(0, min(100, volume))
    mpv_cmd(state, {"command": ["set_property", "volume", volume]})
    state.current_volume = volume
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
