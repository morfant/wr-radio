import json
import os
import socket
import subprocess
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
        print("⏹️  재생 중지")
    else:
        print("⚠️  stop 실패")


def play_station(state, index: int) -> None:
    st = state.radio_stations[index]
    print(f"\n🎵 재생: {st['name']}")
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
    # mpv 종료
    try:
        if state.player_process:
            state.player_process.terminate()
            state.player_process.wait(timeout=2)
    except Exception:
        pass

    # 소켓 정리
    try:
        if os.path.exists(state.mpv_sock):
            os.remove(state.mpv_sock)
    except Exception:
        pass
