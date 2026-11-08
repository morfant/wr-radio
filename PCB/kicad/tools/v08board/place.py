"""First-pass component placement for radio-hat-v08 (placement only, no routing).
Moves every unlocked footprint to the coordinates below, places reference text, adds a few
silkscreen notes, refills the GND zone and saves. J1 and H1-H5 (locked) are never touched.
Rerunnable: positions are absolute. Run with KiCad's python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 place.py

Frame: same as build.py / v07 import. x right, y DOWN (negative = toward the top edge).
Board outline x 0..63.48, y -64.90..5.08. J1 runs along the left edge (Pi on the left).
Edges:  top y=-64.90 (power side: J4 switch, USB-C J2, charge LEDs)
        right x=63.48 (battery connector J3)
        bottom y=5.08 (headphone jack J8, as on v07)
"""
import os, math
import pcbnew
from pcbnew import FromMM as mm, ToMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_FILE = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_pcb"))

# ref: (x, y, rotation_deg)
P = {
    # ---- external connectors: v07 positions/orientations (v07 Eagle y negated) ----
    "J5": (10.30, -28.55, 0),     # LCD_CONN  pad1 (10.3,-28.55) .. pad8 (10.3,-10.77)
    "J6": (10.30, -43.98, 0),     # ENC_CONN  pad1 (10.3,-43.98) .. pad5 (10.3,-33.82)
    "J7": (41.81, -13.97, 0),     # SPK       pad1 (41.81,-13.97), pad2 (41.81,-11.43)
    "J4": (18.83, -61.44, 270),   # SWITCH    pad1 (18.83,-61.44) .. pad3 (13.75,-61.44)
    "J8": (37.70, 1.58, 90),      # PJ-307C: plug opening -X(local) -> +Y = bottom edge; front face on edge
    # ---- new external parts ----
    "J2": (44.00, -61.55, 180),   # USB-C on top edge, mouth 0.3 mm past the edge
    "D2": (35.50, -63.30, 0),     # CHRG LED (red)   } one window/light pipe left of J2
    "D3": (35.50, -61.40, 0),     # STDBY LED (white)}
    "J3": (59.20, -39.00, 90),    # JST XH battery on right edge, pin1 BAT+ (59.2,-39, lower), pin2 B- (59.2,-41.5, upper)

    # ---- USB input / charger (top centre-right) ----
    "D4": (51.50, -58.50, 270),   # SMAJ5.0A TVS right beside J2 VBUS pads
    "C1": (47.50, -54.80, 0),     # VBUS bulk 10u at J2
    "R24": (44.00, -55.00, 0),    # VBUS 10k pulldown
    "R1": (51.90, -54.00, 0),     # CC1 5.1k (J2 A5)
    "R2": (40.40, -54.60, 0),     # CC2 5.1k (J2 B5)
    "R4": (35.50, -59.60, 0),     # LED R CHRG
    "R5": (35.50, -57.70, 0),     # LED R STDBY
    "U1": (44.00, -48.50, 180),   # TP4056: VCC top-right (to J2), BAT top-left, LEDs/CE left
    "C2": (49.30, -49.50, 90),    # TP4056 VCC 10u
    "R3": (46.50, -44.40, 0),     # PROG 1.2k
    "C3": (39.50, -44.00, 0),     # BAT+ 10u
    "Q2": (43.50, -41.50, 0),     # 2N7002 CE switch
    "R6": (39.50, -42.00, 0),     # CE pull-up 10k
    "R7": (39.50, -40.10, 0),     # Q2 gate pulldown 100k
    # ---- load sharing (between charger and boost) ----
    "D1": (36.50, -52.00, 90),    # SS34 VBUS(top) -> SYS(bottom)
    "Q1": (32.50, -47.00, 0),     # AO3401A
    "R10": (32.50, -44.20, 0),    # Q1 gate pulldown 100k
    # ---- battery protection (right, between J3 and the rest) ----
    "U3": (52.00, -40.80, 180),   # WSP8814: S1(B-) right -> J3 pin2, S2(GND) left
    "U2": (52.00, -45.30, 0),     # DW01A
    "C4": (55.50, -45.30, 90),    # DW VCC-B- 0.1u
    "R8": (55.50, -48.60, 90),    # BAT+ -> DW VCC 100R
    "R9": (48.90, -45.90, 90),    # CS 1k

    # ---- boost (top-left, output toward J1 pins 2/4) ----
    "U4": (21.00, -52.00, 0),     # TPS61023: FB/EN/VIN left, VOUT/SW/GND right
    "L1": (25.60, -52.00, 0),     # SW (left pad) -> SYS (right pad)
    "C6": (21.60, -54.80, 90),    # Cout 22u: +5V pad next to VOUT, GND pad up
    "C7": (19.45, -55.60, 90),    # Cout 22u, paired with C6 (GND pads up)
    "C8": (26.50, -60.80, 0),     # 220u bulk
    "C5": (20.90, -49.60, 0),     # Cin 10u at VIN pin
    "C27": (29.60, -52.00, 90),   # Cin 22u at L1 SYS end
    "R11": (17.20, -51.70, 0),    # FB top 510k (+5V-FB)
    "R12": (17.20, -49.80, 180),  # FB bottom 68k (FB-GND)
    "C26": (16.90, -53.60, 0),    # feed-forward 330p (+5V-FB)
    "R13": (13.30, -57.30, 0),    # EN pulldown 100k

    # ---- ADC (near J1 I2C pins 3/5) ----
    "U5": (15.50, -43.50, 90),    # ADS1115: SCL/SDA/VDD on top row, AIN0/1 bottom
    "C11": (17.60, -47.60, 0),    # VDD 0.1u
    "R14": (15.30, -38.60, 0),    # BAT+ 100k
    "R15": (15.30, -36.70, 0),    # VBAT_SENSE 100k
    "C9": (15.30, -34.80, 0),     # VBAT_SENSE 100n
    "R16": (19.00, -38.60, 0),    # VBUS 100k
    "R17": (19.00, -36.70, 0),    # VBUS_SENSE 100k
    "C10": (19.00, -34.80, 0),    # VBUS_SENSE 100n

    # ---- headphone DAC (bottom-left, next to J8) ----
    "U6": (19.50, -6.00, 180),    # PCM5102A: I2S/LDOO/DVDD left (toward J1), analog right (toward J8)
    "C12": (25.60, -9.10, 0),     # AVDD 0.1u
    "R20": (25.60, -7.20, 0),     # OUTR 100R
    "R19": (25.60, -5.30, 0),     # OUTL 100R
    "C20": (29.30, -7.20, 0),     # HP_R 2.2n
    "C19": (29.30, -5.30, 0),     # HP_L 2.2n
    "C16": (24.50, -2.90, 90),    # CAPP-CAPM 2.2u
    "C17": (26.20, -2.90, 90),    # VNEG 2.2u
    "C14": (21.50, -0.90, 0),     # CPVDD 0.1u
    "C15": (21.50, 1.30, 0),      # 3V3 10u common
    "C18": (14.30, -3.80, 90),    # LDOO 2.2u
    "C13": (14.30, -0.60, 90),    # DVDD 0.1u
    "R18": (17.60, -0.70, 0),     # XSMT pull-up 10k
    "R23": (45.60, -4.00, 90),    # HP detect 4.7k (J8 pin4 TN)
    "C25": (47.80, -4.00, 90),    # HP_DET 22u

    # ---- speaker amp (next to J7) ----
    "U7": (33.50, -14.00, 0),     # MAX98357A: I2S top-left, OUTP/OUTN right, VDD bottom
    "FB1": (38.00, -11.50, 0),    # OUTP -> SPK+ (J7 pin2)
    "FB2": (38.00, -15.20, 0),    # OUTN -> SPK- (J7 pin1)
    "C23": (45.00, -11.50, 90),   # SPK+ 220p
    "C24": (45.00, -15.00, 90),   # SPK- 220p
    "C22": (34.00, -10.40, 0),    # VDD 0.1u
    "C21": (34.00, -8.40, 0),     # VDD 10u
    "JP1": (29.30, -14.50, 90),   # gain jumper
    "R22": (26.00, -19.00, 0),    # SD_MODE 1.8k
    "R21": (26.00, -20.90, 0),     # AMP_SD 10k
}

# extra silkscreen notes: (text, x, y, size, rot)
NOTES = [
    ("BAT+", 59.2, -35.3, 0.8, 0),              # J3 pin1 (lower pin) = BAT+
    ("BAT-", 59.2, -45.3, 0.8, 0),              # J3 pin2 (upper pin) = B-
    ("1 SIDE ONLY", 26.8, -14.3, 0.8, 90),      # JP1: bridging both sides shorts 5V-GND
]

REF_SIZE = 0.8
REF_THICK = 0.15

b = pcbnew.LoadBoard(PCB_FILE)
fps = {f.GetReference(): f for f in b.GetFootprints()}
missing = [r for r in fps if r not in P and not fps[r].IsLocked()]
extra = [r for r in P if r not in fps]
assert not extra, "unknown refs %s" % extra
if missing:
    print("WARNING: unplaced (not in table):", missing)

for r, (x, y, rot) in P.items():
    f = fps[r]
    assert not f.IsLocked(), r
    if f.IsFlipped():
        f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(rot)
    f.SetPosition(VECTOR2I(mm(x), mm(y)))

# ---- remove previous notes (rerun-safe) ----
DRAW = list(b.GetDrawings())
existing = {d.GetText(): d for d in DRAW if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() == pcbnew.F_SilkS}
for t, x, y, s, rot in NOTES:           # update in place on rerun (b.Remove() upsets swig typing)
    tx = existing.get(t)
    if tx is None:
        tx = pcbnew.PCB_TEXT(b); tx.SetText(t); tx.SetLayer(pcbnew.F_SilkS); b.Add(tx); DRAW.append(tx)
    tx.SetTextSize(VECTOR2I(mm(s), mm(s))); tx.SetTextThickness(mm(max(0.12, s * 0.15)))
    tx.SetPosition(VECTOR2I(mm(x), mm(y))); tx.SetTextAngleDegrees(rot)
# move the board title text into the free middle area
for d in DRAW:
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetText().startswith("wr-radio v0.8"):
        d.SetPosition(VECTOR2I(mm(23.0), mm(-25.0)))

# ---- geometry helpers ----
def crt_box(f):
    c = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    return (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))

def boxdist(b, x, y):
    return math.hypot(max(b[0] - x, 0, x - b[2]), max(b[1] - y, 0, y - b[3]))

def overlap(a, c, gap=0.0):
    return a[0] < c[2] + gap and c[0] < a[2] + gap and a[1] < c[3] + gap and c[1] < a[3] + gap

boxes = {r: crt_box(f) for r, f in fps.items()}

# ---- reference text placement: 0.8 mm, outside pads / other courtyards / all silk, upright ----
def bbmm(bb):
    return (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
pad_boxes = [bbmm(p.GetBoundingBox()) for f in fps.values() for p in f.Pads()]
silk_boxes = []   # (owner, box) for footprint silk graphics
for r, f in fps.items():
    for g in f.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == "PCB_SHAPE":
            silk_boxes.append((r, bbmm(g.GetBoundingBox())))
EDGE = (0.0, -64.90, 63.48, 5.08)
used_txt = []
for d in DRAW:
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() == pcbnew.F_SilkS:
        used_txt.append(bbmm(d.GetBoundingBox()))
hidden = []
order = sorted(P.keys(), key=lambda r: (boxes[r][2] - boxes[r][0]) * (boxes[r][3] - boxes[r][1]))
for r in order:   # small parts first: they have the fewest options
    f = fps[r]; t = f.Reference()
    t.SetTextSize(VECTOR2I(mm(REF_SIZE), mm(REF_SIZE))); t.SetTextThickness(mm(REF_THICK))
    t.SetKeepUpright(True); t.SetVisible(True)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    x0, y0, x1, y1 = boxes[r]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    best = None
    for gap, pg, sg in ((0.25, 0.2, 0.17), (0.6, 0.2, 0.17), (1.0, 0.2, 0.17), (0.15, 0.12, 0.03), (0.5, 0.12, 0.03), (1.0, 0.12, 0.03)):
        for ang in (0, 90):
            t.SetTextAngleDegrees(ang)
            t.SetPosition(VECTOR2I(mm(cx), mm(cy)))
            tb0 = bbmm(t.GetBoundingBox()); tw, th = tb0[2] - tb0[0], tb0[3] - tb0[1]
            cands = [(cx, y0 - th / 2 - gap), (cx, y1 + th / 2 + gap),
                     (x0 - tw / 2 - gap, cy), (x1 + tw / 2 + gap, cy)]
            for k in (-1.2, 1.2, -2.4, 2.4):
                cands += [(cx + k, y0 - th / 2 - gap), (cx + k, y1 + th / 2 + gap),
                          (x0 - tw / 2 - gap, cy + k), (x1 + tw / 2 + gap, cy + k)]
            for tx, ty in cands:
                tb = (tx - tw / 2, ty - th / 2, tx + tw / 2, ty + th / 2)
                if not (tb[0] > EDGE[0] + 0.4 and tb[2] < EDGE[2] - 0.4 and tb[1] > EDGE[1] + 0.4 and tb[3] < EDGE[3] - 0.4):
                    continue
                if any(overlap(tb, pb, pg) for pb in pad_boxes): continue
                if any(overlap(tb, sb, sg) for o, sb in silk_boxes): continue
                if any(overlap(tb, boxes[o], -0.05) for o in boxes if o != r and not o.startswith("H")): continue
                if any(overlap(tb, u, max(sg, 0.1)) for u in used_txt): continue
                # the label must sit closer to its own part than to any other part
                own = boxdist(boxes[r], tx, ty)
                if sg > 0.1 and any(boxdist(boxes[o], tx, ty) < own - 0.3 for o in P if o != r): continue
                best = (tx, ty, ang, tb); break
            if best: break
        if best: break
    if best:
        tx, ty, ang, tb = best
        t.SetTextAngleDegrees(ang); t.SetPosition(VECTOR2I(mm(tx), mm(ty)))
        used_txt.append(tb)
    else:
        t.SetVisible(False); hidden.append(r)
print("hidden refs:", hidden)

# ---- checks ----
HOLES = {r: fps[r].GetPosition() for r in ("H1", "H2", "H3", "H4", "H5")}
EDGE_OK = {"J2", "J8"}           # intentional overhang
problems = []
refs = sorted(P)
for i, a in enumerate(refs):
    A = boxes[a]
    if a not in EDGE_OK and not (A[0] >= 0.3 and A[2] <= 63.18 and A[1] >= -64.6 and A[3] <= 4.78):
        problems.append("edge %s %s" % (a, A))
    for hr, hp in HOLES.items():
        hx, hy = ToMM(hp.x), ToMM(hp.y)
        nx, ny = min(max(hx, A[0]), A[2]), min(max(hy, A[1]), A[3])
        if math.hypot(nx - hx, ny - hy) < 3.5:
            problems.append("keepout %s %s" % (a, hr))
    for c in refs[i + 1:] + ["J1"]:
        if overlap(A, boxes[c]):
            problems.append("crt %s-%s" % (a, c))
print("bbox problems:", problems or "none")

# drop silk notes from earlier iterations (done last: b.Remove() upsets later swig calls)
STALE = {"+", "BAT", "USB-C", "ONE SIDE ONLY"}
for d in [d for d in DRAW if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() in STALE]:
    b.Remove(d)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PCB_FILE)
print("saved", PCB_FILE)
