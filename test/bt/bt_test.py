#!/usr/bin/env python3
"""
bt_test.py — WR-Radio Bluetooth 오디오 테스트 스크립트

실행 방법:
  python3 bt_test.py                  # 대화형 메뉴
  python3 bt_test.py --scan           # BT 장치 스캔만
  python3 bt_test.py --stream <MAC>   # 페어링된 장치로 바로 스트리밍
"""

import subprocess
import sys
import time
import re
import argparse
import logging
import signal

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# 테스트용 스트림 URL (Jeju 환경음 — config.py의 실제 URL로 교체 가능)
TEST_STREAM_URL = "https://locus.creacast.com:9443/jeju_georo.mp3"

# ─────────────────────────────────────────────────────────────────────────────
# BlueZ 제어
# ─────────────────────────────────────────────────────────────────────────────

def bt_cmd(cmd: str, timeout: int = 10) -> str:
    """bluetoothctl 명령 실행 후 출력 반환"""
    try:
        result = subprocess.run(
            ["bluetoothctl"] + cmd.split(),
            capture_output=True, text=True, timeout=timeout
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        log.warning(f"bluetoothctl timeout: {cmd}")
        return ""
    except FileNotFoundError:
        log.error("bluetoothctl not found. Install: sudo apt install bluez")
        sys.exit(1)


def check_bt_powered() -> bool:
    out = bt_cmd("show")
    return "Powered: yes" in out


def power_on():
    log.info("Bluetooth 전원 ON...")
    bt_cmd("power on")
    time.sleep(1)
    if check_bt_powered():
        log.info("✓ Bluetooth 활성화됨")
        return True
    log.error("✗ Bluetooth 활성화 실패")
    return False


def get_paired_devices() -> list[tuple[str, str]]:
    """[(MAC, 이름), ...] 형태로 반환"""
    out = bt_cmd("devices")
    devices = []
    for line in out.splitlines():
        m = re.match(r"Device ([0-9A-Fa-f:]{17})\s+(.+)", line)
        if m:
            devices.append((m.group(1), m.group(2)))
    return devices


def scan_devices(duration: int = 10) -> list[tuple[str, str]]:
    """주변 BT 장치 스캔"""
    log.info(f"주변 장치 스캔 중... ({duration}초)")
    subprocess.Popen(
        ["bluetoothctl", "scan", "on"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(duration)
    subprocess.run(["bluetoothctl", "scan", "off"],
                   capture_output=True, timeout=5)

    return get_paired_devices()


def pair_and_connect(mac: str) -> bool:
    """페어링 + 신뢰 + 연결"""
    log.info(f"페어링 시도: {mac}")
    bt_cmd("agent NoInputNoOutput")
    bt_cmd("default-agent")

    out = bt_cmd(f"pair {mac}", timeout=30)
    if "Failed" in out and "already" not in out.lower():
        log.error(f"페어링 실패: {out}")
        return False

    bt_cmd(f"trust {mac}")
    return connect_device(mac)


def connect_device(mac: str) -> bool:
    """이미 페어링된 장치에 연결"""
    log.info(f"연결 중: {mac}")
    out = bt_cmd(f"connect {mac}", timeout=15)
    if "Connection successful" in out:
        log.info(f"✓ 연결 성공: {mac}")
        return True
    log.error(f"✗ 연결 실패: {out}")
    return False


def disconnect_device(mac: str):
    log.info(f"연결 해제: {mac}")
    bt_cmd(f"disconnect {mac}")


# ─────────────────────────────────────────────────────────────────────────────
# PulseAudio / PipeWire sink 탐색
# ─────────────────────────────────────────────────────────────────────────────

def get_bt_sink(retries: int = 5, wait: float = 1.5) -> str | None:
    """
    PulseAudio/PipeWire에서 Bluetooth A2DP sink 이름 반환.
    BT 연결 직후 sink 등록에 시간이 걸리므로 재시도.
    """
    log.info("PulseAudio BT sink 탐색 중...")
    for i in range(retries):
        try:
            out = subprocess.check_output(
                ["pactl", "list", "short", "sinks"],
                text=True, timeout=5
            )
            for line in out.splitlines():
                if "bluez" in line.lower():
                    sink = line.split()[1]
                    log.info(f"✓ BT sink 발견: {sink}")
                    return sink
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        if i < retries - 1:
            log.info(f"  sink 대기 중... ({i+1}/{retries})")
            time.sleep(wait)

    log.error("✗ BT sink를 찾을 수 없음")
    return None


def list_all_sinks():
    """현재 사용 가능한 모든 오디오 sink 출력 (디버깅용)"""
    try:
        out = subprocess.check_output(
            ["pactl", "list", "short", "sinks"], text=True
        )
        print("\n[사용 가능한 오디오 sink]")
        for line in out.splitlines():
            print(f"  {line}")
    except FileNotFoundError:
        log.error("pactl not found. Install: sudo apt install pulseaudio-utils")
    except subprocess.CalledProcessError as e:
        log.error(f"pactl 오류: {e}")


def set_default_sink(sink: str):
    """시스템 기본 sink 변경"""
    try:
        subprocess.run(["pactl", "set-default-sink", sink], check=True, timeout=5)
        log.info(f"기본 sink → {sink}")
    except Exception as e:
        log.warning(f"기본 sink 변경 실패: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# mpv 스트리밍
# ─────────────────────────────────────────────────────────────────────────────

def stream_to_bt(sink: str, url: str = TEST_STREAM_URL):
    """
    mpv로 지정 sink에 스트리밍.
    pulse/<sink_name> 형식으로 audio-device 지정.
    """
    device = f"pulse/{sink}"
    cmd = [
        "mpv",
        f"--audio-device={device}",
        "--no-video",
        "--cache=yes",
        "--cache-secs=5",
        "--volume=70",
        "--msg-level=all=warn",
        "--term-osd-bar",
        url
    ]

    log.info(f"스트리밍 시작")
    log.info(f"  URL   : {url}")
    log.info(f"  장치  : {device}")
    log.info(f"  종료  : Ctrl+C\n")

    try:
        proc = subprocess.Popen(cmd)

        def _stop(sig, frame):
            log.info("\n스트리밍 중단...")
            proc.terminate()
            sys.exit(0)

        signal.signal(signal.SIGINT, _stop)
        proc.wait()

    except FileNotFoundError:
        log.error("mpv not found. Install: sudo apt install mpv")


def stream_default(url: str = TEST_STREAM_URL):
    """
    BT sink를 직접 지정하지 않고 시스템 기본 sink로 스트리밍.
    set_default_sink()로 BT를 기본으로 설정한 후 사용.
    """
    cmd = [
        "mpv",
        "--no-video",
        "--cache=yes",
        "--cache-secs=5",
        "--volume=70",
        "--msg-level=all=warn",
        url
    ]

    log.info(f"기본 sink로 스트리밍: {url}")
    log.info("종료: Ctrl+C\n")

    try:
        proc = subprocess.Popen(cmd)

        def _stop(sig, frame):
            proc.terminate()
            sys.exit(0)

        signal.signal(signal.SIGINT, _stop)
        proc.wait()

    except FileNotFoundError:
        log.error("mpv not found.")


# ─────────────────────────────────────────────────────────────────────────────
# 대화형 메뉴
# ─────────────────────────────────────────────────────────────────────────────

def interactive_menu():
    print("\n" + "="*50)
    print("  WR-Radio Bluetooth 테스트")
    print("="*50)

    # 1. BT 전원 확인
    if not check_bt_powered():
        if not power_on():
            sys.exit(1)

    while True:
        print("\n[메뉴]")
        print("  1. 페어링된 장치 목록 보기")
        print("  2. 주변 장치 스캔 (10초)")
        print("  3. 장치에 연결 후 스트리밍")
        print("  4. 현재 오디오 sink 목록 보기")
        print("  5. 종료")
        choice = input("\n선택: ").strip()

        if choice == "1":
            devices = get_paired_devices()
            if not devices:
                print("  페어링된 장치 없음")
            else:
                for i, (mac, name) in enumerate(devices):
                    print(f"  [{i}] {name}  ({mac})")

        elif choice == "2":
            scan_devices(10)
            devices = get_paired_devices()
            print(f"\n발견된 장치 {len(devices)}개:")
            for mac, name in devices:
                print(f"  {mac}  {name}")

        elif choice == "3":
            devices = get_paired_devices()
            if not devices:
                print("페어링된 장치가 없습니다. 먼저 스캔 후 페어링하세요.")
                continue

            print("\n연결할 장치 선택:")
            for i, (mac, name) in enumerate(devices):
                print(f"  [{i}] {name}  ({mac})")

            try:
                idx = int(input("번호: ").strip())
                mac, name = devices[idx]
            except (ValueError, IndexError):
                print("잘못된 입력")
                continue

            # 연결
            if not connect_device(mac):
                ans = input("페어링부터 시도할까요? (y/n): ").strip()
                if ans.lower() == "y":
                    if not pair_and_connect(mac):
                        continue
                else:
                    continue

            # sink 탐색
            sink = get_bt_sink()
            if not sink:
                print("\n[대안] 기본 sink로 스트리밍을 시도합니다.")
                set_default_sink_ans = input("시스템 기본 sink를 BT로 변경 후 스트리밍? (y/n): ")
                if set_default_sink_ans.lower() == "y":
                    stream_default()
                continue

            # 스트리밍
            custom_url = input(f"\n스트림 URL (Enter = 기본값): ").strip()
            url = custom_url if custom_url else TEST_STREAM_URL
            stream_to_bt(sink, url)

            # 종료 후 연결 해제
            ans = input("\nBT 연결을 해제할까요? (y/n): ").strip()
            if ans.lower() == "y":
                disconnect_device(mac)

        elif choice == "4":
            list_all_sinks()

        elif choice == "5":
            print("종료")
            break


# ─────────────────────────────────────────────────────────────────────────────
# 엔트리포인트
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WR-Radio BT 오디오 테스트")
    parser.add_argument("--scan", action="store_true", help="장치 스캔만 실행")
    parser.add_argument("--stream", metavar="MAC", help="지정 MAC으로 바로 스트리밍")
    parser.add_argument("--url", default=TEST_STREAM_URL, help="스트림 URL")
    parser.add_argument("--sinks", action="store_true", help="오디오 sink 목록만 출력")
    args = parser.parse_args()

    if args.sinks:
        list_all_sinks()
        return

    if args.scan:
        power_on()
        devices = scan_devices(10)
        print(f"\n발견된 장치 {len(devices)}개:")
        for mac, name in devices:
            print(f"  {mac}  {name}")
        return

    if args.stream:
        mac = args.stream
        power_on()
        if not connect_device(mac):
            log.error("연결 실패. 페어링 상태를 확인하세요.")
            sys.exit(1)
        sink = get_bt_sink()
        if not sink:
            log.error("BT sink를 찾을 수 없습니다.")
            sys.exit(1)
        stream_to_bt(sink, args.url)
        return

    # 인수 없으면 대화형 메뉴
    interactive_menu()


if __name__ == "__main__":
    main()
