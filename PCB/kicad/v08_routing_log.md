# v08 HAT 배선 진행 기록

배선 방식: Claude가 KiCad Python(pcbnew) 스크립트로 구역별로 그리고, 구역마다 확대 그림을 사용자에게 보여 확인받은 뒤 다음 구역으로 간다. 그린 선·비아·존은 잠가서 나중 자동 배선(Freerouting)이 건드리지 못하게 한다.

- 스크립트는 KiCad GUI가 **닫힌 상태**에서만 돌린다 (`pgrep -fl kicad` 확인).
- 구역 스크립트는 재실행 가능하다: 자기 구역의 선·비아·존을 지우고 다시 그린다.
- 그림 도구: `tools/v08board/dump_region.py`, `plot_region.py` (구역 메모는 `notes_<n>_<이름>.json`).
- 자동 배선 도구: Freerouting 2.5.0 `~/Applications/freerouting/freerouting-2.5.0.jar`, Java는 `$(brew --prefix openjdk)/bin/java`.

## 진행 현황

| 구역 | 상태 | 스크립트 / 그림 |
|---|---|---|
| 1. 부스트 (U4 TPS61023) | **완료** (2026-11-08) | `tools/v08board/route_1_boost.py` / `radio-hat-v08/route_1_boost.png` |
| 2. 충전 경로 + 배터리 보호 | **완료** (2026-11-12) | `place_2.py` → `route_2a_usbc.py` → `route_2b_charger.py` → `route_2c_battery.py` (공용 `routelib.py`) / `radio-hat-v08/route_2_charger.png` |
| 3. +5V → J1 (Pi) | 다음 | C8.1에서 왼쪽으로, 약 40mm, 굵게 |
| 4. 헤드폰 DAC (U6) + 잭 J8 | 대기 | 캡은 핀 옆, 출력은 짧게, L1에서 멀리 |
| 5. 스피커 앰프 (U7) + J7 | 대기 | SPK+/SPK− 나란히 |
| 6. 일반 신호선 | 대기 | Freerouting (I2C, SPI/LCD, 엔코더, 제어선, LED, J9) |
| 7. GND 채우기 + 연결 비아 | 대기 | F.Cu/B.Cu 모두. 지금 B.Cu에 이름 없는 연습용 GND 존이 있음 → 정식 존으로 교체 |
| 8. 마무리 | 대기 | DRC 0, 실크 정리, Fable 최종 검토 제안 |

## 구역 1 (부스트) 메모

- U4를 90° 돌려 핀 6/5/4(VOUT/SW/GND)가 위로 오게 했다. C6·C7이 그 바로 위에 붙고 F.Cu 존 `BST_5V_F`(+5V), `BST_GND_F`(GND)로 묶었다. 스위칭 고리 약 2mm, 비아 없음.
- 옮긴 부품: U4, L1, C6, C7, C5, R11, C26, R12, R13 (자세한 좌표는 스크립트).
- 남겨 둔 출구:
  - +5V → J1 2/4번: C8 1번 패드 (31.8, −60.8)에서 왼쪽으로.
  - SYS 입력: C5 아래 y ≈ −49.6 틈으로 F.Cu에서 들어온다. 틈은 0.6mm 선만 들어가므로 짧게 지나고 바로 1.0mm로 넓힌다 (뒷면으로 돌리면 GND 면이 갈라져서 이쪽을 택함).
  - BST_EN → J4.2: R13 1번 패드 (37.775, −51.5)에서 왼쪽으로, D1 위를 지나 아래로.
- 점검: 구리 관련 DRC 오류 0, 부스트 구역 안 연결 모두 완료.

## 구역 2 (충전 + 로드셰어 + 배터리 보호) 메모

- 스크립트 순서: `place_2.py`(부품 위치) → `route_2a_usbc.py` → `route_2b_charger.py` → `route_2c_battery.py`(U2/U3/C4/R8/R9 위치도 여기서). 각 스크립트는 자기가 넣은 항목을 `owned_<단계>.json`(UUID)으로 기억해 지우고 다시 그린다. 공용 함수 `routelib.py` (`python3 routelib.py drc [넷…]` = DRC 요약).
- 옮긴 부품(옛 좌표는 스크립트 주석): U1 180° 회전(VCC 왼쪽 위, BAT 왼쪽 아래, 상태·CE 아래 줄), D1을 부스트 오른쪽(51.0, −49.9)으로 — 캐소드 패드가 SYS 줄기에 바로 닿고 애노드는 J2 A9/B4에서 바로 받음. Q1은 U1 왼쪽 위(38.0, −46.6). C1~C3, R1~R7, R10, R24, D4, Q2, U2, U3, C4, R8, R9도 옮김. 가장자리 부품(J2, J3, D2/D3)·홀은 그대로, courtyard 겹침 0.
- 전류 경로 (모두 F.Cu):
  - USB: A9/B4 → D1 애노드(1.0 + 작은 VBUS 존) → SYS 존·줄기. D1 애노드에서 0.8 띠가 U1 위를 지나 VCC(4번)·C2·Q1 게이트로.
  - A4/B9 → D4(TVS, 커넥터 옆 약 2 mm)·C1·R6·R24/R10. 두 VBUS 핀 묶음은 핀 바로 옆 비아 2개 + B.Cu 0.6 (약 5 mm)로 연결 — CC1/CC2가 두 묶음 사이에 있어서. R1/R2는 그 안쪽에, GND는 비아 1개.
  - BAT+: Q1 드레인 → C3 → U1 BAT, 줄기 1.5 mm가 U5와 ADC 분압 줄 사이로 내려가 그 줄 아래를 비스듬히 지나 U3 왼쪽(1.2 mm)으로 J3.1.
  - SYS: Q1 소스 → C5 아래 y −49.5 통로(0.8) → C5.1. D1 캐소드 → 줄기·C27 (존 `CHG_SYS_F`).
  - B−: U3 S1(2,3번) → U3 오른쪽 1.2 mm → J3.2. U3 S2(6,7번) = 시스템 GND: 패키지 아래 작은 존 `BAT_GND_F` + 비아 4개.
- U1 EP: 비아 6개(0.6/0.3, 3×2), GND 핀 1(TEMP)·3을 EP로. R3(PROG) GND는 TEMP 핀으로.
- B.Cu 짧은 건너가기 (전부 가는 선): VBUS 핀 묶음 연결(0.6, 약 5 mm), LED·감지용 VBUS(0.3, V1 (56.0,−38.4) → V3 (56.0,−36.0) → V2 (54.2,−33.2), 상태선 CHRG/STDBY 밑으로 — R4가 두 상태선 사이에 있어서 어쩔 수 없음), DW01A VCC(0.3, 약 6.4 mm, y −17.8). OD는 U2 몸체 아래로 지나감.
- 남겨 둔 출구:
  - CHG_DIS → J1.22: R7.1 옆 비아 (46.9, −35.65)에서 B.Cu로 이어갈 것(상태선과 BAT+ 줄기에 둘러싸여 F.Cu로는 못 나감; via_dangling 경고 1개는 이 비아).
  - SYS → J4.1: 이미 연결(0.5, x 31.5로 내려감). BST_EN → J4.2는 그 왼쪽 x ≈ 30 길을 비워 둠.
  - VBUS_SENSE / VBAT_SENSE: R16.1에 VBUS(0.3, y −30.0), R14.1에 BAT+ 가지 연결됨. 분압 중간점 → U5.4/U5.5는 신호 구역 몫 — BAT+ 줄기(x 36.9)를 건너야 하므로 B.Cu 짧은 건너가기 필요.
  - 상태선은 D2/D3까지 완료.
- 점검: 구리 관련 DRC 오류 0 (남은 것: 실크 경고, via_dangling 1 = CHG_DIS 출구), 연결 안 됨 164 → 104 (남은 것은 다른 구역 넷과 GND 비아 미설치 패드), 회로도↔보드 불일치 0 (`chk_A3.py`, kicad-cli parity 0). 새 silk_over_copper 경고 약 14개는 마무리(8구역) 때 실크 정리.
