# v08 부품 재고 점검 (2026-11-12)

출처: LCSC 부품 페이지(https://www.lcsc.com/product-detail/<번호>.html)의 재고(inventoryLevel)와 JLCPCB 부품 페이지(https://jlcpcb.com/partdetail/<번호>)의 부품 종류 표기. 일반 fetch만 사용, 차단 없음.
- **재고는 LCSC 페이지 값**이다. JLCPCB 부품 페이지는 재고 수치를 자바스크립트로 따로 불러와서 정적 HTML로는 읽지 못했다(JLC 조립 재고는 보통 LCSC와 같은 창고지만 같다고 보장은 못 함 → 주문 직전 JLC 부품 검색에서 한 번 더 볼 것).
- 종류: JLC 페이지 표기 그대로. 'Preferred Extended'로 표시된 부품은 없었다(페이지에 Basic/Extended만 나옴 — Preferred 여부는 JLC 부품 검색 필터로 확인 필요).

## 문제 요약

1. **U6 PCM5102APWR (C107671): LCSC 재고 0.** JLC 쪽 재고 확인 못함. 대체 후보: PCM5101APWR(C2667024, 재고 2,022 — JLC 페이지 유사 부품 목록 값), 같은 PCM510x 계열 TSSOP-20이라 핀 배치는 같지만 SNR이 낮고 PLL/필터 사양이 다르므로 데이터시트 대조 후 결정. PCM5102PWR(C17598262)도 재고 0.
2. **C23, C24 220pF (C1603, CL10B221KB8NNNC): LCSC 재고 0, Basic 부품.** JLC 쪽 재고 확인 못함. 같은 0603 220pF 50V면 아무 제조사 것으로 바꿔도 된다(풋프린트 동일) — JLC 부품 검색에서 '220pF 0603' Basic 필터로 재고 있는 것을 고를 것. 번호를 내가 추측해 적지는 않았다.
3. 재고 200 미만은 위 둘뿐. 낮은 편(1만 미만): L1 C53426685 1,065 / C85840 FB 4,120 / C919459 TPS61023 5,595 / C37593 ADS1115 11,730 — 지금은 충분하지만 주문을 미루면 다시 볼 것.

## 표

| Ref | LCSC | 종류(Basic/Extended) | 재고(LCSC) | 비고 |
|---|---|---|---|---|
| C1-C3,C5,C15,C21 | C15850 (10uF) | Basic | 1,789,980 |  |
| C4,C11-C14,C22 | C14663 (0.1uF) | Basic | 13,400 |  |
| C6,C7,C25,C27 | C45783 (22uF) | Basic | 609,720 |  |
| C8 | C970695 (220uF) | Extended | 29,560 |  |
| C9,C10 | C14663 (100nF) | Basic | 13,400 |  |
| C16-C18 | C23630 (2.2uF) | Basic | 1,135,750 |  |
| C19,C20 | C1604 (2.2nF) | Basic | 19,100 |  |
| C23,C24 | C1603 (220pF) | Basic | 0 | **재고 0 — 대체 필요** |
| C26 | C1664 (330pF) | Basic | 260,450 |  |
| D1 | C8678 (SS34) | Basic | 1,955,040 |  |
| D2 | C965860 (RED) | Extended | 213,050 |  |
| D3 | C965863 (GREEN) | Extended | 192,900 |  |
| D4 | C2925443 (SMAJ5.0A) | Extended | 95,160 |  |
| FB1,FB2 | C85840 (FerriteBead) | Extended | 4,120 |  |
| J1 | - | - | - | BOM에 LCSC 없음(J1은 보드에 직접 실장하지 않는 헤더로 추정, 확인 필요) |
| J2 | C165948 (USB_C_Receptacle_USB2.0_16P) | Extended | 263,780 |  |
| J3 | C157931 (BAT) | Extended | 63,360 |  |
| J4 | C492411 (PWR_SW) | Extended | 86,380 |  |
| J5 | C492416 (LCD) | Extended | 25,100 |  |
| J6 | C492413 (ENC) | Extended | 37,040 |  |
| J7 | C492410 (SPK) | Extended | 170,120 |  |
| J8 | C16684 (PJ-307C) | Extended | 13,400 |  |
| L1 | C53426685 (1uH) | Extended | 1,065 |  |
| Q1 | C15127 (AO3401A) | Basic | 1,186,980 |  |
| Q2 | C8545 (2N7002) | Basic | 5,534,400 |  |
| R1,R2 | C23186 (5.1k) | Basic | 14,439,800 |  |
| R3 | C22765 (1.2k) | Basic | 1,416,500 |  |
| R4,R5,R9 | C21190 (1k) | Basic | 3,509,100 |  |
| R6,R18,R21,R24 | C25804 (10k) | Basic | 3,705,000 |  |
| R7,R10,R13-R17 | C25803 (100k) | Basic | 6,188,300 |  |
| R8,R19,R20 | C22775 (100) | Basic | 1,648,400 |  |
| R11 | C23192 (510k) | Basic | 355,800 |  |
| R12 | C23231 (68k) | Basic | 406,200 |  |
| R22 | C4177 (1.8k) | Basic | 310,600 |  |
| R23 | C23162 (4.7k) | Basic | 2,456,100 |  |
| U1 | C16581 (TP4056) | Extended | 70,690 |  |
| U2 | C351410 (DW01A) | Extended | 92,220 |  |
| U3 | C148371 (WSP8814) | Extended | 1,970 |  |
| U4 | C919459 (TPS61023) | Extended | 5,595 |  |
| U5 | C37593 (ADS1115IDGS) | Extended | 11,730 |  |
| U6 | C107671 (PCM5102A) | Extended | 0 | **재고 0 — 대체 필요** |
| U7 | C910544 (MAX98357A) | Extended | 28,659 |  |

## WSP8814 (U3, C148371) 핀 배치

데이터시트: Winsok WSP8814 (Dec.2014), LCSC 호스팅 PDF `https://datasheet.lcsc.com/datasheet/pdf/15bb62ca00b34efa8a0eadd6bd5dd55a.pdf?productCode=C148371` 1쪽 'TSSOP-8 Pin Configuration' 그림(PDF를 받아 그림을 직접 봄).

| 핀 | 데이터시트 | 보드(pcbnew 읽기) |
|---|---|---|
| 1 | D (공통 드레인) | /FET_D |
| 2, 3 | S1 | /B- |
| 4 | G1 | /OD |
| 5 | G2 | /OC |
| 6, 7 | S2 | GND |
| 8 | D (공통 드레인) | /FET_D |

**판정: 일치.** 1·8번이 드레인(내부에서 두 FET 드레인이 묶임), S1 = 2·3, G1 = 4, G2 = 5, S2 = 6·7. 8205A와 같은 배열이다. 보드의 U3 회전은 180°(핀 번호는 풋프린트 기준이므로 영향 없음). 데이터시트의 핀 번호 위치(그림의 핀 1 = 칩 왼쪽 아래 기준 D)는 TSSOP-8 표준과 같다. S1에 B-, G1에 OD를 잇는 연결은 DW01A + 8205A 표준 회로와 같은 쪽이다. 최종 검토 S3 확인 완료로 닫아도 된다. 참고: JLC 페이지의 종류는 Extended.

## D2/D3 측면 LED 극성 (최종 검토 M1)

확인한 자료: LCSC C965860 페이지의 제품 사진 3장(front/back/blank, `assets.lcsc.com/images/lcsc/900x900/20230131_XINGLIGHT-XL-1606SURC_C965860_*.jpg`), LCSC 데이터시트 PDF(`datasheet.lcsc.com/datasheet/pdf/474b7d3c9b2c2c1299854fcb6f1a7cfb.pdf`) 7쪽 외형 치수, JLC/LCSC 설명 문구('Red 625nm LED Indication - Discrete 2.4V SMD, 1.7x1.1mm'). UGC(C965863)는 같은 제조사·같은 패키지라 따로 보지 않음.

- 설명 문구에는 핀/렌즈 방향 정보가 없다. JLC/LCSC 풋프린트 설명도 페이지에 따로 없다.
- 7쪽 도면: 극성 기호에서 ②=애노드(+), ①=캐소드(−). 윗면도·밑면도 모두 ② 왼쪽, ① 오른쪽. 밑면도에서 초록 표시는 ① 쪽 가까이(패드 ① 안쪽). 앞면도(렌즈가 위로 솟은 그림)에서는 초록 표시가 오른쪽(① 쪽)에 있음. 권장 패드 그림에서는 렌즈 윤곽이 위쪽이고 초록 표시가 오른쪽 패드 쪽 — 최종 검토에서 읽은 것과 같다.
- 제품 사진 back: 초록 사각 표시가 한쪽 끝에 붙어 있고(밑면의 캐소드 표시로 보임) 렌즈 돌기가 부품 반대쪽 끝 방향에 있다. 사진 해상도·시점이 낮아 렌즈 쪽에서 봤을 때 그 표시가 좌/우 어느 쪽인지는 단정할 수 없다. front 사진은 렌즈 면이지만 극성 표시가 없다.
- **결론: 결정적인 증거 없음.** 도면 7쪽의 앞면도 기준(렌즈를 마주 봤을 때 캐소드 ① = 오른쪽)이 가장 직접적이지만 최종 검토가 지적한 대로 다른 그림과 충돌 여부가 남는다. 확실히 하려면 (a) 시제품 LED를 멀티미터 다이오드 모드로 직접 확인(초록 표시 쪽 = 캐소드가 일반적), 또는 (b) 보드 주문 전에 LED 2개를 따로 사서 렌즈 방향과 표시를 눈으로 확인.

## 부록: 스크래치

`/private/tmp/claude-502/-Users-giy-Projects-weatherReport-wr-radio/049b7745-a306-46b5-8ea2-34051b46fbe4/scratchpad/stock/` (받은 HTML, 데이터시트, 사진)
