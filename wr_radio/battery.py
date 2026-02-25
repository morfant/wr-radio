import threading
import time
from typing import Optional, Tuple

# 배터리 전압 → 잔량 매핑 (LiPo 방전 커브 근사)
VOLTAGE_TABLE = [
    (4.20, 100),
    (4.10, 90),
    (4.00, 80),
    (3.90, 70),
    (3.80, 60),
    (3.70, 50),
    (3.60, 35),
    (3.50, 20),
    (3.40, 10),
    (3.30, 5),
    (3.00, 0),
]

SAMPLE_INTERVAL_SEC = 10   # 샘플링 간격 (초)
STABLE_WAIT_SEC = 20       # 채널 변경 후 안정화 대기 (초)
LOW_BATTERY_PCT = 15       # 저전력 경고 기준 (%)
BLINK_PERIOD_SEC = 2.0     # 점멸 주기 (초)


def voltage_to_percent(voltage: float) -> int:
    """배터리 전압 → 잔량 % 변환 (선형 보간, 5% 단위)"""
    if voltage >= VOLTAGE_TABLE[0][0]:
        return 100
    if voltage <= VOLTAGE_TABLE[-1][0]:
        return 0

    for i in range(len(VOLTAGE_TABLE) - 1):
        v_high, p_high = VOLTAGE_TABLE[i]
        v_low, p_low = VOLTAGE_TABLE[i + 1]
        if v_low <= voltage <= v_high:
            ratio = (voltage - v_low) / (v_high - v_low)
            raw = p_low + ratio * (p_high - p_low)
            return round(raw / 5) * 5

    return 0


class BatteryMonitor:
    def __init__(self):
        self.voltage: float = 0.0
        self.percent: int = 0
        self._lock = threading.Lock()
        self._running = False
        self._ads = None
        self._chan = None
        self._stable_after: float = 0.0  # 이 시각 이후부터 샘플링

    def init_adc(self) -> bool:
        """ADS1115 초기화. 성공 시 True."""
        try:
            import board
            import busio
            from adafruit_ads1x15.ads1115 import ADS1115
            from adafruit_ads1x15.analog_in import AnalogIn

            i2c = busio.I2C(board.SCL, board.SDA)
            self._ads = ADS1115(i2c)
            self._chan = AnalogIn(self._ads, 0)
            # 초기값은 대략적 — 안정화 후 정확해짐
            raw = self._chan.voltage
            self.voltage = raw * 2
            self.percent = voltage_to_percent(self.voltage)
            print(f"🔋 배터리 초기화: {self.voltage:.3f}V ({self.percent}%)")
            return True
        except Exception as e:
            print(f"❌ ADS1115 초기화 실패: {e}")
            return False

    def _read_voltage(self) -> Optional[float]:
        try:
            if self._chan is None:
                return None
            raw = self._chan.voltage
            return raw * 2
        except Exception as e:
            print(f"⚠️  배터리 읽기 실패: {e}")
            return None

    def pause_sampling(self):
        """채널 변경 등 부하 변동 시 호출 — 안정화 대기"""
        with self._lock:
            self._stable_after = time.time() + STABLE_WAIT_SEC

    def _is_stable(self) -> bool:
        return time.time() >= self._stable_after

    def _monitor_loop(self):
        while self._running:
            if self._is_stable():
                v = self._read_voltage()
                if v is not None:
                    with self._lock:
                        self.voltage = v
                        self.percent = voltage_to_percent(v)
            time.sleep(SAMPLE_INTERVAL_SEC)

    def start(self) -> bool:
        if not self.init_adc():
            return False
        # 초기 안정화 대기
        self._stable_after = time.time() + STABLE_WAIT_SEC
        self._running = True
        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()
        print("🔋 배터리 모니터링 시작")
        return True

    def stop(self):
        self._running = False

    def get_status(self) -> Tuple[float, int]:
        """(voltage, percent) 반환"""
        with self._lock:
            return (self.voltage, self.percent)

    @property
    def is_low(self) -> bool:
        return self.percent <= LOW_BATTERY_PCT

    @staticmethod
    def is_blink_on() -> bool:
        """점멸 주기에서 현재 '켜짐' 상태인지"""
        return (time.time() % BLINK_PERIOD_SEC) < (BLINK_PERIOD_SEC / 2)
