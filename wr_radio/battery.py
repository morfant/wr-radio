import threading
import time
from typing import Optional, Tuple

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

SAMPLE_INTERVAL_SEC = 10
VBUS_CHECK_INTERVAL_SEC = 2
STABLE_WAIT_SEC = 20
LOW_BATTERY_PCT = 15
BLINK_PERIOD_SEC = 2.0
VBUS_THRESHOLD = 4.0  # VBUS 분압값이 이 이상이면 충전 중


def voltage_to_percent(voltage: float) -> int:
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
        self.is_charging: bool = False
        self._lock = threading.Lock()
        self._running = False
        self._ads = None
        self._chan_bat = None   # A0: 배터리
        self._chan_vbus = None  # A1: USB VBUS
        self._stable_after: float = 0.0

    def init_adc(self) -> bool:
        try:
            import board
            import busio
            from adafruit_ads1x15.ads1115 import ADS1115
            from adafruit_ads1x15.analog_in import AnalogIn
            i2c = busio.I2C(board.SCL, board.SDA)
            self._ads = ADS1115(i2c)
            self._chan_bat = AnalogIn(self._ads, 0)
            self._chan_vbus = AnalogIn(self._ads, 1)

            # 첫 번째 읽기는 버림 (채널 안정화 전 값)
            try:
                self._chan_bat.voltage
                self._chan_vbus.voltage
            except Exception:
                pass
            time.sleep(0.2)

            # 배터리 초기값: 10번 평균
            samples = []
            for _ in range(10):
                try:
                    samples.append(self._chan_bat.voltage)
                except Exception:
                    pass
                time.sleep(0.05)
            raw = sum(samples) / len(samples) if samples else 0.0
            self.voltage = raw * 2
            self.percent = voltage_to_percent(self.voltage)

            # VBUS 초기값
            vbus = self._read_vbus()
            self.is_charging = vbus is not None and vbus >= VBUS_THRESHOLD

            charging_str = "충전 중" if self.is_charging else "배터리"
            print(f"🔋 배터리 초기화: {self.voltage:.3f}V ({self.percent}%) [{charging_str}]")
            return True
        except Exception as e:
            print(f"❌ ADS1115 초기화 실패: {e}")
            return False

    def _read_voltage(self) -> Optional[float]:
        try:
            if self._chan_bat is None:
                return None
            raw = self._chan_bat.voltage
            return raw * 2
        except Exception as e:
            print(f"⚠️  배터리 읽기 실패: {e}")
            return None

    def _read_vbus(self) -> Optional[float]:
        try:
            if self._chan_vbus is None:
                return None
            raw = self._chan_vbus.voltage
            return raw * 2
        except Exception as e:
            return None

    def pause_sampling(self):
        with self._lock:
            self._stable_after = time.time() + STABLE_WAIT_SEC

    def _is_stable(self) -> bool:
        return time.time() >= self._stable_after

    def _monitor_loop(self):
        last_bat_check = 0.0
        while self._running:
            now = time.time()
            if self._is_stable():
                # VBUS 충전 여부: 2초마다
                vbus = self._read_vbus()
                with self._lock:
                    was_charging = self.is_charging
                    self.is_charging = vbus is not None and vbus >= VBUS_THRESHOLD
                    if self.is_charging != was_charging:
                        status = "충전 시작" if self.is_charging else "충전 해제"
                        print(f"🔋 {status} (VBUS: {vbus:.2f}V)")

                # 배터리 전압: 10초마다
                if (now - last_bat_check) >= SAMPLE_INTERVAL_SEC:
                    last_bat_check = now
                    v = self._read_voltage()
                    if v is not None:
                        with self._lock:
                            self.voltage = v
                            self.percent = voltage_to_percent(v)
            time.sleep(VBUS_CHECK_INTERVAL_SEC)

    def start(self) -> bool:
        if not self.init_adc():
            return False
        self._stable_after = time.time() + STABLE_WAIT_SEC
        self._running = True
        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()
        print("🔋 배터리 모니터링 시작")
        return True

    def stop(self):
        self._running = False

    def get_status(self) -> Tuple[float, int]:
        with self._lock:
            return (self.voltage, self.percent)

    @property
    def is_low(self) -> bool:
        return self.percent <= LOW_BATTERY_PCT

    @staticmethod
    def is_blink_on() -> bool:
        return (time.time() % BLINK_PERIOD_SEC) < (BLINK_PERIOD_SEC / 2)
