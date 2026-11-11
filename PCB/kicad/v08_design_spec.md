# wr-radio HAT v08 회로 설계 사양 (2026-11-08, Fable 판단 완료 → 회로도 파일 생성은 Opus; 같은 날 부품 조사 후 변경 반영)

v07(외장 모듈 4개 + 외장 충전 모듈)을 모두 보드 위 SMT 부품으로 통합한다. JLCPCB SMT 조립 목표.
이 문서는 **설계 판단이 끝난 상태**이며, 이 사양대로 KiCad 10 회로도(`radio-hat-v08.kicad_sch` + `.kicad_pro`)를 생성하면 된다.
생성 방법 권장: Python 스크립트로 `.kicad_sch` s-expression을 직접 작성(라이브러리 심볼은 `/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/*.kicad_sym`에서 블록을 복사해 `lib_symbols`에 포함).
각 핀에 짧은 와이어 + 넷 라벨 방식으로 그려도 됨(배치 정돈은 사용자가 GUI에서). 완료 후 `kicad-cli sch erc`로 검증하고 `kicad-cli sch export pdf`로 렌더 확인.

**(2026-11-08 변경)** 부품 조사(`v08_parts.md`)와 v06/v07 실물 사진 확인 후 반영한 변경: SD_MODE 하단 1.8k, TPS61023 분압 220k/30k, PROG 1.2k(1A), 8205A를 HXY C5148694로, 헤드폰 잭 PJ-307C + 팁 NC 감지 회로, STDBY LED 백색, 10µF 전부 0805 25V C15850, LCSC 필드 채움, J5 LCD 핀 순서 v07 실물대로, J6 VCC를 +3V3로, J1 풋프린트를 부품면용 커스텀으로. 아래 각 항목에 표시.

**(2026-11-08 변경 2차)** 독립 감사(`v08_audit.md`) 반영: 보호 FET를 WSP8814(저 Rds)로, ADC 감지 분압 100k/100k, VBUS 10k 풀다운 추가, 헤드폰 감지 4.7k/22µF, 부스트 분압 510k/68k(5.06V) + 피드포워드 330pF, 부스트 입력 22µF 추가, 인덕터 FXL0420-1R0-MA1(Isat 6.5A), 배터리 커넥터 JST XH, 스피커 극성 v07과 같게, USB VBUS TVS(SMAJ5.0A) 추가, JP1 경고 메모. PROG 1.2k(1A)는 사용자 결정으로 유지.

**(2026-11-08 A3 케이스 반영)** 케이스 A3안(`Case/concepts/A3_review.md` P1~P7)에 맞춰 커넥터 종류·위치 변경: 보드는 케이스 뒷벽에 세우고 **부품면이 뒷벽(여유 약 17 mm)** 을 본다(9절). USB-C J2와 측면 발광 충전 LED는 KiCad 오른쪽 변(케이스 왼쪽 벽), 이어폰 잭 J8은 KiCad 위 변(케이스 위 벽), 배터리 J3는 JST XH 옆꽂이로 KiCad 아래 변(아래에서 꽂음), J4~J7은 2.54 mm **라이트앵글** 헤더, TP4056 풋프린트를 비아 없는 EP 버전으로, 시리얼 디버그 패드 J9(GPIO14/15, 부품 미실장) 추가. 배치 스크립트 `tools/v08board/place_A3.py`, 회로도 수정 `tools/v08board/sch_A3.py`.

## 0. 확정된 큰 결정
| v07 외장 모듈 | v08 통합안 | 근거 |
|---|---|---|
| UDA1334 DAC + PAM8403 앰프 | **MAX98357A**(스피커, I2S 직결) + **PCM5102A**(헤드폰 라인아웃) 병렬 I2S | MAX98357A는 라인아웃 없음·BTL 출력이라 헤드폰 불가 → DAC 별도. Pi I2S는 송신 전용이라 수신 칩 2개 병렬 OK, 오버레이 hifiberry-dac 그대로 |
| ADS1115 모듈 | ADS1115IDGS 직접 실장, ADDR=GND(0x48) | 소프트웨어 무변경 |
| TPS61023 부스터 모듈 | TPS61023DRL + 1µH + 10µF/2×22µF, 5V | 데이터시트 Fig 8-1 그대로(Li-ion→5V 1.5A) |
| 외장 TP4056 충전 모듈 | TP4056(ESOP-8) + DW01A + 듀얼 N-FET 보호(WSP8814 C148371 (2026-11-08 변경 2차); 1차 변경 때는 HXY 8205A) + 로드셰어링 P-FET | 충전 중 Pi 구동 시 종지 오판 방지 위해 로드셰어링 필수 |
| 충전 상한(메모 charge-limit-feature A안: VBUS P-FET 스위치) | **TP4056 CE 핀 게이팅으로 변경** (GPIO25 → 2N7002 → CE) | 칩 직접 실장이라 CE 노출됨. 페일세이프: GPIO LOW/플로팅 = 충전 ON |

## 1. GPIO 맵 (BCM, 물리핀) — CLAUDE.md 기준 + 신규 1개
| 신호 | BCM | 물리핀 | 비고 |
|---|---|---|---|
| I2C SDA / SCL | 2 / 3 | 3 / 5 | ADS1115 (Pi 보드 내 1.8k 풀업 있음, 추가 풀업 불필요) |
| I2S BCLK / LRCLK / DIN | 18 / 19 / 21 | 12 / 35 / 40 | PCM5102A BCK/LRCK/DIN + MAX98357A BCLK/LRCLK/DIN 병렬 |
| SPI MOSI / SCLK | 10 / 11 | 19 / 23 | LCD DIN / CLK |
| LCD CS / DC / RST / BL | 26 / 13 / 6 / 12 | 37 / 33 / 31 / 32 | |
| ENC S1 / S2 / KEY | 17 / 27 / 22 | 11 / 13 / 15 | |
| HP_DET | 23 | 16 | 내부 풀업, HIGH=삽입. 잭 팁 NC 스위치 + 4.7k/22µF 필터 사용(4.2절) (2026-11-08 변경 2차) |
| AMP_SD | 24 | 18 | MAX98357A SD_MODE 제어 |
| **CHG_DIS** (신규) | **25** | 22 | HIGH=충전 차단. 소프트웨어 추후(battery.py 히스테리시스 4.0V 차단/3.85V 재개) |
| 5V (HAT→Pi 공급) | – | 2, 4 | 부스터 출력 |
| 3V3 (Pi→HAT) | – | 1, 17 | ADS1115, PCM5102A 전원 |
| GND | – | 6,9,14,20,25,30,34,39 | |
| **UART_TX / UART_RX** (디버그) | 14 / 15 | 8 / 10 | J9 디버그 패드 전용(부품 미실장). 넷 이름은 Pi 기준(TX = Pi 송신) (2026-11-08 A3 케이스 반영) |
| ID_SD/ID_SC(27,28) 및 나머지 GPIO | – | – | No-connect 표시 |

## 2. 전원부
### 2.1 USB-C 입력 J_USB (Connector:USB_C_Receptacle_USB2.0_16P, 풋프린트 Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12)
- **위치 (2026-11-08 A3 케이스 반영)**: KiCad 오른쪽 변(케이스 왼쪽 벽) 가운데 위쪽, J2 (60.78, −47.8) r90. 소켓 앞면이 보드 가장자리보다 **1.0 mm 밖**(A3_review P4). H1(59.44, −29.16)과 그 보스(Ø6) 위쪽, H4 아래쪽에 들어감. TVS D4·VBUS 10µF C1·CC 저항 R1/R2는 J2 바로 왼쪽
- VBUS(A4,A9,B4,B9) → 넷 `VBUS`
- CC1 → 5.1k → GND, CC2 → 5.1k → GND (R_0603)
- GND(A1,A12,B1,B12), SHIELD → GND. D+/D-/SBU → No-connect
- VBUS 벌크 10µF — 0805 25V X5R, LCSC C15850(Basic) (2026-11-08 변경)
- VBUS TVS D4: **SMAJ5.0A**(Liown, LCSC C2925443, SMA, 단방향, VRWM 5V, VBR min 6.4V, Vc 9.2V) K=VBUS, A=GND (2026-11-08 변경 2차). Basic TVS는 없어서 Preferred Extended(셋업비 없음) 부품 사용. ESD·핫플러그 링잉 완화용(Vc 9.2V는 TP4056 절대최대 8V보다 높으므로 완전한 과전압 보호는 아님)

### 2.2 충전기 U_CHG TP4056 (Battery_Management:TP4056-42-ESOP8, 풋프린트 Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm — (2026-11-08 A3 케이스 반영) 비아 내장(_ThermalVias, 드릴 0.2 mm < 규칙 0.3 mm) 버전에서 변경. **배선할 때 EP 아래에 0.3 mm 비아를 직접 넣어 뒷면 GND와 넓게 이을 것**)
- VCC(4) = VBUS, 10µF to GND
- BAT(5) = 넷 `BAT+`, 10µF to GND (10µF는 모두 0805 25V C15850 (2026-11-08 변경))
- PROG(2) → **1.2k**(Basic C22765) → GND ≈ **1A** (2026-11-08 변경). 이유: 배터리 5000mAh 이상 사용 → 1A ≈ 0.2C. (이전: 2.0k ≈ 600mA)
- TEMP(1) → GND (온도감지 비활성)
- CHRG(7) → LED_CHRG(적) 애노드… 정확히: VBUS → 1k → LED(A→K) → CHRG. STDBY(6) 동일하게 VBUS → 1k → LED_STDBY(**백색**, C2290) → STDBY. (LED_0603) (2026-11-08 변경): 녹색은 Basic 부품이 없어 백색으로. CHRG는 적색(C2286) 유지
- **충전 LED (2026-11-08 A3 케이스 반영)**: 측면 발광(라이트앵글) LED로 바꿔 KiCad 오른쪽 변(케이스 왼쪽 벽)에서 바깥으로 빛을 냄. D2 CHRG = **적색 XINGLIGHT XL-1606SURC (C965860)**, D3 STDBY = **녹색 XINGLIGHT XL-1606UGC (C965863)** (2026-11-12 검토 M1로 MHS190UGCT에서 교체, D2와 같은 시리즈·같은 핀 기준, 풋프린트 `radio-hat-v08:LED_XINGLIGHT_XL-1606_Horizontal`) (백색 측면 LED는 JLC 재고가 수십 개뿐이라 녹색으로). 둘 다 풋프린트 `LED_SMD:LED_Kingbright_APA1606_1.6x0.6mm_Horizontal`(데이터시트 권장 패드와 거의 같음). 위치 D2 (62.63, −36.95), D3 (62.63, −32.95), 중심 간격 4.0 mm(D3는 H1 보스 Ø5.5 + 0.5 mm 한계까지 내림, J2는 위로 올림 → 케이스의 USB-C 홈(J2 중심 ±6.75 mm, 가장자리 y −41.05)과 D2 구멍(Ø2, 가장자리 y −37.95) 사이 벽 **3.10 mm**), 발광면이 보드 가장자리에서 약 0.5 mm. 직렬저항 R4/R5는 1k 유지: 적색 Vf 약 1.9V → 약 3.1 mA, 녹색 Vf 약 2.7V → 약 2.3 mA(녹색이 훨씬 밝은 칩이라 밝기는 비슷). **(2026-11-12 해소: D3를 XL-1606UGC로 바꿔 두 LED 모두 1번 = 캐소드)** 옛 주의: **MHS190UGCT 데이터시트는 1번 핀 = 애노드(XL-1606은 1번 = 캐소드)라서, JLC 조립 미리보기에서 두 LED의 캐소드 방향(풋프린트 패드 1 = K)을 꼭 확인**
- CE(8): 10k 풀업 → VBUS. Q_CE 2N7002 (Transistor_FET:2N7002, SOT-23) D=CE, S=GND, G=`CHG_DIS`(GPIO25) + G–GND 100k 풀다운. → GPIO LOW/플로팅이면 CE=H 충전 ON (페일세이프), GPIO HIGH면 충전 OFF
- GND(3), EPAD(9) → GND

### 2.3 배터리 보호 (DW01A + WSP8814) (2026-11-08 변경 2차)
- **(2026-11-08 A3 케이스 반영) 배터리 커넥터를 옆꽂이로**: **JST S2B-XH-A(LF)(SN), LCSC C157931**(Extended, 재고 약 6.8만), 풋프린트 `Connector_JST:JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal`. KiCad 아래 변 오른쪽 J3 (47.5, −4.17) r0: 하우징 앞면이 보드 아래 변(y 5.08)과 같은 선, **플러그는 아래(+y)에서 꽂아** 보드 아래 빈 바닥 공간(KiCad x 38~63.6, 높이 약 15 mm)으로 내려감. 핀1 BAT+ = x 47.5, 핀2 B− = x 50.0 (실크 +/−). 보호회로 U2/U3/C4/R8/R9는 J3 바로 위. 아래 줄의 수직형 B2B-XH-A는 이전 사양
- 배터리 커넥터 J_BAT: Connector_Generic:Conn_01x02, 풋프린트 (이전) **Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical**(JST B2B-XH-A(LF)(SN), LCSC C158012, 3A) (2026-11-08 변경 2차): PH(2A)는 배터리 피크 약 2.8A보다 정격이 낮아 XH로 변경. 핀1 = `BAT+`, 핀2 = 넷 `B-`(셀 음극, 시스템 GND와 FET로 분리). **배터리 리드는 + 를 핀1에 오도록 직접 크림핑할 것. 역극성 보호 없음**(회로도 메모 있음)
- DW01A (Battery_Management:DW01A, SOT-23-6): VCC(5) ← 100Ω ← BAT+, VCC–B- 사이 0.1µF; GND(6) = `B-`; CS(2) → 1k → GND(=P-, 시스템 그라운드); OD(1) → 넷 `OD`; OC(3) → 넷 `OC`; TD(4) No-connect
- 듀얼 N-FET U3: **Winsok WSP8814, LCSC C148371** (2026-11-08 변경 2차) (커스텀 심볼 `radio-hat-v08:WSP8814`, TSSOP-8, 풋프린트 Package_SO:TSSOP-8_4.4x3mm_P0.65mm). 핀: 1=D, 2=S1, 3=S1, 4=G1, 5=G2, 6=S2, 7=S2, 8=D (8205A와 같은 배열, Winsok 데이터시트 핀 그림으로 확인)
  - 이유(감사 M2): 8205A(27/37 mΩ max @4.5/2.5V) 두 개 직렬이면 DW01A 과전류 문턱 150mV에서 약 2~3A에 차단 → 배터리가 낮을 때 큰 음량 피크(약 2.8A)에 걸리고, 감지 분압 때문에 해제도 안 됨
  - WSP8814: 20V, Rds(on) 7.6/9.5 mΩ(typ/max) @4.5V, 9.5/13 mΩ @2.5V, ±12V Vgs, 9A. 두 FET 직렬 약 15~26 mΩ → 과전류 차단 전류 = (120~180 mV)/(직렬 Rds) ≈ **4.6~12 A**(typ 약 8~9 A, 25°C). 고온에서는 Rds가 커져 낮은 쪽으로 이동
  - 재고 약 2천 개(2026-11-08, 시제품 수량에 충분). Winsok 데이터시트에는 패키지 외형 도면이 없어(핀 그림과 'TSSOP-8' 표기만) 표준 TSSOP-8 4.4×3.0 P0.65로 간주
  - 결선: S1(2,3) = `B-`, G1(4) = `OD`, D(1)–D(8) 공통 드레인, G2(5) = `OC`, S2(6,7) = GND
  - (2026-11-08 변경, 2차에서 다시 교체) 스펙의 Fortune FS8205A(C16052)는 재고 0 → 1차에 **HXY 8205A, LCSC C5148694** 사용. HXY 데이터시트에서 핀배열(위와 동일)과 패키지(D 2.9~3.1, E 4.3~4.5, E1 6.25~6.55, e 0.65 = TSSOP-8 4.4x3 P0.65) 일치 확인
  - S1(2,3) = `B-`, G1(4) = `OD`(방전 FET), D1(1)–D2(8) 서로 연결(공통 드레인), G2(5) = `OC`(충전 FET), S2(6,7) = GND
  - 논리: 방전 FET 바디다이오드가 B-→GND 방향(충전 전류 통과), 충전 FET 바디다이오드가 GND→B- 방향

### 2.4 로드셰어링 (충전 중 배터리 분리)
- D_LS: Diode:SS34 (D_SMA) A=VBUS, K=넷 `SYS`
- Q_LS: Transistor_FET:AO3401A (SOT-23) **S=SYS, D=BAT+, G=VBUS**, G–GND 100k 풀다운
- VBUS–GND **10k 풀다운 R24**(C25804) 추가 (2026-11-08 변경 2차): USB가 없을 때 SS34 역누설(고온에서 수십~수백 µA)이 VBUS를 1~3V로 띄워 충전 중으로 오표시되거나 Q1이 덜 켜지는 것을 막음. USB 연결 시 손실 5V/10k = 0.5mA
  - VBUS 있음: Vgs≈+0.3 → OFF, 바디다이오드(BAT+→SYS)는 SYS(4.7V)>BAT(≤4.2V)라 역바이어스 → 배터리 분리, 부하는 USB에서
  - VBUS 없음: 게이트 0V → ON → 배터리가 SYS 공급

### 2.5 부스터 U_BST TPS61023 (라이브러리에 없음 → 커스텀 심볼. 풋프린트 Package_TO_SOT_SMD:SOT-563)
- 핀(TI SLVSF14B 확인): 1=FB, 2=EN, 3=VIN, 4=GND, 5=SW, 6=VOUT
- VIN = SYS, Cin 10µF (0805 25V C15850 (2026-11-08 변경)) + **22µF 0805 25V(C27, C45783 Basic)** (2026-11-08 변경 2차): 배터리 리드·SS34 경로 인덕턴스 대비(TI §8.2.2.5)
- L1 **1µH**: **cjiang FXL0420-1R0-MA1, LCSC C53426685**, 풋프린트 Inductor_SMD:L_Changjiang_FXL0420 (2026-11-08 변경 2차). 4.4×4.2×2.0 몰드형, DCR 27 mΩ max, Isat 6.5A(30% 강하, 보증값)/9.0A typ, Irms 5.4A(ΔT 20°C)/6.0A typ. 이전 SWPA4020S(Isat 4.78A, Irms 2.15A)는 배터리 3.0V·1.5A 출력에서 Irms 초과. 같은 계열 FXL0420-1R0-M(C167203, 재고 많음)은 Isat 보증값 5.6A라 6A 조건 미달 → -MA1 선택(재고 약 1천). SW ↔ L1 ↔ SYS
- VOUT = `+5V`, Cout 22µF ×2 (C_0805, 10V) + 벌크 220µF (Device:C_Polarized, SMD 전해 D6.3 또는 폴리머; v07 C3 220µF 계승)
- FB 분압(데이터시트 Fig 8-1, VREF 595mV): R1 **510k**(C23192) (VOUT–FB), R2 **68k**(C23231) (FB–GND) → 0.595 × (1 + 510/68) = **5.06V** (2026-11-08 변경 2차). 둘 다 Basic, R2 < 300k(데이터시트 §8.2.2.1 권장) 만족. 4.96V(1차 220k/30k)는 VREF 최소 580mV에서 4.83V까지 내려가 Pi 저전압 경고(약 4.63V)까지 여유가 작았음. OVP min 5.5V 대비 여유 있음
- **피드포워드 C26 330pF**(0603 C0G, C1664 Basic) R1과 병렬(VOUT–FB) (2026-11-08 변경 2차): TI SLVSF14B §8.2.2.4 "출력 용량 40µF 초과 시 영점 1kHz로 피드포워드 커패시터 권장", 식(10) C3 = 1/(2π·f_FFZ·R1) = 1/(2π·1kHz·510k) = 312pF → 330pF(영점 약 0.95kHz). +5V 레일 용량: 22µF×2 + 220µF + C21 10µF + Pi 보드 → 250µF 초과
- EN: J_SW Connector_Generic:Conn_01x03 ((2026-11-08 A3 케이스 반영) **PinHeader_1x03_P2.54mm_Horizontal 라이트앵글, XFCN PZ254R-11-03P C492411** — 이전: PinHeader_1x03 2.54 수직; 외장 토글 스위치용, v07 SWITCH 계승) 핀1=SYS, 핀2=EN, 핀3=GND. EN–GND 100k 풀다운(스위치 미장착 시 OFF). (2026-11-08 변경 2차) 기존 스위치는 3핀 SPDT 슬라이드 스위치로 확인됨 → 이 배선 그대로 동작(변경 없음)
- 데이터시트: Li-ion→5V 1.5A 가능. Pi Zero 2W + MAX98357A 피크 충분

### 2.6 전압 감지 분압 (ADS1115로)
- A0 ← BAT+ → **100k** → `VBAT_SENSE` → **100k** → GND  (v07 A0 계승, 배터리 OCV) (2026-11-08 변경 2차)
- A1 ← VBUS → **100k** → `VBUS_SENSE` → **100k** → GND  (v07 A1 계승, 플러그인 감지. 충전 차단 중에도 감지됨) (2026-11-08 변경 2차)
- 각 감지 노드에 100nF to GND(필터, ADC 샘플링 전하 공급) 유지
- (2026-11-08 변경 2차) 10k/10k → 100k/100k 이유: (1) BAT+–P− 사이 상시 20k 부하가 DW01A 과전류 해제(부하 약 500k 이상 필요)를 막아 래치되는 문제 완화(감사 M2), (2) Pi가 꺼진 상태에서 ADS1115 입력 ESD 다이오드를 통한 +3V3 역급전 전류를 1/10로(감사 m6). 비율은 그대로 1/2이라 소프트웨어 변경 없음. ADS1115 입력 임피던스는 MΩ급이라 오차 1% 이내

### 2.7 PWR_FLAG
- VBUS, BAT+, B-, SYS, +5V, +3V3, GND 각각에 power:PWR_FLAG (ERC 전원 미구동 오류 방지). 전원 심볼: power:+5V, +3V3, GND, VBUS 사용, 나머지는 넷 라벨

## 3. ADC U_ADC ADS1115IDGS (Analog_ADC:ADS1115IDGS, TSSOP-10)
- VDD(8)=+3V3, 0.1µF; GND(3)=GND; SDA(9)=`SDA`, SCL(10)=`SCL`; ADDR(1)=GND; ALERT/RDY(2) NC; AIN0(4)=VBAT_SENSE; AIN1(5)=VBUS_SENSE; AIN2(6), AIN3(7) NC

## 4. 오디오
### 4.1 헤드폰 DAC U_DAC PCM5102A (Audio:PCM5102A, TSSOP-20_4.4x6.5mm_P0.65mm)
- AVDD(8), DVDD(20), CPVDD(1) = +3V3, 각각 0.1µF + 공통 10µF(0805 25V C15850 (2026-11-08 변경))
- AGND(9), DGND(19), CPGND(3) = GND
- CAPP(2)–CAPM(4) 사이 2.2µF; VNEG(5) 2.2µF to GND; LDOO(18) 2.2µF to GND
- BCK(13)=`I2S_BCLK`, LRCK(15)=`I2S_LRCLK`, DIN(14)=`I2S_DIN`, SCK(12)=GND(BCK로 PLL)
- FMT(16)=GND(I2S), DEMP(10)=GND, FLT(11)=GND(normal), XSMT(17)= 10k → +3V3 (언뮤트)
- OUTL(6) → 100Ω → `HP_L` → 잭 T ; OUTR(7) → 100Ω → `HP_R` → 잭 R ; HP_L/HP_R 각 2.2nF to GND (RF 필터). (PCM5102A 출력은 차지펌프로 0V 중심이라 커플링 캡 불필요)
### 4.2 헤드폰 잭 J_HP (2026-11-08 변경)
- 부품: **PJ-307C**(Boom, LCSC C16684), THT 수평, **팁·링 NC 스위치**(슬리브 스위치 없음). 이전 사양의 "그라운드(슬리브) 스위치" 잭은 JLCPCB에서 찾지 못해 변경.
- 핀(데이터시트 도면 재확인): 1=슬리브, 5=팁 스프링, 4=팁 NC 접점, 2=링 스프링, 3=링 NC 접점. 플러그 없을 때 5–4, 2–3이 붙어 있고 삽입 시 떨어짐.
- 심볼: Connector_Audio:AudioJack3_SwitchTR 그림을 복사해 핀 번호를 데이터시트 번호로 바꾼 프로젝트 심볼 `radio-hat-v08:PJ-307C` (S→1, R→2, RN→3, TN→4, T→5; 풋프린트 패드 번호와 일치시키기 위함).
- 연결: 1(S)=GND, 5(T)=HP_L, 2(R)=HP_R, 3(RN)=No-connect, 4(TN)=감지.
- **감지 회로** (2026-11-08 변경 2차): 4(TN) → **4.7k**(R23, C23162) → `HP_DET`(GPIO23, 물리핀 16), `HP_DET` → **22µF**(C25, 0805 25V C45783 Basic) → GND. 외부 풀업 없음 — Pi 내부 풀업 사용(현재 소프트웨어 그대로). (1차: 10k/4.7µF)
  - 미삽입: 팁 스프링이 4번에 닿아 있어 HP_DET에 0V 중심 DAC 출력이 4.7k×22µF(τ≈100ms) 저역통과로 걸림 → 내부 풀업(약 50k)과 분압되어 DC ≈ 3.3 × 4.7/(4.7+50) ≈ **0.28V** → **LOW** (VIL max 0.8V까지 여유 약 0.5V. 1차 10k에서는 0.55V로 여유 부족 — 감사 M3).
  - 저음 리플도 τ 증가로 작아짐(DAC 풀스케일 50Hz 기준 약 0.1V 이하). 그래도 소프트웨어에서 여러 번 읽는 디바운스 권장.
  - 삽입: 접점이 열림 → 내부 풀업으로 **HIGH**. (극성은 v07과 같음: HIGH=삽입)
- **위치 (2026-11-08 A3 케이스 반영)**: KiCad 위 변 왼쪽 J8 (16.0, −61.4) r−90, 플러그 입구가 위(−y, 케이스 위 벽). 본체 앞면이 보드 위 변(y −64.90)과 같은 선이고 **원통이 3.0 mm 밖으로 나온다**(데이터시트 도면: 본체 11 + 앞 원통 3, 원통 지름은 도면에 ΦX로만 표기 — 실물 측정 필요. 2026-11-12 EasyEDA C16684 풋프린트와 대조: 구멍·슬롯 위치 모두 일치, 돌출 3.0 mm 확인, 원통 폭은 EasyEDA 실크 5.0 / 3D 모델 Ø6.0이라 케이스 구멍은 실물로 확정). 패드 2~5는 y −56.4 한 줄. DAC U6과 출력 R19/R20/C19/C20은 잭 바로 아래, 감지 R23/C25도 잭 근처. 부스트 L1/U4와 약 20 mm 떨어짐(보드 반대편 위쪽)
- 풋프린트: KiCad 기본 라이브러리에 없어 데이터시트 치수로 커스텀 작성 `radio-hat-v08.pretty/Jack_3.5mm_PJ-307C_Horizontal` (패드 번호 = 데이터시트 핀 번호, 플러그 입구는 -X 쪽).
  - 원점 = 1번 패드. 2·3·4·5번 패드: x=+5.0, y=-5/-2.5/+2.5/+5 (본체 앞면에서 8.5, 간격 5/10). 1번: (0,0), 본체 앞면에서 3.5.
  - 단자 구멍 5개 1.5×0.8 슬롯(1번은 세로, 2~5번은 가로), 패드 2.2×1.5. 위치 고정 핀 구멍 Ø1.2 5개(NPTH): 앞면에서 1.0·3.5, y=±5 네 개 + 뒤쪽 중앙(5.0, 0).
  - 본체 12×11(앞면 x=-3.5 ~ 7.5), 앞쪽 원통 3 mm 돌출(지름은 도면에 'ΦX'로만 표기 → 6 mm 가정).

### 4.3 스피커 앰프 U_AMP MAX98357A (Audio:MAX98357A, TQFN-16-1EP_3x3mm)
- VDD(7,8)=+5V, 10µF(C15850 (2026-11-08 변경)) + 0.1µF; GND(3,11,15), PAD(17)=GND; NC(5,6,12,13) No-connect
- DIN(1)=I2S_DIN, BCLK(16)=I2S_BCLK, LRCLK(14)=I2S_LRCLK
- GAIN_SLOT(2) = JP_GAIN Jumper:SolderJumper_3_Open 중앙핀(2). 핀1(A)=+5V(브리지 시 6dB), 핀3(B)=GND(브리지 시 12dB), 열림=9dB 기본. (ACC 보드 5핀 헤더 단순화; 3dB/15dB는 100k 경유라 제외)
  - **JP1은 한쪽만 브리지할 것 — 양쪽 다 브리지하면 5V–GND 단락** (2026-11-08 변경 2차)(회로도 메모 추가, 레이아웃 때 실크에도 표기)
- SD_MODE(4): `AMP_SD`(GPIO24) → 10k → SD_MODE 노드, 노드 → **1.8k**(C4177) → GND (2026-11-08 변경). GPIO HIGH 시 노드 ≈**0.50V** → (L+R)/2 모노 믹스 모드, LOW 시 셧다운. 데이터시트 문턱(B0 max 0.355V, B1 min 0.65V) 기준 개체 편차를 넘어서도 모노가 보장되는 구간 0.355~0.65V의 중앙(이전 1.5k는 0.43V로 하한 여유 0.05V뿐). (ACC의 1M→5V 풀업은 효과 없어 생략)
- OUTP(9) → FB1 Device:FerriteBead(0805) → `SPK+` → **J_SPK 핀2** ; OUTN(10) → FB2 → `SPK-` → **J_SPK 핀1** ; SPK+/SPK- 각 220pF to GND (ACC 보드 계승) (2026-11-08 변경 2차): v07 SPK(핀1 = L−, 핀2 = L+)와 같은 극성으로 맞춤
- J_SPK: Conn_01x02, ((2026-11-08 A3 케이스 반영)) **PinHeader_1x02_P2.54mm_Horizontal 라이트앵글, XFCN PZ254R-11-02P C492410**(이전: 2.54 수직, v07 SPK 계승). J7 (42.2, −14.2) r−90, 앰프 U7 바로 아래: 핀이 아래(+y)를 보지만 **보드 안**에 있고, 플라스틱 앞면(y −10.16)부터 아래 변 직전(y +4.84)까지 15 mm(x 37.8~44.0)를 부품 없는 플러그 공간으로 비움 — 플러그가 보드 가장자리 밖으로 나가지 않음(보드 아래 15 mm 공간에 6 mm 핀 + 듀폰 14 mm + 전선 꺾임이 안 들어가서 옮김). 핀1 SPK− = x 42.2, 핀2 SPK+ = x 39.66

## 5. 외부 커넥터 (v07 핀 순서 계승)
- **(2026-11-08 A3 케이스 반영) J4/J5/J6/J7은 모두 2.54 mm 라이트앵글(수평) 핀헤더**로 바꿈(세로 헤더 + 듀폰 플러그 + 전선 꺾임 약 22 mm > 부품면 앞 여유 17 mm). LCSC: XFCN PZ254R-11-0NP (2핀 C492410, 3핀 C492411, 5핀 C492413, 8핀 C492416, 모두 Extended·THT). 풋프린트 `Connector_PinHeader_2.54mm:PinHeader_1x0N_P2.54mm_Horizontal`. J4·J6·J5는 패드 열 x = 27.7에 위에서부터 차례로(J4 y −34.4~−39.5, J6 −20.5~−30.7, J5 +0.97~−16.8, 각 1번 핀이 아래쪽) 놓고 **핀이 −x(Pi 쪽)** 를 본다. 플라스틱 앞면(x 23.66)에서 J1 쪽으로 **15 mm(x 8.66~23.66, y −41.3~+2.8)는 부품 없는 플러그 공간**(배선은 지나가도 됨). 케이블은 J1 위로 들려 Pi 쪽·위 변 쪽으로 감. 핀 순서는 아래와 같음(변경 없음)
- J_LCD Conn_01x08 (PinHeader_1x08): **1=LCD_BL, 2=LCD_RST, 3=LCD_DC, 4=LCD_CS, 5=LCD_CLK, 6=LCD_DIN, 7=GND, 8=VCC(+5V)** (2026-11-08 변경): v07 Eagle LCD_CONN 패드 배치 그대로(기존 LCD 케이블 그대로 사용). 이전 사양의 1=GND…8=BL 순서는 틀렸음. LCD는 +5V 유지(Waveshare 1.54" 모듈에 자체 레귤레이터 있음)
- J_ENC Conn_01x05 (PinHeader_1x05): 1=**+3V3**, 2=ENC_KEY, 3=ENC_S2, 4=ENC_S1, 5=GND (핀 순서는 v07 ENC_CONN 계승) (2026-11-08 변경): 엔코더 모듈의 풀업 저항이 모듈 VCC에 걸려 있어, 5V를 주면 3.3V 전용 Pi GPIO에 정격 초과 전압이 걸림 → +3V3로 변경
- J_PI Connector:Raspberry_Pi_4 심볼(40핀, Pi 4와 Zero 2W 핀 동일), 풋프린트 **radio-hat-v08:PinHeader_2x20_P2.54mm_Horizontal_PiSide** (2026-11-08 변경): 실물 사진상 라이트앵글 헤더 본체는 HAT **윗면(부품면)**에 있고 Pi는 그 옆에 앞면이 위로 놓임. 표준 PinHeader_2x20_P2.54mm_Horizontal을 X 방향으로 거울 복사한 프로젝트 풋프린트를 F.Cu에 놓으면(본체는 보드 왼쪽 가장자리 밖으로) Pi 핀 n이 v07의 핀 n 위치에 온다(오차 0 mm 확인)
- **J_DBG J9 (2026-11-08 A3 케이스 반영)**: 시리얼 디버그 패드, Conn_01x03, 풋프린트 `Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical`(구멍 패드만, **부품 미실장 — DNP, BOM·위치 파일 제외, LCSC 없음**). 1 = GND, 2 = `UART_TX`(Pi GPIO14 TXD, J1 8번), 3 = `UART_RX`(Pi GPIO15 RXD, J1 10번), 직렬 부품 없음, 3.3V 레벨. 위치 J9 (10.5, −48.42): J1 6/8/10번 핀과 같은 높이, 실크 "GND TX RX". 부품면(뒤판 쪽)이라 뒤판을 열면 바로 닿음
- 마운팅 홀: v07과 동일 5개 M2.5 (보드 작업 때 반영; 회로도엔 Mechanical:MountingHole ×5 선택)

## 6. 수동부품 기본 풋프린트
R: Resistor_SMD:R_0603_1608Metric / C: Capacitor_SMD:C_0603_1608Metric (10µF·22µF는 C_0805_2012Metric) / LED: LED_SMD:LED_0603_1608Metric / FB: Inductor_SMD:L_0805_2012Metric
(2026-11-08 변경) LCSC·MPN 필드를 `v08_parts.md` 기준으로 모두 채움. 비워 둔 것: 손납땜 핀헤더(J1, J4~J7), 마운팅 홀(H1~H5), 솔더점퍼 JP1(동박만, BOM 제외). (2026-11-08 A3 케이스 반영) J4~J7은 라이트앵글 헤더 LCSC 번호를 채움(5절). J9 디버그 패드는 DNP·BOM 제외. 10µF는 전부 0805 25V C15850(Basic). 220µF(C970695)는 D6.3x7.7이라 풋프린트를 CP_Elec_6.3x7.7로 맞춤. BOM: `radio-hat-v08/radio-hat-v08_bom.csv`

## 7. 참조번호 규칙
U1 TP4056, U2 DW01A, U3 WSP8814(Winsok), U4 TPS61023, U5 ADS1115, U6 PCM5102A, U7 MAX98357A / Q1 AO3401A(로드셰어), Q2 2N7002(CE) / D1 SS34 / L1 / J1 Pi, J2 USB-C, J3 BAT, J4 SW, J5 LCD, J6 ENC, J7 SPK, J8 HP / JP1 GAIN / R·C·LED·FB 번호는 순서대로. 잭 감지용 R23·C25 추가 (2026-11-08 변경; (2026-11-08 변경 2차)에 4.7k·22µF로 값 변경). (2026-11-08 변경 2차) 추가 부품: R24(VBUS 풀다운 10k), C26(피드포워드 330pF), C27(부스트 입력 22µF), D4(VBUS TVS)

## 8. 검토 메모(사용자 확인 필요)
- ~~MAX98357A SD_MODE 전압 구간 확인~~ → 데이터시트로 확인 완료, 1.8k로 구간 중앙에 맞춤 (2026-11-08 변경)
- ~~헤드폰 잭 그라운드 스위치 타입~~ → JLCPCB에 없음. PJ-307C 팁 NC 스위치 방식으로 변경(4.2절) (2026-11-08 변경). 미삽입 시 HP_DET ≈0.28V((2026-11-08 변경 2차), 4.7k/22µF; LOW 판정 문턱 0.8V 이하)는 계산값이므로 시제품에서 측정 확인, 소프트웨어는 수백 ms 디바운스 권장
- PCM5102A 라인아웃으로 32Ω 헤드폰 직결은 v07(UDA1334)과 같은 조건(음량 낮을 때 OK). 100Ω 직렬저항으로 과부하 완화
- **사용자 결정: 1A 유지 — 충전하며 큰 음량 재생 시 3A 충전기 권장** (2026-11-08 변경 2차). 계산(감사 M4): 평상시 USB 합계 약 1.7A, 큰 음량 피크 약 2.85A이고 TP4056에는 입력 전류 제한이 없음. 충전 전류를 1A로 올렸으므로 (2026-11-08 변경) **충전하면서 Pi를 구동하려면 최소 5V 2A USB 충전기가 필요**하다(충전 1A + Pi·앰프 부하). 500mA USB-A 포트에서는 전류 부족으로 VBUS가 처질 수 있음. 또 TP4056이 1A에서 발열(5V→3.7V 차이 × 1A ≈ 1.3W)로 열 조절에 들어갈 수 있으니 EPAD 아래 동박·비아를 넉넉히

## 9. 케이스 안 보드 방향과 배치 (2026-11-08 A3 케이스 반영)
- 보드는 케이스 뒷벽에 세로로 서고 **부품면이 뒷벽을 본다**(부품면과 뒷벽 사이 약 17 mm, 반대쪽 납땜면은 스피커 칸막이와 약 3 mm → 납땜면에는 3 mm 이하로 자른 THT 다리만). 뒤에서 보면 KiCad 윗면 그림과 똑같이 보인다.
- 변 대응: KiCad **위 변**(y −64.9, H3/H4) = 케이스 **위 벽** → 이어폰 잭 J8. KiCad **아래 변**(y +5.08, H2/H5) = 케이스 **아래**(배터리 위 약 3 mm; KiCad x 38~63.6 아래는 높이 약 15 mm 빈 바닥) → 배터리 J3만 아래에서 꽂음(XH 플러그는 헤더 앞면에서 약 2.8 mm 나오고 전선 꺾임 포함 약 9~11 mm로 15 mm 안). 스피커 J7은 보드 안 플러그 공간(4.3절). KiCad **오른쪽 변**(x 63.48, H1) = 케이스 **왼쪽 벽**(간격 0.5 mm) → USB-C J2, 충전 LED D2/D3. KiCad **왼쪽 변** = J1 라이트앵글 헤더로 Pi와 연결.
- 블록: 위 왼쪽 = 이어폰 잭 + 헤드폰 DAC(U6) + 디버그 패드 J9, 위 오른쪽 = 부스트(U4/L1/C8), 오른쪽 가운데 = USB-C + 충전기(U1) + 로드셰어(D1/Q1) + ADC(U5), 왼쪽 가운데~아래 = 라이트앵글 헤더 J4/J6/J5와 플러그 공간, 아래 가운데 = 스피커 앰프(U7) + J7과 그 플러그 공간(x 37.8~44.0, y −10.2~+4.8), 아래 오른쪽 = 배터리 보호(U2/U3) + J3.
- 케이스 보스(H1~H5, Ø5.5, 뒷벽에서 부품면으로): 모든 부품 courtyard가 홀 중심에서 3.25 mm(= 2.75 + 0.5) 이상 떨어짐(`place_A3.py` 검사).
- 발열(A3_review P5): U1 TP4056(y −44), D1 SS34(y −46), U4/L1(y −53.5)은 모두 보드 위쪽 절반(KiCad y < −35, 케이스 위쪽)에 있음.
- 케이스 모델용 좌표(풋프린트 원점, KiCad mm): J2 (60.78, −47.80) r90, D2 (62.63, −36.95), D3 (62.63, −32.95), J8 (16.00, −61.40) r−90, J3 (47.50, −4.17) r0, J9 (10.50, −48.42), J7 (42.20, −14.20) r−90.
- 배치 결과 그림: `radio-hat-v08/placement_top.png`, `placement_blocks.png`. 배치 재현: `sch_A3.py` → `place_A3.py`(백업 `*.bak_before_A3`에서 다시 만듦). 배선은 아직 안 함.
