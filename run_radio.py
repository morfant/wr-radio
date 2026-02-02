#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import time
import json
import os
import subprocess
import socket

# ===============================
# GPIO 핀 번호 설정 (BCM)
# ===============================
S1 = 17
S2 = 22
KEY = 23

# ===============================
# 설정 파일
# ===============================
CONFIG_FILE = "/home/wr-radio/wr-radio/last_station.json"

radio_stations = [
    {"name": "Jeju Georo",        "url": "https://locus.creacast.com:9443/jeju_georo.mp3"},
    {"name": "London stave hill", "url": "https://locus.creacast.com:9443/london_stave_hill.mp3"},
    {"name": "Wicken Fen",        "url": "https://locus.creacast.com:9443/wicken_wicken_fen.mp3"},
    {"name": "Newyork wave-farm", "url": "https://locus.creacast.com:9443/acra_wave_farm.mp3"},
    {"name": "Marseille",         "url": "https://locus.creacast.com:9443/marseille_frioul.mp3"},
]

# ===============================
# mpv IPC 설정
# ===============================
MPV_SOCK = "/tmp/wr_mpv.sock"
player_process = None

# 재생 상태
is_playing = False

# ===============================
# 튜닝 파라미터 (취향/환경 따라 조절)
# ===============================
ROTATION_DEBOUNCE_SEC = 0.10   # 엔코더 디바운스 (너무 민감하면 올려)
PLAY_SWITCH_DELAY_SEC = 0.40  # 마지막 회전 후 이 시간 멈추면 재생 전환
SAVE_DELAY_SEC = 5.0          # 마지막 변경 후 이 시간 멈추면 last_station 저장

# ===============================
# 설정 로드/저장
# ===============================
def load_last_station():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                index = int(data.get('last_index', 0))
                if 0 <= index < len(radio_stations):
                    return index
        except Exception:
            pass
    return 0

def save_last_station(index):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'last_index': index}, f)
        print("💾 저장 완료")
    except Exception as e:
        print(f"저장 실패: {e}")

# ===============================
# mpv IPC 유틸
# ===============================
def _wait_for_mpv_sock(timeout_sec=8.0):
    """mpv IPC 소켓이 '실제로 연결 가능'해질 때까지 대기"""
    start = time.time()
    while time.time() - start < timeout_sec:
        if os.path.exists(MPV_SOCK):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.2)
                s.connect(MPV_SOCK)
                s.close()
                return True
            except Exception:
                pass
        time.sleep(0.05)
    return False


def mpv_cmd(payload):
    """mpv IPC로 JSON 명령 전송"""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(MPV_SOCK)
        s.send((json.dumps(payload) + "\n").encode("utf-8"))
        s.close()
        return True
    except Exception:
        return False

def ensure_mpv_running():
    """mpv를 한 번만 실행해 상주시킴"""
    global player_process

    # 기존 소켓 정리(비정상 종료 후 남아있을 수 있음)
    try:
        if os.path.exists(MPV_SOCK):
            os.remove(MPV_SOCK)
    except Exception:
        pass

    log_path = "/tmp/mpv_ipc.log"
    logf = open(log_path, "w")
    
    # mpv 실행 (idle=yes: 재생 없어도 살아있음)
    # 버퍼 줄이기 옵션 포함 (끊김 생기면 cache-secs 등을 올리면 됨)
    cmd = [
        "mpv",
        "--no-video",
        "--idle=yes",
        "--no-terminal",

        "--no-config",            # 사용자 설정(~/.config/mpv) 무시 (속도/예측성↑)
        "--load-scripts=no",      # lua 스크립트(osc 등) 로딩 끄기
        "--osc=no",               # 화면 컨트롤 끄기 (혹시 켜져있다면)
        "--input-default-bindings=no",  # 기본 키바인딩 끄기 (불필요)

        "--input-ipc-server=" + MPV_SOCK,
        "--volume=50",

        "--cache=yes",
        "--cache-secs=0.3",
        "--demuxer-readahead-secs=0.3",
        "--network-timeout=3",
    ]

    try:
        player_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"❌ mpv 실행 실패: {e}")
        player_process = None
        return False

    ok = _wait_for_mpv_sock(timeout_sec=8.0)
    if not ok:
        rc = player_process.poll()
        logf.close()
        print("❌ mpv IPC 소켓 생성 실패(시간 초과)")

        if rc is not None:
            print(f"mpv가 즉시 종료됨. return code: {rc}")
        else:
            print("mpv는 살아있지만 소켓이 없음(옵션/경로 문제 가능)")

        # 로그 보여주기
        try:
            with open(log_path, "r") as f:
                print("----- /tmp/mpv_ipc.log -----")
                print(f.read().strip() or "(empty)")
                print("----------------------------")
        except Exception as e:
            print(f"로그 읽기 실패: {e}")

        return False

    logf.close()
    return True

def stop_playback():
    """재생 중지(프로세스는 살아있음)"""
    global is_playing
    if mpv_cmd({"command": ["stop"]}):
        is_playing = False
        print("⏹️  재생 중지")
    else:
        print("⚠️  stop 실패: mpv IPC 연결 불가")

def play_station(index):
    """해당 인덱스 스테이션 재생"""
    global is_playing

    station = radio_stations[index]
    print(f"\n🎵 재생 시작: {station['name']}")
    print(f"URL: {station['url']}")

    ok = mpv_cmd({"command": ["loadfile", station["url"], "replace"]})
    if ok:
        is_playing = True
    else:
        print("❌ 재생 실패: mpv IPC 연결 불가")
        is_playing = False

# ===============================
# UI 출력
# ===============================
def display_station(current_index):
    station = radio_stations[current_index]
    print(f"\n[{current_index + 1}/{len(radio_stations)}] {station['name']}")
    print(f"URL: {station['url']}")

# ===============================
# 메인
# ===============================
def main():
    global is_playing

    # GPIO 초기화
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(S1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(S2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    current_index = load_last_station()

    # mpv 상주 실행
    if not ensure_mpv_running():
        print("mpv를 시작할 수 없어 종료합니다.")
        GPIO.cleanup()
        return

    # 상태 변수
    s1LastState = GPIO.input(S1)
    keyLastState = GPIO.input(KEY)

    last_rotation_time = 0.0

    needs_save = False
    last_change_time = 0.0

    pending_play = False
    last_station_change_time = 0.0

    print("=" * 50)
    print("라디오 스테이션 선택")
    print("=" * 50)
    print("↑↓ 로터리: 방송국 선택")
    print("버튼: 재생/정지")
    print("Ctrl+C: 종료")
    print("=" * 50)

    if current_index > 0:
        print(f"\n[복원됨] 마지막 선택: {radio_stations[current_index]['name']}")
    display_station(current_index)

    try:
        while True:
            # ----------------------------
            # 로터리 처리
            # ----------------------------
            s1State = GPIO.input(S1)
            s2State = GPIO.input(S2)

            if s1State != s1LastState:
                now = time.time()
                if now - last_rotation_time > ROTATION_DEBOUNCE_SEC:
                    # 방향 판정
                    if s2State != s1State:
                        current_index = (current_index + 1) % len(radio_stations)
                    else:
                        current_index = (current_index - 1) % len(radio_stations)

                    display_station(current_index)

                    # 저장 예약
                    needs_save = True
                    last_change_time = now

                    # 재생 중이라면 "즉시 전환"이 아니라 "멈춘 후 전환" 예약
                    if is_playing:
                        pending_play = True
                        last_station_change_time = now

                    last_rotation_time = now

            s1LastState = s1State

            # ----------------------------
            # 버튼 처리 (재생/정지 토글)
            # ----------------------------
            keyState = GPIO.input(KEY)
            if keyState == 0 and keyLastState == 1:
                if is_playing:
                    stop_playback()
                else:
                    play_station(current_index)

                # 변경 시각 기록(저장/재생 모두)
                now = time.time()
                needs_save = True
                last_change_time = now

                # 버튼 디바운스
                time.sleep(0.3)

            keyLastState = keyState

            # ----------------------------
            # (중요) 로터리 멈춘 뒤 일정 시간 후에만 재생 전환
            # ----------------------------
            if pending_play and (time.time() - last_station_change_time) >= PLAY_SWITCH_DELAY_SEC:
                play_station(current_index)
                pending_play = False

            # ----------------------------
            # 마지막 변경 후 5초 지나면 저장
            # ----------------------------
            if needs_save and (time.time() - last_change_time) >= SAVE_DELAY_SEC:
                save_last_station(current_index)
                needs_save = False

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n프로그램 종료")
        # 종료 시 최종 저장
        if needs_save:
            save_last_station(current_index)

        # 재생 중지(프로세스는 kill할 수도 있고, 남겨도 되지만 여기서는 정리)
        try:
            stop_playback()
        except Exception:
            pass

    finally:
        # mpv 프로세스 종료
        try:
            if player_process:
                player_process.terminate()
                player_process.wait(timeout=2)
        except Exception:
            pass

        # IPC 소켓 정리
        try:
            if os.path.exists(MPV_SOCK):
                os.remove(MPV_SOCK)
        except Exception:
            pass

        GPIO.cleanup()

if __name__ == "__main__":
    main()
