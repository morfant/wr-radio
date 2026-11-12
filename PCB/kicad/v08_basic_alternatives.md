# v08 Extended 부품 수수료 절감 조사 (2026-11-12)

방법: JLCPCB 부품 페이지(https://jlcpcb.com/partdetail/<번호>)의 HTML에 들어 있는 `componentLibraryType`(base = Basic, expand = Extended)와 `preferredComponentFlag`를 읽음. LCSC 페이지(https://www.lcsc.com/product-detail/<번호>.html)의 `inventoryLevel`로 재고 확인. 일반 요청만 사용. bom.csv 등 설계 파일은 수정하지 않음.
- 주의: `preferredComponentFlag`는 모든 부품에서 비어 있었다(= Preferred Extended 표시 없음). 다만 이 필드가 Preferred 표시를 정확히 담는지는 확인 못함 → 주문 화면(BOM 업로드 후 부품 종류 열)에서 최종 확인할 것.
- 재고는 LCSC 값이다(JLC 조립 재고와 다를 수 있음).

## 1. BOM의 Extended 부품 현재 등급 (전부 일반 Extended)

| Ref | LCSC | 부품 | JLC 등급 | LCSC 재고 |
|---|---|---|---|---|
| C8 | C970695 | 220µF 16V 6.3x7.7 | Extended | 29,560 (이전 점검) |
| D2 | C965860 | 측면 LED 적 | Extended | 213,050 |
| D3 | C965863 | 측면 LED 녹 | Extended | 192,900 |
| D4 | C2925443 | SMAJ5.0A | Extended | 95,160 |
| FB1,FB2 | C85840 | BLM21PG221SN1D 0805 220Ω 2A | Extended | 4,120 |
| J2 | C165948 | USB-C HRO TYPE-C-31-M-12 | Extended | 263,780 |
| L1 | C53426685 | 1µH FXL0420 | Extended | 1,065 |
| U1 | C16581 | TP4056 | Extended | 70,690 |
| U2 | C351410 | DW01A | Extended | 92,220 |
| U3 | C148371 | WSP8814 | Extended | 1,970 |
| U4 | C919459 | TPS61023 | Extended | 5,595 |
| U5 | C37593 | ADS1115IDGS | Extended | 11,730 |
| U6 | C107671 | PCM5102APWR | Extended | **0** |
| U7 | C910544 | MAX98357A | Extended | 28,659 |

고유 Extended 14종 = 약 $42. (J3~J8 등 커넥터는 이 bom.csv에 없음 — 별도 실장/수배선이면 이 계산에 포함 안 됨.)

## 2. 후보 비교

| Ref | 현재 LCSC | 현재 등급 | 후보 LCSC | 후보 등급 | 재고 | 비교/근거 | 추천 |
|---|---|---|---|---|---|---|---|
| U3 | C148371 | Extended | 8205A TSSOP-8 전부 (C14212 FS, C16052 FS, C181100 Hottech, C5148694 HXY, C7499846 HL ...) | **전부 Extended** (C14212, C16052, C181100 직접 확인) | - | Basic/Preferred인 TSSOP-8 듀얼 N-FET을 못 찾음. 설령 있어도 8205A급(Rds 27~38mΩ)은 감사 M2에서 과전류 차단이 2~3A로 내려가 부적합 판정(스펙 2.3절) | 교체 안 함 |
| FB1,FB2 | C85840 | Extended | C1002 (Sunlord GZ1608D601TF) | Basic | 있음 | **0603**, 600Ω, 정격 200mA, DCR 450mΩ — 풋프린트 다르고 스피커 전류(수백 mA~A)에 부족 | 불가 |
| C8 | C970695 | Extended | 6.3x7.7 SMD 전해 중 Basic 없음 | - | - | 검색에서 Basic SMD 220µF 못 찾음(찾은 것은 전부 Extended 또는 삽입형) | 교체 안 함 |
| C23,C24 | C1603 (CL10B221KB8NNNC, X7R 50V) | Basic | (a) C1664 330pF C0G 50V | Basic | 260,450 | 같은 0603, **추가 Extended 없음**. SPK 출력 EMI 필터용이라 220→330pF은 차단 주파수가 낮아질 뿐(페라이트 220Ω과 RC ≈ 2 MHz대) 동작 문제 없음. 이미 C26에 쓰는 번호라 BOM 줄도 줄어든다. 단, 값 변경이므로 사용자 판단 필요 | **추천(a)** |
| | | | (b) C107081 Yageo CC0603KRX7R9BB221 | **Extended** | 973,300 | 220pF 그대로지만 Extended라 +$3 | 비추 |
| | | | (c) C16194546 Samsung CL10B221KB8NFNC | Extended | 50,300 | 같은 이유 +$3 | 비추 |
| | | | (d) C14858 100pF C0G | Basic | 302,000 | 값이 절반 — 필터 효과 약함 | 차선 |
| | | | C0G 220pF (C440180, C342909) | - | 0 | 재고 0. C452747 KEMET은 재고 60 | 불가 |
| U6 | C107671 | Extended | C2667024 PCM5101APWR | **Extended** | 2,020 | TSSOP-20 동일 핀 배치, 같은 TI PCM510xA 계열. Basic 아님 → 수수료 변화 없음, 재고만 해결 | 재고 때문에 교체 필요(수수료는 그대로 $3) |
| L1, J2, D2/D3, U1, U2, U4, U5, U7, D4 | - | Extended | 없음 | - | - | IC·전용 커넥터·특수 LED는 같은 풋프린트의 Basic이 없음(JLC Basic 라이브러리에 해당 종류 없음) | 교체 안 함 |

U6 참고: PCM5101A는 PCM5102A와 데이터시트가 같지만 SNR 등이 한 단계 낮다. 이 용도(소형 스피커/헤드폰)에서는 문제 없다고 본다. 주문 전 BOM 번호를 C2667024로 바꾸는 것은 사용자 결정.

## 3. 예상 절감

- 확인된 Basic/Preferred 대체 가능 건: **0건** → 수수료 절감 **$0**. 현재 약 $42(14종) 그대로.
- 후보를 찾지 못한 이유: 남은 Extended는 IC·전용 커넥터·LED·인덕터·페라이트·전해 콘덴서이고, 같은 풋프린트·정격의 Basic이 없다.
- 큰 절감을 하려면 풋프린트 변경이 필요하다(범위 밖): 예) 페라이트를 0603 Basic으로, 측면 LED를 0603 Basic LED로.
- C23/C24는 C1603 재고 0 문제만 있고, C1664로 바꾸면 수수료 증가 없이 해결.

## 4. 확인 못함

- Preferred Extended 여부(위 주의 참고). JLC 조립 재고(LCSC 값만 확인).
- C1603의 JLC 쪽 재고: 페이지에서 읽지 못했다.
