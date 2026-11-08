"""A3 case placement for radio-hat-v08 (2026-11-08). Placement only, no routing.
Reproducible: starts from radio-hat-v08.kicad_pcb.bak_before_A3 (the pre-A3 board), then
  1. swaps footprints changed in the schematic by sch_A3.py (side-view LEDs, XH side-entry J3,
     right-angle headers J4-J7, TP4056 EP without built-in vias) keeping ref/fields/path/nets,
  2. adds J9 UART debug pads (DNP, not in BOM/pos files) and the UART_TX/UART_RX nets on J1 pins 8/10,
  3. moves every unlocked footprint to the table below, places ref text, silk notes, refills GND, saves.
J1 and H1-H5 (locked) and the outline are never touched.
Run sch_A3.py first (J9 needs its schematic UUID), then with KiCad's python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 place_A3.py

Board orientation in the A3 case (board vertical, COMPONENT SIDE FACES THE REAR WALL, seen from the
rear it looks exactly like this KiCad top view):
  KiCad top edge    y=-64.90 -> case TOP wall      (J8 headphone jack exits here)
  KiCad bottom edge y=+5.08  -> case BOTTOM        (battery below; free floor under x 38..63.6:
                                                    J3 battery plug and J7 speaker plug enter from below)
  KiCad right edge  x=63.48  -> case LEFT wall     (USB-C J2 + side-view charge LEDs D2/D3 exit here)
  KiCad left edge   x=0      -> Pi (J1 right-angle header)
Right-angle headers J4/J6/J5 point -x (toward the Pi); their plug zone x 8.66..(pad-4.04) must stay empty.
Frame: x right, y DOWN (negative = toward the top edge).
"""
import os, math, shutil, re
import pcbnew
from pcbnew import FromMM as mm, ToMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08"))
PCB_FILE = os.path.join(D, "radio-hat-v08.kicad_pcb")
BAK = PCB_FILE + ".bak_before_A3"
SCH = os.path.join(D, "radio-hat-v08.kicad_sch")
STOCK = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"

# ---------------- stage 1: footprint swaps + J9 (from the backup) ----------------
SWAP = {  # ref: (lib, footprint, {field: value})
    "D2": ("LED_SMD", "LED_Kingbright_APA1606_1.6x0.6mm_Horizontal", {"LCSC": "C965860", "MPN": "XL-1606SURC", "Value": "RED"}),
    "D3": ("LED_SMD", "LED_Kingbright_APA1606_1.6x0.6mm_Horizontal", {"LCSC": "C409794", "MPN": "MHS190UGCT", "Value": "GREEN"}),
    "J3": ("Connector_JST", "JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal", {"LCSC": "C157931", "MPN": "S2B-XH-A(LF)(SN)"}),
    "J4": ("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Horizontal", {"LCSC": "C492411", "MPN": "PZ254R-11-03P"}),
    "J5": ("Connector_PinHeader_2.54mm", "PinHeader_1x08_P2.54mm_Horizontal", {"LCSC": "C492416", "MPN": "PZ254R-11-08P"}),
    "J6": ("Connector_PinHeader_2.54mm", "PinHeader_1x05_P2.54mm_Horizontal", {"LCSC": "C492413", "MPN": "PZ254R-11-05P"}),
    "J7": ("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Horizontal", {"LCSC": "C492410", "MPN": "PZ254R-11-02P"}),
    "U1": ("Package_SO", "SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm", {}),
}
shutil.copyfile(BAK, PCB_FILE)
b = pcbnew.LoadBoard(PCB_FILE)
for ref, (lib, name, flds) in SWAP.items():
    old = b.FindFootprintByReference(ref)
    new = pcbnew.FootprintLoad(STOCK + lib + ".pretty", name)
    new.SetFPID(pcbnew.LIB_ID(lib, name))
    for f in old.GetFields():                      # carry Reference/Value/LCSC/MPN/Description...
        n = f.GetName()
        if n in ("Footprint",): continue
        new.SetField(n, f.GetText())
        nf = new.GetField(n)
        if n not in ("Reference", "Value"):
            nf.SetVisible(False)
    for k, v in flds.items():
        new.SetField(k, v)
    new.SetPath(old.GetPath()); new.SetSheetname(old.GetSheetname()); new.SetSheetfile(old.GetSheetfile())
    new.SetPosition(old.GetPosition())
    pads_old = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    b.Add(new)
    for p in new.Pads():
        if p.GetNumber() in pads_old:
            p.SetNet(pads_old[p.GetNumber()])
    b.Remove(old)

if b.FindFootprintByReference("J9") is None:
    s = open(SCH).read()
    i = s.find('(property "Reference" "J9"')
    assert i > 0, "run sch_A3.py first"
    uid = re.findall(r'\(uuid "([^"]+)"\)', s[s.rfind("(symbol", 0, i):i])[-1]
    nets = {}
    for nn in ("/UART_TX", "/UART_RX"):
        ni = b.FindNet(nn)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(b, nn); b.Add(ni)
        nets[nn] = ni
    j1 = b.FindFootprintByReference("J1")
    for p in j1.Pads():
        if p.GetNumber() == "8": p.SetNet(nets["/UART_TX"])
        if p.GetNumber() == "10": p.SetNet(nets["/UART_RX"])
    j9 = pcbnew.FootprintLoad(STOCK + "Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical")
    j9.SetFPID(pcbnew.LIB_ID("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical"))
    j9.SetReference("J9"); j9.SetValue("UART_DBG")
    j9.SetField("Datasheet", ""); j9.SetField("Description", "Serial debug pads, no part fitted (1=GND 2=Pi TXD GPIO14 3=Pi RXD GPIO15)")
    j9.SetField("LCSC", ""); j9.SetField("MPN", "")
    for n in ("Datasheet", "Description", "LCSC", "MPN"):
        j9.GetField(n).SetVisible(False)
    j9.SetPath(pcbnew.KIID_PATH("/" + uid)); j9.SetSheetname("/"); j9.SetSheetfile("radio-hat-v08.kicad_sch")
    j9.SetAttributes(pcbnew.FP_THROUGH_HOLE | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    j9.SetDNP(True)
    b.Add(j9)
    gnd = b.FindNet("GND")
    for p in j9.Pads():
        p.SetNet({"1": gnd, "2": nets["/UART_TX"], "3": nets["/UART_RX"]}[p.GetNumber()])
# mounting holes were created without a library nickname and flagged DNP (build.py); match the
# schematic ("MountingHole:" nickname, dnp no) so schematic parity is clean (position/lock unchanged)
for r in ("H1", "H2", "H3", "H4", "H5"):
    h = b.FindFootprintByReference(r)
    h.SetFPID(pcbnew.LIB_ID("MountingHole", str(h.GetFPID().GetLibItemName())))
    h.SetDNP(False)                                  # schematic: dnp no (no part, NPTH only)
b.Save(PCB_FILE)

# ---------------- stage 2: placement ----------------
# Rotation convention (KiCad, y down): r90 maps local (x,y)->(y,-x) (local +y -> +x, local -x -> +y);
# r-90 maps (x,y)->(-y,x); r180 maps (x,y)->(-x,-y).
HX = 27.70                      # pad column of the right-angle headers J4/J6/J5 (pins point -x)
P = {
    # ---- external connectors ----
    "J8": (16.00, -61.40, -90),   # PJ-307C: opening local -x -> -y (top edge). Body front on the edge (y=-64.90),
                                  # barrel 3.0 mm past the edge (datasheet), pads 2..5 in a row at y=-56.4
    "J2": (60.78, -47.80, 90),    # USB-C (case pocket = centre y +-6.75), mouth local +y -> +x (right edge), receptacle front 1.0 mm past the edge
    "D2": (62.63, -36.95, -90),   # CHRG red side-view LED, lens local -y -> +x (emits through the case left wall)
    "D3": (62.63, -32.95, -90),   # STDBY green side-view LED, 4.0 mm c-c from D2; as low as the H1 boss allows
                                  # (wall between J2 pocket edge -41.05 and D2 hole edge -37.95 = 3.10 mm)
    "J3": (47.50, -4.17, 0),      # S2B-XH-A side entry: housing front on the bottom edge, plug enters from below (+y)
                                  # pin1 BAT+ (47.5), pin2 B- (50.0)
    "J7": (42.20, -14.20, -90),   # SPK right-angle header, pins point +y (down) INSIDE the board: pads y -14.2,
                                  # plastic face y -10.16, plug zone y -10.16..+4.84 (15 mm, nothing beyond the edge);
                                  # pin1 SPK- (42.20), pin2 SPK+ (39.66)
    "J4": (HX, -34.41, 180),      # PWR_SW right-angle, pins -x; pin1 bottom (y -34.41) .. pin3 (y -39.49)
    "J6": (HX, -20.53, 180),      # ENC right-angle, pins -x; pin1 +3V3 bottom .. pin5 GND top
    "J5": (HX, 0.97, 180),        # LCD right-angle, pins -x; pin1 BL bottom (y 0.97) .. pin8 +5V top (y -16.81)
    "J9": (10.50, -48.42, 0),     # UART debug pads (DNP): 1 GND / 2 TX / 3 RX on the J1 pin 6/8/10 rows

    # ---- headphone DAC (top-left, under the jack) ----
    "U6": (19.00, -47.00, 270),   # PCM5102A: pins 1-10 (charge pump, OUTL/OUTR, AVDD) on top, 11-20 (I2S) below
    "R19": (17.10, -52.30, 0),    # OUTL 100R -> HP_L (jack pin 5, x 11)
    "R20": (20.40, -52.30, 0),    # OUTR 100R -> HP_R (jack pin 2, x 21)
    "C19": (13.80, -52.30, 0),    # HP_L 2.2n
    "C20": (23.70, -52.30, 0),    # HP_R 2.2n
    "C14": (24.30, -49.80, 0),    # CPVDD 0.1u (pin 1)
    "C16": (24.30, -48.00, 0),    # CAPP-CAPM 2.2u
    "C17": (24.30, -46.20, 0),    # VNEG 2.2u
    "C15": (27.80, -48.90, 90),   # 3V3 10u common
    "C18": (24.30, -44.40, 0),    # LDOO 2.2u
    "C13": (24.30, -42.60, 0),    # DVDD 0.1u
    "R18": (20.60, -42.30, 0),    # XSMT pull-up 10k
    "C12": (14.40, -49.00, 90),   # AVDD 0.1u
    "R23": (14.40, -45.10, 90),   # HP detect 4.7k (jack pin 4 TN)
    "C25": (25.40, -56.50, 90),   # HP_DET 22u

    # ---- boost (top-right, far from the jack) ----
    "U4": (42.00, -53.50, 0),     # TPS61023: FB/EN/VIN left, VOUT/SW/GND right
    "L1": (46.60, -53.50, 0),     # SW (left pad) -> SYS (right pad)
    "C6": (42.60, -56.30, 90),    # Cout 22u
    "C7": (40.45, -57.10, 90),    # Cout 22u
    "C8": (34.50, -60.80, 0),     # 220u bulk (+5V, toward J1)
    "C5": (41.90, -51.10, 0),     # Cin 10u at VIN
    "C27": (50.60, -53.50, 90),   # Cin 22u at L1 SYS end
    "R11": (38.20, -53.20, 0),    # FB top 510k
    "R12": (38.20, -51.30, 180),  # FB bottom 68k
    "C26": (37.90, -55.10, 0),    # feed-forward 330p
    "R13": (45.50, -58.50, 0),    # EN pulldown 100k

    # ---- USB input / charger (right, at J2) ----
    "D4": (53.00, -47.80, 90),    # SMAJ5.0A TVS beside the J2 VBUS pads
    "C1": (53.00, -42.40, 0),     # VBUS bulk 10u
    "R1": (56.50, -54.00, 0),     # CC1 5.1k
    "R2": (53.30, -52.60, 0),     # CC2 5.1k
    "R24": (52.50, -38.00, 0),    # VBUS 10k pulldown
    "U1": (46.00, -44.00, 90),    # TP4056: VCC bottom-right, BAT top-right, CE/CHRG/STDBY top
    "C2": (48.50, -38.40, 0),    # TP4056 VCC 10u
    "R3": (44.50, -38.50, 0),    # PROG 1.2k
    "C3": (46.50, -49.00, 0),     # BAT+ 10u
    "Q2": (40.30, -44.50, 90),    # 2N7002 CE switch
    "R6": (41.60, -48.60, 0),     # CE pull-up 10k
    "R7": (40.30, -40.60, 0),    # Q2 gate pulldown 100k
    "R4": (59.60, -38.40, 0),    # LED R CHRG
    "R5": (59.60, -34.40, 0),    # LED R STDBY
    # ---- load sharing ----
    "D1": (33.00, -46.00, 90),    # SS34 VBUS -> SYS
    "Q1": (36.30, -40.50, 0),     # AO3401A
    "R10": (32.60, -40.30, 90),   # Q1 gate pulldown 100k

    # ---- ADC ----
    "U5": (34.00, -33.00, 90),    # ADS1115
    "C11": (34.00, -37.70, 0),    # VDD 0.1u
    "R14": (38.50, -32.20, 90),
    "R15": (40.20, -32.20, 90),
    "C9": (41.90, -32.20, 90),
    "R16": (43.60, -32.20, 90),
    "R17": (45.30, -32.20, 90),
    "C10": (47.00, -32.20, 90),

    # ---- battery protection (above J3) ----
    "U3": (50.00, -13.50, 180),   # WSP8814
    "U2": (50.00, -18.50, 0),     # DW01A
    "C4": (53.80, -18.50, 90),
    "R8": (46.50, -18.50, 90),
    "R9": (50.00, -9.50, 0),

    # ---- speaker amp (middle, above J7) ----
    "U7": (36.00, -20.00, 0),     # MAX98357A
    "FB1": (41.00, -19.60, 0),   # OUTP -> SPK+
    "FB2": (41.00, -17.40, 0),   # OUTN -> SPK-
    "C23": (44.40, -19.00, 90),
    "C24": (44.40, -22.60, 90),
    "C22": (36.00, -24.00, 0),
    "C21": (40.20, -24.00, 0),
    "JP1": (32.30, -20.00, 90),
    "R22": (33.00, -15.50, 0),
    "R21": (33.00, -13.60, 0),
}

NOTES = [  # (text, x, y, size, rot)
    ("+", 47.5, -7.6, 0.8, 0), ("-", 50.0, -7.6, 0.8, 0),          # J3 polarity (pin1 BAT+)
    ("1 SIDE ONLY", 30.30, -20.0, 0.8, 90),                          # JP1: bridging both sides shorts 5V-GND
    ("GND", 12.65, -48.42, 0.8, 90), ("TX", 12.65, -45.88, 0.8, 90), ("RX", 12.65, -43.34, 0.8, 90),  # J9 pads
    ("SW", 12.5, -37.0, 0.8, 0), ("ENC", 12.5, -25.6, 0.8, 0), ("LCD", 12.5, -8.0, 0.8, 0),      # plug zones
    ("SPK", 40.9, -2.3, 0.8, 0),
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

DRAW = list(b.GetDrawings())
existing = {d.GetText(): d for d in DRAW if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() == pcbnew.F_SilkS}
for t, x, y, s, rot in NOTES:
    tx = existing.get(t)
    if tx is None:
        tx = pcbnew.PCB_TEXT(b); tx.SetText(t); tx.SetLayer(pcbnew.F_SilkS); b.Add(tx); DRAW.append(tx)
    tx.SetTextSize(VECTOR2I(mm(s), mm(s))); tx.SetTextThickness(mm(max(0.12, s * 0.15)))
    tx.SetPosition(VECTOR2I(mm(x), mm(y))); tx.SetTextAngleDegrees(rot)
TITLE_POS = (42.8, -26.6)
for d in DRAW:
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetText().startswith("wr-radio v0.8"):
        d.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        d.SetPosition(VECTOR2I(mm(TITLE_POS[0]), mm(TITLE_POS[1])))

def crt_box(f):
    c = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    return (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
def boxdist(bx, x, y):
    return math.hypot(max(bx[0] - x, 0, x - bx[2]), max(bx[1] - y, 0, y - bx[3]))
def overlap(a, c, gap=0.0):
    return a[0] < c[2] + gap and c[0] < a[2] + gap and a[1] < c[3] + gap and c[1] < a[3] + gap
boxes = {r: crt_box(f) for r, f in fps.items()}

# plug zones of the right-angle headers: 15 mm from the plastic face in the plug direction (must stay empty)
PLUG = {}
for r in ("J4", "J6", "J5"):
    x0, y0, x1, y1 = boxes[r]
    PLUG[r] = (HX - 4.04 - 15.0, y0, HX - 4.04, y1)
x0, y0, x1, y1 = boxes["J7"]                    # J7 pins point +y: zone from the plastic face 15 mm down
PLUG["J7"] = (x0, P["J7"][1] + 4.04, x1, P["J7"][1] + 4.04 + 15.0)
assert PLUG["J7"][3] <= 5.08, "J7 plug would stick out past the bottom edge"

def bbmm(bb):
    return (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
pad_boxes = [bbmm(p.GetBoundingBox()) for f in fps.values() for p in f.Pads()]
silk_boxes = []
for r, f in fps.items():
    for g in f.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == "PCB_SHAPE":
            silk_boxes.append((r, bbmm(g.GetBoundingBox())))
EDGE = (0.0, -64.90, 63.48, 5.08)
used_txt = [bbmm(d.GetBoundingBox()) for d in DRAW if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() == pcbnew.F_SilkS]
used_txt += [bbmm(fps[h].Reference().GetBoundingBox()) for h in ("H1", "H2", "H3", "H4", "H5") if fps[h].Reference().IsVisible()]
hidden = []
order = sorted(P.keys(), key=lambda r: (boxes[r][2] - boxes[r][0]) * (boxes[r][3] - boxes[r][1]))
for r in order:
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
            cands = [(cx, y0 - th / 2 - gap), (cx, y1 + th / 2 + gap), (x0 - tw / 2 - gap, cy), (x1 + tw / 2 + gap, cy)]
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
EDGE_OK = {"J2", "J8", "J3", "D2", "D3"}      # intentional overhang at the board edge
problems = []
refs = sorted(P)
for i, a in enumerate(refs):
    A = boxes[a]
    if a not in EDGE_OK and not (A[0] >= 0.3 and A[2] <= 63.18 and A[1] >= -64.6 and A[3] <= 4.78):
        problems.append("edge %s %s" % (a, A))
    for hr, hp in HOLES.items():
        hx, hy = ToMM(hp.x), ToMM(hp.y)
        nx, ny = min(max(hx, A[0]), A[2]), min(max(hy, A[1]), A[3])
        if math.hypot(nx - hx, ny - hy) < 3.25:     # case boss Ø5.5 + 0.5 mm
            problems.append("keepout %s %s" % (a, hr))
    for c in refs[i + 1:] + ["J1"]:
        if overlap(A, boxes[c]):
            problems.append("crt %s-%s" % (a, c))
    for z, Z in PLUG.items():
        if a != z and overlap(A, Z):
            problems.append("plugzone %s-%s" % (z, a))
for z, Z in PLUG.items():
    if overlap(Z, boxes["J1"]): problems.append("plugzone %s-J1" % z)
print("plug zones:", {k: tuple(round(v, 2) for v in Z) for k, Z in PLUG.items()})
print("bbox problems:", problems or "none")

STALE = {"BAT+", "BAT-", "ONE SIDE ONLY"}
for d in [d for d in DRAW if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() in STALE]:
    b.Remove(d)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PCB_FILE)
print("saved", PCB_FILE)
