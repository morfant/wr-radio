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
| 2. 충전 경로 + 배터리 보호 | 다음 | J2 → D4 → U1(EP 아래 0.3mm 비아) → Q1/D1 → SYS 입구, J3 → U3/U2 |
| 3. +5V → J1 (Pi) | 대기 | C8.1에서 왼쪽으로, 약 40mm, 굵게 |
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
