#!/usr/bin/env python3
"""WR-Radio case layout concepts A/B/C1/C2. All coordinates in INNER frame (mm):
x = left->right, y = front->rear, z = bottom->top. Inner origin = front/left/bottom inner corner.
Wall T=3 mm; case outer = inner +/- T. Run: python3 concepts.py"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

plt.rcParams["font.family"] = ["Apple SD Gothic Neo", "AppleGothic", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
OUT = os.path.dirname(os.path.abspath(__file__))
T = 3.0
COL = dict(spk="#f28e2b", spk2="#fbc78c", lcd="#4e79a7", enc="#59a14f", sw="#b07aa1",
           bat="#edc948", pi="#8cd17d", hat="#76b7b2", flex="#1f3b5c")


def P(name, box, col, lv="FTR", shape="box", axis=None, dashed=False, label=None, alpha=None):
    return dict(name=label or name, box=box, col=col, lv=lv, shape=shape, axis=axis, dashed=dashed, alpha=alpha)


def cyl(cx, cy, cz, d, ln, axis, y_or_z0):
    """cylinder centered (cx,cy,cz) in the two non-axis dims, from axis coord y_or_z0 length ln."""
    r = d / 2
    if axis == "z":
        return (cx - r, cx + r, cy - r, cy + r, y_or_z0, y_or_z0 + ln)
    if axis == "y":
        return (cx - r, cx + r, y_or_z0, y_or_z0 + ln, cz - r, cz + r)
    return (y_or_z0, y_or_z0 + ln, cy - r, cy + r, cz - r, cz + r)


def concept_A():
    Wi, Di, Hi = 122.0, 71.0, 96.0  # LCD landscape 50 wide: 66+3+50+3(flex bend gap)
    bx0 = Wi - 0.5 - 101  # 20.5
    lcx = 94.0  # LCD centre x (69..119)
    parts = [
        P("배터리 90×52×12", (26, 116, 9.5, 61.5, 0, 12), COL["bat"], label="배터리 90×52×12"),
        P("Pi Zero", (bx0, bx0 + 30, 3, 68, 12, 27), COL["pi"], label="Pi Zero", lv="F"),
        P("HAT", (bx0 + 37.5, bx0 + 101, 0.5, 70.5, 12, 27), COL["hat"], label="HAT 63.5×70", lv="F"),
        P("스피커 유닛 27", (0, 66, 0, 27, 30, 96), COL["spk"], lv="F", label="스피커 66×66"),
        P("챔버 16", (0, 66, 27, 43, 30, 96), COL["spk2"], lv="TR", label="챔버16\n유닛27"),
        P("LCD", (69, 119, 0, 8, 45.25, 80.75), COL["lcd"], label="LCD 50×35.5"),
        P("flex", (119, 121.5, 3.2, 4.0, 53, 73), COL["flex"], lv="FT", label=""),
        P("flex", (120.7, 121.5, 4.0, 23.2, 53, 73), COL["flex"], lv="FT", label=""),
        P("엔코더 body", cyl(94, 24, 0, 26, 30, "z", 66), COL["enc"], shape="cyl", axis="z", label="엔코더\nø26×30"),
        P("knob", cyl(94, 24, 0, 27, 25, "z", 99), COL["enc"], shape="cyl", axis="z", dashed=True, label="노브ø27", lv="FR"),
        P("스위치", (60, 73, 51, 71, 28, 35), COL["sw"], label="스위치\n13×7×20"),
        P("bushing", cyl(66.5, 0, 31.5, 6.13, 6, "y", 74), COL["sw"], shape="cyl", axis="y", dashed=True, label=""),
    ]
    xs = 85  # USB-C x
    marks = [
        dict(v="T", rect=(93.5, 102.5, 71, 74), shape="rect", txt="USB-C 충전", at=(141, 66)),
        dict(v="R", rect=(71, 74, 17.5, 21.5), shape="rect", txt="", at=None),
        dict(v="T", rect=(122, 125, 32.5, 38.5), shape="rect", txt="이어폰 잭", at=(141, 40)),
        dict(v="T", rect=(66.5 - 3.07, 66.5 + 3.07, 74, 80), shape="rect", txt="전원 스위치", at=(141, 84), fill=False),
        dict(v="F", rect=(94 - 17.8, 94 + 17.8, 63 - 16.15, 63 + 16.15), shape="rect", txt="LCD 창", at=(138, 70), fill=False),
        dict(v="F", rect=(33 - 28, 33 + 28, 63 - 28, 63 + 28), shape="circ", txt="스피커 그릴", at=(33, 110), fill=False),
        dict(v="F", rect=(94 - 13.5, 94 + 13.5, 99, 124), shape="rect", txt="엔코더", at=(138, 110), fill=False),
    ]
    return dict(key="A", title="A. 가로 탁상형", inner=(Wi, Di, Hi), parts=parts, marks=marks, flex_note="LCD 플렉스: 우측(+X)으로 나와 3mm 틈에서 뒤(+Y)로 꺾임", extra="LCD 가로 50×35.5. 노브 +25 (높이 방향), 스위치 부싱 +6 (뒤)")


def concept_A2():
    """A2: like A but Pi+HAT stands vertically (101 X, 70 Z, 15 Y) against the rear wall.
    Battery flat under speaker+board (z0-12), so speaker/board are raised 15. Encoder on top behind LCD."""
    Wi, Di, Hi = 122.0, 61.5, 85.5
    zb = 15.0  # raised floor plane (battery 12 + gap 3)
    lzc = 48.0  # LCD / speaker centre height
    parts = [
        P("배터리 90×52×12", (16, 106, 9.5, 61.5, 0, 12), COL["bat"], label="배터리 90×52×12"),
        P("Pi Zero", (20.5, 50.5, 46, 61, zb + 2.5, zb + 67.5), COL["pi"], label="Pi Zero", lv="F"),
        P("HAT", (58, 121.5, 46, 61, zb, zb + 70), COL["hat"], label="HAT 63.5×70", lv="F"),
        P("스피커 유닛 27", (0, 66, 0, 27, zb, zb + 66), COL["spk"], lv="F", label="스피커 66×66"),
        P("챔버 16", (0, 66, 27, 43, zb, zb + 66), COL["spk2"], lv="TR", label="챔버16\n유닛27"),
        P("LCD", (69, 119, 0, 8, lzc - 17.75, lzc + 17.75), COL["lcd"], label="LCD 50×35.5"),
        P("flex", (119, 121.5, 3.2, 4.0, lzc - 10, lzc + 10), COL["flex"], lv="FT", label=""),
        P("flex", (120.7, 121.5, 4.0, 23.2, lzc - 10, lzc + 10), COL["flex"], lv="FT", label=""),
        P("엔코더 body", cyl(94, 24, 0, 26, 30, "z", Hi - 30), COL["enc"], shape="cyl", axis="z", label="엔코더\nø26×30"),
        P("knob", cyl(94, 24, 0, 27, 25, "z", Hi + T), COL["enc"], shape="cyl", axis="z", dashed=True, label="노브ø27", lv="FR"),
        P("스위치", (101.5, 121.5, 28, 41, 20, 27), COL["sw"], label="스위치"),
        P("bushing", cyl(0, 34.5, 23.5, 6.13, 6, "x", Wi + T), COL["sw"], shape="cyl", axis="x", dashed=True, label=""),
    ]
    marks = [
        dict(v="F", rect=(94 - 17.8, 94 + 17.8, lzc - 16.15, lzc + 16.15), shape="rect", txt="LCD 창", at=(135, 100), fill=False),
        dict(v="F", rect=(33 - 28, 33 + 28, lzc - 28, lzc + 28), shape="circ", txt="스피커 그릴", at=(33, 100), fill=False),
        dict(v="F", rect=(122, 125, zb + 30.5, zb + 35.5), shape="rect", txt="", at=None),
        dict(v="T", rect=(94 - 13.5, 94 + 13.5, 24 - 13.5, 24 + 13.5), shape="rect", txt="엔코더(상단)", at=(30, 80), fill=False),
        dict(v="T", rect=(122, 125, 50, 57), shape="rect", txt="USB-C 충전", at=(142, 56)),
        dict(v="T", rect=(86, 94, 49.5, 57.5), shape="rect", txt="이어폰 잭", at=(98, 80)),
        dict(v="R", rect=(49.5, 57.5, Hi, Hi + T), shape="rect", txt="이어폰 잭", at=(75, 100)),
        dict(v="T", rect=(Wi, Wi + T + 6, 31, 38), shape="rect", txt="전원 스위치", at=(142, 25), fill=False),
    ]
    return dict(key="A2", title="A2. 가로 탁상형 (보드 세움)", inner=(Wi, Di, Hi), parts=parts, marks=marks,
                flex_note="LCD 플렉스: 우측(+X)으로 나와 3mm 틈에서 뒤(+Y)로 꺾임",
                extra="Pi+HAT 세움(15 두께, 뒷벽). 배터리는 스피커·보드 아래 눕힘(바닥 +15). 엔코더 상단. USB-C·스위치 우측, 이어폰 상단")


def concept_A3():
    """A3 (board flipped, option P1-2): board block stands against the rear wall with its COMPONENT SIDE toward the rear.
    Depth (outer) = 3 + 27 + 12 + 2(cup back) + 2(gap) + 3(trimmed leads) + 1.6(PCB) + 17(parts+cables) + 3 = 70.6.
    Speaker chamber = sealed 5-sided cup (2 mm walls; left side = case wall). Switch raised to z66-73."""
    Wi, Hi = 122.0, 85.5
    zb = 15.0
    lzc = 48.0
    ch1 = 27 + 12            # speaker unit 27 + chamber 12 = 39
    pt1 = ch1 + 2            # cup back wall 2 -> 41
    ld0 = pt1 + 2            # 43: 2 mm gap, then trimmed-lead zone
    pc0 = ld0 + 3            # 46: PCB front face (leads 3 mm)
    pc1 = pc0 + 1.6          # 47.6: PCB rear (component) face
    Di = pc1 + 17            # 64.6: rear wall inner face (17 mm parts+cable space)
    sw_y, sw_z = 55.6, 69.5  # switch bushing centre
    parts = [
        P("배터리 90×52×12", (26, 116, 3, 55, 0, 12), COL["bat"], label="배터리 90×52×12"),
        P("Pi Zero (SD 끝 위)", (71.5, 101.5, pc0, pc1, zb + 2.5, zb + 67.5), COL["pi"], lv=""),
        P("HAT", (0.5, 64, pc0, pc1, zb, zb + 70), COL["hat"], lv=""),
        P("스피커 유닛 27", (0, 66, 0, 27, zb, zb + 66), COL["spk"], lv="F", label="스피커 66×66"),
        P("챔버 12", (0, 66, 27, ch1, zb, zb + 66), COL["spk2"], lv="TR", label="챔버12\n유닛27"),
        # sealed five-sided cup (2 mm walls): back, top, bottom, right (left = case wall)
        P("밀폐 챔버(컵)", (0, 68, ch1, pt1, zb - 2, zb + 68), "#9c8a6b", lv="", label="밀폐 챔버(컵)"),
        P("밀폐 챔버(컵)", (0, 68, 27, ch1, zb + 66, zb + 68), "#9c8a6b", lv="", label="밀폐 챔버(컵)"),
        P("밀폐 챔버(컵)", (0, 68, 27, ch1, zb - 2, zb), "#9c8a6b", lv="", label="밀폐 챔버(컵)"),
        P("밀폐 챔버(컵)", (66, 68, 27, ch1, zb, zb + 66), "#9c8a6b", lv="", label="밀폐 챔버(컵)"),
        P("LCD", (69, 119, 0, 8, lzc - 17.75, lzc + 17.75), COL["lcd"], label="LCD 50×35.5"),
        P("flex", (119, 121.5, 3.2, 4.0, lzc - 10, lzc + 10), COL["flex"], lv="FT", label=""),
        P("flex", (120.7, 121.5, 4.0, 23.2, lzc - 10, lzc + 10), COL["flex"], lv="FT", label=""),
        P("엔코더 body", cyl(94, 24, 0, 26, 30, "z", Hi - 30), COL["enc"], shape="cyl", axis="z", label="엔코더\nø26×30"),
        P("knob", cyl(94, 24, 0, 27, 25, "z", Hi + T), COL["enc"], shape="cyl", axis="z", dashed=True, label="노브ø27", lv="FR"),
        P("스위치", (102, 122, sw_y - 6.5, sw_y + 6.5, 66, 73), COL["sw"], label="스위치"),
        P("bushing", cyl(0, sw_y, sw_z, 6.13, 6, "x", Wi + T), COL["sw"], shape="cyl", axis="x", dashed=True, label=""),
        P("배터리 커넥터", (14, 17, pc1, pc1 + 9, 4, zb), "#d9534f", label="배터리\n커넥터", lv="F"),
        # translucent clearance volumes
        P("커넥터·케이블 공간 17", (0.5, 101.5, pc1, Di, zb, zb + 70), "#a0c4ff", lv="TR", dashed=True, label="커넥터·케이블 공간 17", alpha=0.2),
        P("납땜 리드 공간 3", (0.5, 101.5, ld0, pc0, zb, zb + 70), "#ffd6a0", lv="", dashed=True, label="납땜 리드 공간 3", alpha=0.25),
    ]
    # 9 standoffs rear wall -> board (length 17, Ø5.5): HAT 5 holes, Pi 4 holes (approx. positions)
    for (hx, hz) in [(3.5, 18), (61, 18), (3.5, 82), (61, 82), (4.7, 49.2), (74.5, 21), (98.5, 21), (74.5, 79), (98.5, 79)]:
        parts.append(P("스탠드오프 Ø5.5×17", cyl(hx, 0, hz, 5.5, 17, "y", pc1), "#7f7f7f", shape="cyl", axis="y", lv="", label="스탠드오프"))
    # USB-C on LEFT wall: recess 13.5(Z)x7.5(Y)x2.2 deep, opening 9.6(Z)x3.8(Y), centred y=pc1+1.6, z=48
    uy, uz = pc1 + 1.6, 67.9   # J2 USB-C (KiCad 60.78,-47.8)
    ledz = (57.0, 53.0)         # D2/D3 (KiCad 62.63,-38/-34), y = pc1+0.6
    ly = pc1 + 0.6
    jx, jy = 48.1, pc1 + 3.0    # J8 jack (KiCad 16.0,-61.4), hole d7
    marks = [
        dict(v="F", rect=(94 - 17.8, 94 + 17.8, lzc - 16.15, lzc + 16.15), shape="rect", txt="LCD 창", at=(135, 100), fill=False),
        dict(v="F", rect=(33 - 28, 33 + 28, lzc - 28, lzc + 28), shape="circ", txt="스피커 그릴", at=(33, 100), fill=False),
        dict(v="F", rect=(-T, 0, uz - 4.8, uz + 4.8), shape="rect", txt="USB-C 충전", at=(-22, 80)),
        dict(v="F", rect=(-T, -0.8, uz - 6.75, uz + 6.75), shape="rect", txt="", at=None, fill=False),
        dict(v="F", rect=(-T, 0, ledz[0] - 1, ledz[0] + 1), shape="rect", txt="충전 LED", at=(-36, 47)),
        dict(v="F", rect=(-T, 0, ledz[1] - 1, ledz[1] + 1), shape="rect", txt="", at=None),
        dict(v="F", rect=(Wi, Wi + T, sw_z - 3.07, sw_z + 3.07), shape="rect", txt="", at=None),
        dict(v="F", rect=(5, 59, 17, 37), shape="rect", txt="환기(뒷벽)", at=(25, 8), fill=False),
        dict(v="F", rect=(5, 59, 64, 84), shape="rect", txt="", at=None, fill=False),
        dict(v="T", rect=(94 - 13.5, 94 + 13.5, 24 - 13.5, 24 + 13.5), shape="rect", txt="엔코더(상단)", at=(62, 78), fill=False),
        dict(v="T", rect=(-T, 0, uy - 1.9, uy + 1.9), shape="rect", txt="USB-C 충전", at=(-24, 72)),
        dict(v="T", rect=(-T, -0.8, uy - 3.75, uy + 3.75), shape="rect", txt="포켓 13.5×7.5×2.2", at=(-24, 36), fill=False),
        dict(v="T", rect=(jx - 3.5, jx + 3.5, jy - 3.5, jy + 3.5), shape="rect", txt="이어폰 잭", at=(30, 78)),
        dict(v="T", rect=(79.5, 93.5, 47.8, 50.8), shape="rect", txt="SD 카드 슬롯", at=(96, 72)),
        dict(v="T", rect=(Wi, Wi + T + 6, sw_y - 3.07, sw_y + 3.07), shape="rect", txt="전원 스위치", at=(136, 72), fill=False),
        dict(v="R", rect=(jy - 3.5, jy + 3.5, Hi, Hi + T), shape="rect", txt="이어폰 잭", at=(30, 98)),
        dict(v="R", rect=(47.8, 50.8, Hi, Hi + T), shape="rect", txt="SD 카드 슬롯", at=(70, 98)),
        dict(v="R", rect=(Di, Di + T, 17, 37), shape="rect", txt="환기", at=(84, 27)),
        dict(v="R", rect=(Di, Di + T, 64, 84), shape="rect", txt="환기", at=(84, 74)),
    ]
    notes = [
        dict(v="F", at=(86.5, 24), txt="Pi (SD 끝 위,\n부품면 뒤)"),
        dict(v="F", at=(32, 50.5), txt="HAT 63.5×70 (부품면 뒤)"),
        dict(v="F", at=(-18, 7), txt="배터리 커넥터", to=(15.5, 9)),
        dict(v="F", at=(40, 91), txt="디버그 패드 J9 (뒤판 열고 접근)", to=(53.6, 66)),
        dict(v="T", at=(100, 14), txt="밀폐 챔버(컵) 벽2", to=(34, 33)),
        dict(v="T", at=(-22, 20), txt="스탠드오프 Ø5.5×17", to=(3.5, 56)),
        dict(v="R", at=(14, 6), txt="밀폐 챔버(컵)", to=(33, 82)),
        dict(v="R", at=(56, 8), txt="스탠드오프 Ø5.5×17", to=(56, 18)),
    ]
    labels3d = [
        dict(txt="밀폐 챔버(컵)", pos=(34, 33, zb + 69)),
        dict(txt="커넥터·케이블 공간 17", pos=(51, 56, zb + 71)),
        dict(txt="스탠드오프 Ø5.5×17", pos=(61, 58, 50)),
        dict(txt="배터리 커넥터", pos=(15.5, 53, 1)),
        dict(txt="디버그 패드 J9", pos=(53.6, 50, 66)),
        dict(txt="납땜 리드 3", pos=(51, 44, zb + 2)),
    ]
    return dict(key="A3", title="A3. 추천안 (A2 + 챔버 컵, 보드 뒤집기②)", inner=(Wi, Di, Hi), parts=parts, marks=marks, notes=notes, labels3d=labels3d,
                flex_note="LCD 플렉스: 우측(+X)으로 나와 3mm 틈에서 뒤(+Y)로 꺾임 (Pi는 y46~ 뒤라 간섭 없음)",
                extra="깊이 3+27+12+2+2+3+1.6+17+3=70.6. 보드 부품면이 뒷벽 향함(스탠드오프17), 밀폐 챔버 컵, SD 슬롯 상단, 전원 스위치 우측 z66-73, USB-C 좌측 포켓")


def concept_B():
    Wi, Di, Hi = 71.0, 76.0, 134.5  # front stack 66+3+27+3+35.5; board block (102) no longer governs
    parts = [
        P("배터리", (9.5, 61.5, 46, 58, 0, 90), COL["bat"], label="배터리\n52×12×90"),
        P("Pi Zero", (0.5, 65.5, 61, 76, 33, 63), COL["pi"], label="Pi Zero", lv="F"),
        P("HAT", (0.5, 70.5, 61, 76, 70.5, 134), COL["hat"], label="HAT 70×63.5", lv="F"),
        P("스피커 유닛 27", (2.5, 68.5, 0, 27, 0, 66), COL["spk"], lv="F", label="스피커 66×66"),
        P("챔버 16", (2.5, 68.5, 27, 43, 0, 66), COL["spk2"], lv="TR", label="챔버16\n유닛27"),
        P("엔코더 body", cyl(35.5, 0, 82.5, 26, 30, "y", 0), COL["enc"], shape="cyl", axis="y", label="엔코더\nø26×30"),
        P("knob", cyl(35.5, 0, 82.5, 27, 25, "y", -25), COL["enc"], shape="cyl", axis="y", dashed=True, label="노브ø27", lv="FR"),
        P("LCD", (10.5, 60.5, 0, 8, 99, 134.5), COL["lcd"], label="LCD 50×35.5"),
        P("flex", (0.5, 10.5, 3.2, 4.0, 106.75, 126.75), COL["flex"], lv="FT", label=""),
        P("flex", (0.5, 1.3, 4.0, 14.0, 106.75, 126.75), COL["flex"], lv="FTR", label=""),
        P("스위치", (51, 71, 46, 59, 112, 119), COL["sw"], label="스위치\n20×13×7"),
        P("bushing", cyl(0, 52.5, 115.5, 6.13, 6, "x", 71 + 3), COL["sw"], shape="cyl", axis="x", dashed=True, label=""),
    ]
    marks = [
        dict(v="F", rect=(35.5 - 17.8, 35.5 + 17.8, 116.75 - 16.15, 116.75 + 16.15), shape="rect", txt="LCD 창", at=(-30, 125), fill=False),
        dict(v="F", rect=(35.5 - 13.5, 35.5 + 13.5, 69, 96), shape="rect", txt="엔코더", at=(-30, 90), fill=False),
        dict(v="F", rect=(2.5, 68.5, 0, 66), shape="circ", txt="스피커 그릴", at=(-30, 30), fill=False),
        dict(v="R", rect=(65, 72, 149, 152), shape="rect", txt="이어폰 잭", at=(90, 145)),
        dict(v="F", rect=(71, 74, 92.5, 112.5), shape="rect", txt="USB-C 충전", at=(95, 105)),
        dict(v="T", rect=(71, 74, 64, 72), shape="rect", txt="", at=None),
        dict(v="F", rect=(71, 74, 112, 119), shape="rect", txt="전원 스위치", at=(95, 125)),
    ]
    return dict(key="B", title="B. 세로형", inner=(Wi, Di, Hi), parts=parts, marks=marks, flex_note="LCD 플렉스: 좌측(-X)으로 10mm 나와 뒤(+Y)로 10mm 꺾임", extra="LCD 가로 50×35.5. 노브 +25 (앞), 스위치 부싱 +6 (우측)")


def _c_common(key, title, Di, Hi, parts, marks, extra):
    return dict(key=key, title=title, inner=(170.5, Di, Hi), parts=parts, marks=marks,
                flex_note="LCD 플렉스: 우측(+X)으로 2.5mm 나와 3mm 틈에서 뒤(+Y)로 꺾임", extra=extra)


def concept_C1():
    """C1: encoder on front, right of LCD. Hi 71 = Pi+HAT block 70 + 2x0.5 (speaker 66 centred)."""
    Hi, Di, zc = 71.0, 63.0, 35.5
    ex = 137.5  # encoder centre x: LCD right 119 + flex 2.5 + gap 3 + r13
    parts = [
        P("스피커 유닛 27", (0, 66, 0, 27, 2.5, 68.5), COL["spk"], lv="F", label="스피커 66×66"),
        P("챔버 9", (0, 66, 27, 36, 2.5, 68.5), COL["spk2"], lv="TR", label="챔버9\n유닛27"),
        P("Pi Zero", (69, 99, 33, 48, 3, 68), COL["pi"], label="Pi Zero", lv="F"),
        P("HAT", (106.5, 170, 33, 48, 0.5, 70.5), COL["hat"], label="HAT 63.5×70", lv="F"),
        P("배터리", (57.5, 147.5, 51, 63, 9.5, 61.5), COL["bat"], label="배터리 90×52×12"),
        P("LCD", (69, 119, 0, 8, zc - 17.75, zc + 17.75), COL["lcd"], label="LCD 50×35.5"),
        P("flex", (119, 121.5, 3.2, 4.0, zc - 10, zc + 10), COL["flex"], lv="FT", label=""),
        P("flex", (120.7, 121.5, 4.0, 23.2, zc - 10, zc + 10), COL["flex"], lv="FT", label=""),
        P("엔코더 body", cyl(ex, 0, zc, 26, 30, "y", 0), COL["enc"], shape="cyl", axis="y", label="엔코더\nø26×30"),
        P("knob", cyl(ex, 0, zc, 27, 25, "y", -25), COL["enc"], shape="cyl", axis="y", dashed=True, label="노브"),
        P("스위치", (150.5, 170.5, 12, 25, 12, 19), COL["sw"], label="스위치"),
        P("bushing", cyl(0, 18.5, 15.5, 6.13, 6, "x", 173.5), COL["sw"], shape="cyl", axis="x", dashed=True, label=""),
    ]
    marks = [
        dict(v="F", rect=(94 - 17.8, 94 + 17.8, zc - 16.15, zc + 16.15), shape="rect", txt="LCD 창", at=(94, 90), fill=False),
        dict(v="F", rect=(33 - 28, 33 + 28, zc - 28, zc + 28), shape="circ", txt="스피커 그릴", at=(33, 90), fill=False),
        dict(v="F", rect=(ex - 13.5, ex + 13.5, zc - 13.5, zc + 13.5), shape="rect", txt="엔코더", at=(140, 90), fill=False),
        dict(v="F", rect=(170.5, 173.5, 31, 36), shape="rect", txt="", at=None),
        dict(v="T", rect=(170.5, 173.5, 37, 44), shape="rect", txt="USB-C 충전", at=(160, 82)),
        dict(v="T", rect=(134.5, 142.5, 36.5, 44.5), shape="rect", txt="이어폰 잭", at=(128, 82)),
        dict(v="R", rect=(36.5, 44.5, Hi, Hi + T), shape="rect", txt="이어폰 잭", at=(80, 90)),
        dict(v="T", rect=(173.5 - 3, 173.5 + 6, 15, 22), shape="rect", txt="전원 스위치", at=(190, 40), fill=False),
    ]
    return _c_common("C1", "C1. 엔코더 정면 옆", Di, Hi, parts, marks,
                     "정면 스피커·LCD·엔코더 한 줄. 노브 중심 높이 책상 위 38.5mm. 배터리는 보드 뒤. 노브 +25 (앞), 부싱 +6 (우측)")


def concept_C2():
    """C2: encoder on top (knob up), above LCD. LCD low (z 2.5-38) so body z41-71 clears it by 3."""
    Hi, Di = 71.0, 60.0
    ex, ey = 94.0, 14.0
    lz0, lz1 = 2.5, 38.0
    lzc = (lz0 + lz1) / 2
    parts = [
        P("스피커 유닛 27", (0, 66, 0, 27, 2.5, 68.5), COL["spk"], lv="F", label="스피커 66×66"),
        P("챔버 9", (0, 66, 27, 36, 2.5, 68.5), COL["spk2"], lv="TR", label="챔버9\n유닛27"),
        P("Pi Zero", (69, 99, 30, 45, 3, 68), COL["pi"], label="Pi Zero", lv="F"),
        P("HAT", (106.5, 170, 30, 45, 0.5, 70.5), COL["hat"], label="HAT 63.5×70", lv="F"),
        P("배터리", (57.5, 147.5, 48, 60, 9.5, 61.5), COL["bat"], label="배터리 90×52×12"),
        P("LCD", (69, 119, 0, 8, lz0, lz1), COL["lcd"], label="LCD 50×35.5"),
        P("flex", (119, 121.5, 3.2, 4.0, lzc - 10, lzc + 10), COL["flex"], lv="FT", label=""),
        P("flex", (120.7, 121.5, 4.0, 23.2, lzc - 10, lzc + 10), COL["flex"], lv="FT", label=""),
        P("엔코더 body", cyl(ex, ey, 0, 26, 30, "z", Hi - 30), COL["enc"], shape="cyl", axis="z", label="엔코더\nø26×30"),
        P("knob", cyl(ex, ey, 0, 27, 25, "z", Hi + T), COL["enc"], shape="cyl", axis="z", dashed=True, label="노브ø27", lv="FR"),
        P("스위치", (150.5, 170.5, 12, 25, 12, 19), COL["sw"], label="스위치"),
        P("bushing", cyl(0, 18.5, 15.5, 6.13, 6, "x", 173.5), COL["sw"], shape="cyl", axis="x", dashed=True, label=""),
    ]
    marks = [
        dict(v="F", rect=(94 - 17.8, 94 + 17.8, lzc - 16.15, lzc + 16.15), shape="rect", txt="LCD 창", at=(125, 112), fill=False),
        dict(v="F", rect=(33 - 28, 33 + 28, 35.5 - 28, 35.5 + 28), shape="circ", txt="스피커 그릴", at=(33, 112), fill=False),
        dict(v="F", rect=(170.5, 173.5, 31, 36), shape="rect", txt="", at=None),
        dict(v="T", rect=(ex - 13.5, ex + 13.5, ey - 13.5, ey + 13.5), shape="rect", txt="엔코더(상단)", at=(60, 82), fill=False),
        dict(v="T", rect=(170.5, 173.5, 34, 41), shape="rect", txt="USB-C 충전", at=(160, 82)),
        dict(v="T", rect=(134.5, 142.5, 33.5, 41.5), shape="rect", txt="이어폰 잭", at=(128, 82)),
        dict(v="T", rect=(173.5 - 3, 173.5 + 6, 15, 22), shape="rect", txt="전원 스위치", at=(190, 40), fill=False),
    ]
    return _c_common("C2", "C2. 엔코더 상단", Di, Hi, parts, marks,
                     "엔코더 상단(노브 위). LCD는 아래쪽, 엔코더 body가 LCD 위에 3mm 간격. 노브 +25 (위), 부싱 +6 (우측)")


# ---------- drawing ----------
def proj(box, v):
    x0, x1, y0, y1, z0, z1 = box
    return {"F": (x0, x1, z0, z1), "T": (x0, x1, y0, y1), "R": (y0, y1, z0, z1)}[v]


def case_rect(c, v):
    Wi, Di, Hi = c["inner"]
    return {"F": (-T, Wi + T, -T, Hi + T), "T": (-T, Wi + T, -T, Di + T), "R": (-T, Di + T, -T, Hi + T)}[v]


def view_bbox(c, v):
    r = case_rect(c, v)
    xs, ys = [r[0], r[1]], [r[2], r[3]]
    for p in c["parts"]:
        a = proj(p["box"], v)
        xs += [a[0], a[1]]; ys += [a[2], a[3]]
    for m in c["marks"]:
        if m["v"] == v and m.get("at"):
            xs += [m["at"][0] - 14, m["at"][0] + 14]; ys += [m["at"][1] - 5, m["at"][1] + 5]
    for n in c.get("notes", []):
        if n["v"] == v:
            xs += [n["at"][0] - 14, n["at"][0] + 14]; ys += [n["at"][1] - 5, n["at"][1] + 5]
    return min(xs), max(xs), min(ys), max(ys)


def draw_view(ax, c, v, off, labels=True):
    ox, oy = off
    Wi, Di, Hi = c["inner"]
    # case
    r = case_rect(c, v)
    ax.add_patch(Rectangle((r[0] + ox, r[2] + oy), r[1] - r[0], r[3] - r[2], fill=False, ec="k", lw=2.6, zorder=5))
    ri = {"F": (0, Wi, 0, Hi), "T": (0, Wi, 0, Di), "R": (0, Di, 0, Hi)}[v]
    ax.add_patch(Rectangle((ri[0] + ox, ri[2] + oy), ri[1] - ri[0], ri[3] - ri[2], fill=False, ec="k", lw=0.7, zorder=5))
    order = sorted(c["parts"], key=lambda p: -(proj(p["box"], v)[1] - proj(p["box"], v)[0]) * (proj(p["box"], v)[3] - proj(p["box"], v)[2]))
    for p in order:
        a0, a1, b0, b1 = proj(p["box"], v)
        ls = "--" if p["dashed"] else "-"
        if p["shape"] == "cyl" and p["axis"] == {"F": "y", "T": "z", "R": "x"}[v]:
            ax.add_patch(Circle(((a0 + a1) / 2 + ox, (b0 + b1) / 2 + oy), (a1 - a0) / 2, fc=p["col"], alpha=p.get("alpha") or 0.45, ec="k", lw=0.8, ls=ls, zorder=3))
        else:
            ax.add_patch(Rectangle((a0 + ox, b0 + oy), a1 - a0, b1 - b0, fc=p["col"], alpha=p.get("alpha") or 0.45, ec="k", lw=0.8, ls=ls, zorder=3))
        if labels and p["name"] and v in p["lv"] and p["name"]:
            w, h = a1 - a0, b1 - b0
            if (w > 14 and h > 8) or (w > 8 and h > 14):
                rot = 90 if (h > 2.2 * w and h > 30 and "\n" not in p["name"]) else 0
                ax.text((a0 + a1) / 2 + ox, (b0 + b1) / 2 + oy, p["name"], ha="center", va="center", fontsize=6.5, zorder=6, rotation=rot)
    # marks
    for m in c["marks"]:
        if m["v"] != v or m["shape"] == "circ_skip":
            continue
        a0, a1, b0, b1 = m["rect"]
        fill = m.get("fill", True)
        if m["shape"] == "circ":
            ax.add_patch(Circle(((a0 + a1) / 2 + ox, (b0 + b1) / 2 + oy), (a1 - a0) / 2 * 0.8, fill=False, ec="red", lw=1.2, ls=":", zorder=7))
        else:
            ax.add_patch(Rectangle((a0 + ox, b0 + oy), a1 - a0, b1 - b0, fc="red" if fill else "none", alpha=0.85 if fill else 1,
                                   ec="red", lw=1.5, zorder=7))
        if m["txt"]:
            cx, cy = (a0 + a1) / 2, (b0 + b1) / 2
            tx, ty = m["at"]
            ax.annotate(m["txt"], (cx + ox, cy + oy), (tx + ox, ty + oy), color="red", fontsize=8, 
                        ha="center", va="center", zorder=8,
                        arrowprops=dict(arrowstyle="-", color="red", lw=1), bbox=dict(fc="white", ec="red", lw=0.6, pad=1.2, alpha=0.9))


def draw_notes(ax, c, v, off):
    for n in c.get("notes", []):
        if n["v"] != v:
            continue
        x, y = n["at"]
        if n.get("to"):
            ax.annotate(n["txt"], (n["to"][0] + off[0], n["to"][1] + off[1]), (x + off[0], y + off[1]), fontsize=7, ha="center", va="center",
                        zorder=9, arrowprops=dict(arrowstyle="-", color="#555", lw=0.8), bbox=dict(fc="white", ec="#555", lw=0.5, pad=1.2, alpha=0.9))
        else:
            ax.text(x + off[0], y + off[1], n["txt"], fontsize=6.5, ha="center", va="center", zorder=9)


def dim_h(ax, x0, x1, y, txt, fs=9):
    ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", color="navy", lw=1))
    ax.text((x0 + x1) / 2, y - 1.5, txt, ha="center", va="top", fontsize=fs, color="navy")


def dim_v(ax, y0, y1, x, txt, fs=9):
    ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", color="navy", lw=1))
    ax.text(x - 1.5, (y0 + y1) / 2, txt, ha="right", va="center", fontsize=fs, color="navy", rotation=90)


def outer(c):
    Wi, Di, Hi = c["inner"]
    return Wi + 2 * T, Hi + 2 * T, Di + 2 * T


def dims_txt(c):
    W, H, D = outer(c)
    return f"{W:g}×{H:g}×{D:g}"


def layout(c, gap=34):
    fb, tb, rb = (view_bbox(c, v) for v in "FTR")
    offF = (0, 0)
    offT = (0, fb[3] + gap - tb[2])
    offR = (fb[1] + gap - rb[0], 0)
    return fb, tb, rb, offF, offT, offR


def draw_sheet(c, path):
    W, H, D = outer(c)
    fb, tb, rb, offF, offT, offR = layout(c)
    x_min = min(fb[0], tb[0]) - 22
    x_max = offR[0] + rb[1] + 14
    y_min = fb[2] - 24
    y_max = offT[1] + tb[3] + 16
    sc = 0.06
    fig = plt.figure(figsize=((x_max - x_min) * sc, (y_max - y_min) * sc), dpi=140)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x_min, x_max); ax.set_ylim(y_min, y_max); ax.set_aspect("equal"); ax.axis("off")
    draw_view(ax, c, "F", offF); draw_view(ax, c, "T", offT); draw_view(ax, c, "R", offR)
    for v_, o_ in (("F", offF), ("T", offT), ("R", offR)):
        draw_notes(ax, c, v_, o_)
    # view captions
    ax.text(fb[1] + 3, offF[1] + fb[3] + 2, "정면 FRONT (X–Z)", fontsize=8, color="gray", va="bottom", ha="right") if False else None
    ax.text(x_min + 3, y_max - 6, f"{c['title']} — {dims_txt(c)} mm  (W×H×D, 외곽)", fontsize=15, va="top")
    ax.text(fb[0], offF[1] + fb[3] + 4, "FRONT (X–Z)", fontsize=8, color="gray", va="bottom")
    ax.text(tb[0], offT[1] + tb[3] + 2, "TOP (X–Y)", fontsize=8, color="gray", va="bottom")
    ax.text(offR[0] + rb[0], fb[3] + 4, "RIGHT SIDE (Y–Z)", fontsize=8, color="gray", va="bottom")
    # dims on outer case
    dim_h(ax, -T, W - T, fb[2] - 10, f"W = {W:g}")
    dim_v(ax, -T, H - T, -T - 12, f"H = {H:g}")
    dim_h(ax, offR[0] - T, offR[0] + D - T, rb[2] - 10 if False else fb[2] - 10, f"D = {D:g}")
    dim_v(ax, offT[1] - T, offT[1] + D - T, -T - 12, f"D = {D:g}")
    ax.text(x_max - 4, y_max - 22, f"비고: {c['flex_note']}\n{c['extra']}\n벽 3mm, 파트 간격 3mm\n빨간 표시 = 개구부", fontsize=8, ha="right", va="top",
            bbox=dict(fc="#f5f5f5", ec="gray", lw=0.5))
    fig.savefig(path)
    plt.close(fig)


def draw_overview(cs, path):
    gap = 40
    x = 0
    offs = []
    ymax = 0
    for c in cs:
        fb = view_bbox(c, "F")
        offs.append(x - fb[0])
        x += fb[1] - fb[0] + gap
        ymax = max(ymax, fb[3])
    sc = 0.06
    xmin, xmax = -25, x
    ymin, ymax2 = -45, ymax + 55
    fig = plt.figure(figsize=((xmax - xmin) * sc, (ymax2 - ymin) * sc), dpi=140)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax2); ax.set_aspect("equal"); ax.axis("off")
    for c, o in zip(cs, offs):
        draw_view(ax, c, "F", (o, 0))
        draw_notes(ax, c, "F", (o, 0))
        W, H, D = outer(c)
        dim_h(ax, o - T, o + W - T, -14, f"W = {W:g}")
        dim_v(ax, -T, H - T, o - T - 8, f"H = {H:g}")
        ax.text(o - T, ymax + 22, f"{c['title']}", fontsize=13, va="bottom")
        ax.text(o - T, ymax + 14, f"{W:g}×{H:g}×{D:g} mm (깊이 D = {D:g})", fontsize=10, va="bottom")
        ax.text(o - T, -32, c["extra"], fontsize=7, va="top", color="gray")
    ax.text(xmin + 2, ymax2 - 3, "WR-Radio 케이스 배치안 비교 — 정면도, 동일 축척", fontsize=15, va="top")
    fig.savefig(path)
    plt.close(fig)


def collisions(c, eps=1e-6):
    """AABB checks: pairwise overlap + inside-case. Space volumes may overlap boards/standoffs/connector (intended)."""
    Wi, Di, Hi = c["inner"]
    ps = c["parts"]
    res = []
    def spc(p): return p["name"].startswith(("커넥터·케이블", "납땜 리드"))
    def ok_pair(a, b):
        if spc(a) or spc(b):
            o = b if spc(a) else a
            return o["name"].startswith(("스탠드오프", "HAT", "Pi", "배터리 커넥터"))
        return False
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            a, b = ps[i], ps[j]
            if ok_pair(a, b):
                continue
            A, B = a["box"], b["box"]
            if all(min(A[k + 1], B[k + 1]) - max(A[k], B[k]) > eps for k in (0, 2, 4)):
                res.append(("overlap", a["name"], b["name"]))
    for p in ps:
        if p["name"].startswith(("노브", "knob")) or p["name"] == "bushing":
            continue
        x0, x1, y0, y1, z0, z1 = p["box"]
        if x0 < -eps or y0 < -eps or z0 < -eps or x1 > Wi + eps or y1 > Di + eps or z1 > Hi + eps:
            res.append(("outside", p["name"], p["box"]))
    return res


def vol(c):
    Wi, Di, Hi = c["inner"]
    return Wi * Di * Hi / 1000.0


if __name__ == "__main__":
    cs = [concept_A(), concept_A2(), concept_A3(), concept_B(), concept_C1(), concept_C2()]
    for c in cs:
        draw_sheet(c, os.path.join(OUT, f"concept_{c['key']}.png"))
    draw_overview(cs, os.path.join(OUT, "concepts_overview.png"))
    for c in cs:
        print(c["key"], outer(c), c["inner"], round(vol(c), 1), "collisions:", collisions(c))
