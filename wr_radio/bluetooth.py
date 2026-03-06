"""
bluetooth.py — WR-Radio Bluetooth 관리 모듈

BlueZ(bluetoothctl)로 연결 제어,
PulseAudio(pactl)로 A2DP sink 탐색.
"""

import re
import subprocess
import time
import logging

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────────────────────────────────────

def _bt(cmd: str, timeout: int = 10) -> str:
    """bluetoothctl 명령 실행 → stdout+stderr 반환"""
    try:
        r = subprocess.run(
            ["bluetoothctl"] + cmd.split(),
            capture_output=True, text=True, timeout=timeout
        )
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        log.warning(f"bluetoothctl timeout: {cmd}")
        return ""
    except FileNotFoundError:
        log.error("bluetoothctl not found")
        return ""


def _pactl(args: list, timeout: int = 5) -> str:
    """pactl 명령 실행 → stdout 반환"""
    try:
        r = subprocess.run(
            ["pactl"] + args,
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        log.warning(f"pactl 오류: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────────────────────

def is_powered() -> bool:
    """BT 컨트롤러 전원 상태"""
    return "Powered: yes" in _bt("show")


def get_paired_devices() -> list[tuple[str, str]]:
    """페어링된 장치 목록 [(MAC, 이름), ...]"""
    devices = []
    for line in _bt("devices").splitlines():
        m = re.match(r"Device ([0-9A-Fa-f:]{17})\s+(.+)", line)
        if m:
            devices.append((m.group(1), m.group(2).strip()))
    return devices


def is_device_connected(mac: str) -> bool:
    """특정 장치가 현재 연결되어 있는지 확인"""
    out = _bt(f"info {mac}")
    return "Connected: yes" in out


def connect(mac: str) -> bool:
    """페어링된 장치에 연결. 성공 시 True."""
    log.info(f"BT 연결 시도: {mac}")
    out = _bt(f"connect {mac}", timeout=15)
    if "Connection successful" in out:
        log.info(f"BT 연결 성공: {mac}")
        return True
    log.warning(f"BT 연결 실패: {out[:80]}")
    return False


def disconnect(mac: str) -> None:
    """연결 해제"""
    log.info(f"BT 연결 해제: {mac}")
    _bt(f"disconnect {mac}")


def find_bt_sink(retries: int = 6, wait: float = 1.0) -> str | None:
    """
    PulseAudio에서 bluez A2DP sink 이름 반환.
    BT 연결 직후 sink 등록에 시간이 걸리므로 재시도.
    반환 예: 'bluez_sink.A0_60_90_61_95_1E.a2dp_sink'
    """
    for i in range(retries):
        out = _pactl(["list", "short", "sinks"])
        for line in out.splitlines():
            if "bluez" in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    log.info(f"BT sink 발견: {parts[1]}")
                    return parts[1]
        if i < retries - 1:
            log.debug(f"sink 대기 중... ({i+1}/{retries})")
            time.sleep(wait)

    log.warning("BT sink를 찾을 수 없음")
    return None


def get_current_bt_sink() -> str | None:
    """재시도 없이 현재 등록된 BT sink 반환 (빠른 조회용)"""
    out = _pactl(["list", "short", "sinks"])
    for line in out.splitlines():
        if "bluez" in line.lower():
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return None
