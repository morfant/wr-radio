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


def _is_mac_like(s: str) -> bool:
    """문자열이 MAC 주소 형태인지 (콜론/하이픈 모두)"""
    return bool(
        re.match(r"^[0-9A-Fa-f:]{17}$", s) or
        re.match(r"^[0-9A-Fa-f]{2}(-[0-9A-Fa-f]{2}){5}$", s)
    )


def get_paired_devices() -> list:
    """
    실제 페어링된 장치만 반환 [(MAC, 이름), ...]
    1) bluetoothctl devices Paired 시도
    2) 빈 경우 → devices 전체 목록에서 info로 Paired: yes 확인
    """
    # 1) Paired 필터 (BlueZ 5.55+)
    out = _bt("devices Paired")
    pairs = []
    for line in out.splitlines():
        m = re.match(r"Device ([0-9A-Fa-f:]{17})\s+(.+)", line)
        if m:
            pairs.append((m.group(1), m.group(2).strip()))

    if pairs:
        return [(mac, name) for mac, name in pairs if not _is_mac_like(name)]

    # 2) 구버전 fallback: 모든 캐시 장치에서 info로 검증
    out = _bt("devices")
    macs = []
    for line in out.splitlines():
        m = re.match(r"Device ([0-9A-Fa-f:]{17})", line)
        if m:
            macs.append(m.group(1))

    devices = []
    for mac in macs:
        info = _bt(f"info {mac}", timeout=4)
        if "Paired: yes" not in info:
            continue
        name = ""
        has_uuids = False
        is_a2dp   = False
        for line in info.splitlines():
            nm = re.search(r"^\s*Name:\s+(.+)", line)
            if nm:
                name = nm.group(1).strip()
            if "UUID" in line:
                has_uuids = True
            if "110b" in line.lower():
                is_a2dp = True
        if not name or _is_mac_like(name):
            continue
        if has_uuids and not is_a2dp:
            continue
        devices.append((mac, name))

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


def get_current_bt_sink() -> str:
    """재시도 없이 현재 등록된 BT sink 반환 (빠른 조회용)"""
    out = _pactl(["list", "short", "sinks"])
    for line in out.splitlines():
        if "bluez" in line.lower():
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return None


def pair(mac: str) -> bool:
    """페어링 (NoInputNoOutput — PIN 없이 자동 승인)"""
    _bt("agent NoInputNoOutput")
    _bt("default-agent")
    out = _bt(f"pair {mac}", timeout=20)
    if "Failed" in out and "already" not in out.lower():
        log.warning(f"페어링 실패: {out[:80]}")
        return False
    _bt(f"trust {mac}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Scanner
# ─────────────────────────────────────────────────────────────────────────────

import threading


class Scanner:
    """
    백그라운드 BT 스캔.
    - 페어링된 장치는 start() 시 즉시 채움
    - [NEW] / [CHG] 라인 처리
    - 이름 없는 장치(MAC 형태 포함)는 제외
    - 이름 조회(bluetoothctl info)는 별도 스레드 — 스캔 루프 블로킹 없음
    """

    def __init__(self):
        self._devices: dict = {}      # {mac: (name, is_paired)}
        self._proc    = None
        self._thread  = None
        self._running = False
        self._lock    = threading.Lock()
        self._paired_macs: set = set()
        self._pending: set = set()    # info 조회 중인 MAC

    def start(self):
        self._running = True
        for mac, name in get_paired_devices():
            self._paired_macs.add(mac)
            with self._lock:
                self._devices[mac] = (name, True)

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _add(self, mac: str, name: str):
        """검증 후 목록에 추가"""
        name = name.strip()
        if not name or _is_mac_like(name):
            return
        is_paired = mac in self._paired_macs
        with self._lock:
            if mac in self._devices:
                return   # 이미 있으면 무시
            self._devices[mac] = (name, is_paired)
        tag = "페어링됨" if is_paired else "새 장치"
        print(f"🔵 BT [{tag}] {name}  ({mac})")

    def _lookup_async(self, mac: str):
        """bluetoothctl info 로 이름 조회 — 별도 스레드"""
        with self._lock:
            if mac in self._pending or mac in self._devices:
                return
            self._pending.add(mac)

        def _work():
            try:
                out = _bt(f"info {mac}", timeout=5)
                name = ""
                has_uuids = False
                is_a2dp   = False
                for line in out.splitlines():
                    m = re.search(r"^\s*Name:\s+(.+)", line)
                    if m:
                        name = m.group(1).strip()
                    if "UUID" in line:
                        has_uuids = True
                    # A2DP Sink UUID: 0000110b (오디오 출력 장치)
                    if "110b" in line.lower():
                        is_a2dp = True

                print(f"[BT INFO] mac={mac}  name={repr(name)}  a2dp={is_a2dp}  has_uuids={has_uuids}")

                if not name or _is_mac_like(name):
                    print(f"[BT INFO] mac={mac} 이름 없음 또는 MAC형태 → 제외")
                    return
                # UUID 정보 있는데 A2DP Sink 없으면 오디오 출력 불가 장치 → 제외
                if has_uuids and not is_a2dp:
                    print(f"[BT INFO] mac={mac} ({name}) A2DP Sink 없음 → 제외")
                    return
                self._add(mac, name)
            finally:
                with self._lock:
                    self._pending.discard(mac)

        threading.Thread(target=_work, daemon=True).start()

    def _run(self):
        try:
            subprocess.run(
                ["bluetoothctl", "set-scan-filter-rssi", "-80"],
                capture_output=True, timeout=3
            )
            self._proc = subprocess.Popen(
                ["bluetoothctl", "--timeout", "60", "scan", "on"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            print("🔵 스캔 프로세스 시작")
            # ANSI 색상 코드 제거용 패턴
            ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
            for line in self._proc.stdout:
                line = line.rstrip()
                clean = ansi_escape.sub('', line)   # ← ANSI 제거
                print(f"[BT RAW] {repr(clean)}")
                if not self._running:
                    break

                # [NEW] Device MAC Name
                m = re.search(r"\[NEW\] Device ([0-9A-Fa-f:]{17})\s+(.+)", clean)
                if m:
                    mac, name = m.group(1), m.group(2).strip()
                    print(f"[BT NEW] mac={mac}  name={repr(name)}")
                    # 이름 있어도 _lookup_async로 UUID 확인
                    self._lookup_async(mac)
                    continue

                # [CHG] — 처음 보는 MAC
                m = re.search(r"\[CHG\] Device ([0-9A-Fa-f:]{17})\s+", clean)
                if m:
                    mac = m.group(1)
                    with self._lock:
                        known = mac in self._devices or mac in self._pending
                    if not known:
                        print(f"[BT CHG unknown] mac={mac} → lookup")
                        self._lookup_async(mac)

            print("🔵 스캔 프로세스 종료")
        except Exception as e:
            print(f"[BT ERROR] 스캔 스레드 오류: {e}")
        finally:
            try:
                subprocess.run(
                    ["bluetoothctl", "set-scan-filter-clear"],
                    capture_output=True, timeout=3
                )
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                pass
            self._proc = None
        # bluetoothctl scan off 는 호출하지 않음
        # → BlueZ 장치 캐시가 지워져서 재진입 시 devices Paired 가 빈 값 반환되는 문제 방지

    def has_pending(self) -> bool:
        with self._lock:
            return bool(self._pending)

    def get_devices(self) -> list:
        """[(MAC, 이름, 페어링여부), ...] — 페어링된 것 먼저"""
        with self._lock:
            paired = [(mac, n, True)  for mac, (n, p) in self._devices.items() if p]
            new    = [(mac, n, False) for mac, (n, p) in self._devices.items() if not p]
        return paired + new
