"""Section 11: J10 external-button pads (DNP) on Pi GPIO4 (J1 pin 7). KiCad python, GUI closed.
Run fix_11_btn_sch.py first (J10 needs its schematic UUID).
  python3 fix_11_btn.py            (board = $WR_PCB or the project board)

Why J10 is not next to J1.7: the only free column beside J1 (x 8.7..12.3, between the J8 courtyard y -53.66 and
the C25 courtyard y -43.33) is taken by J9, and everything east of it is U6 decoupling (C19/C12/R18/R23) or plug
space. A grid search of the whole board for a 1x02 2.54 mm footprint (1.7 mm pads, 0.25 mm clearance, outside all
courtyards / plug spaces) found nothing closer than ~23 mm. A two-layer grid router then gave the cheapest route
(almost all F.Cu, one 1.3 mm B.Cu hop) to the free spot right of the J8 jack, north of the +5V trunk.

  J10  PinHeader_1x02_P2.54mm_Vertical r90 at (24.76, -60.8): pad 1 BTN (24.76, -60.8), pad 2 GND (27.30, -60.8)
       DNP, through-hole, excluded from BOM and position files (like J9). Courtyard x 22.96..29.10, y -62.6..-59.0.
  /BTN 0.25 mm, F.Cu except one B.Cu hop under I2S_DIN/SDA at the left edge:
       J1.7 -> SW between the J1 pin columns (x 5.22) -> W along y -42.15 (between pin rows 9/10 and 11/12)
       -> via (1.6,-41.7) -> B.Cu -> via (0.65,-42.65) -> N along the left edge x 0.65 -> past J1.1/J1.2 (x 1.9)
       -> NE under the +5V trunk corner -> E along y -56.6 (between the trunk and H3) -> SE behind the J8 pin row
       -> E along y -59.0 -> J10.1.
  J10.2 GND: through the GND zones (F and B).
  Silk: B.SilkS "BTN" / "GND" under each pad (J9 label style), F.SilkS reference "J10" above pad 2.
       Moved to make room: F.SilkS "PHONE" (jack label) (24.84,-60.9) -> (24.6,-63.45); C20 reference -> (27.15,-58.0).
Re-runnable: phase 1 removes the copper listed in owned_11.json and its own B.SilkS labels, phase 2 (new process)
adds/moves J10, sets the nets and re-adds copper + silk.
"""
import json
import os
import re
import subprocess
import sys
import pcbnew
import routelib
from routelib import F, B, MM, V

M = pcbnew.ToMM
HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_sch"))
STOCK = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
LIB, FPNAME = "Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"
DESC = "External button pads, no part fitted (1=BTN Pi GPIO4, 2=GND; Pi internal pull-up)"
J10_AT = (24.76, -60.8, 90.0)                 # r90: local +y (pin 2) -> +x
REF_AT = (27.9, -63.45)                       # F.SilkS "J10" above pad 2
PHONE_AT = (24.6, -63.45)                     # existing F.SilkS jack label "PHONE" (was (24.84, -60.9), now under J10)
C20_REF_AT = (27.15, -58.0)                   # C20 reference (was (26.9, -59.2), overlapped the J10 outline)
LABELS = (("BTN", 24.76), ("GND", 27.30))     # B.SilkS, under each pad
LABEL_Y = -58.95
LABEL_BOX = (22.5, -60.0, 29.5, -58.0)
W = 0.25
ROUTE = [
    (F, [(6.49, -45.885), (5.22, -44.615), (5.22, -42.85), (4.52, -42.15), (2.05, -42.15), (1.6, -41.7)]),
    (B, [(1.6, -41.7), (0.65, -42.65)]),
    (F, [(0.65, -42.65), (0.65, -51.55), (1.9, -52.8), (1.9, -55.0), (3.5, -56.6), (8.3, -56.6), (10.7, -59.0),
         (22.96, -59.0), (24.76, -60.8)]),
]
VIAS = [(1.6, -41.7), (0.65, -42.65)]


def _owned():
    return os.path.join(HERE, "owned_11.json")


def _is_label(d):
    if d.GetClass() != "PCB_TEXT" or d.GetLayer() != pcbnew.B_SilkS or d.GetText() not in ("BTN", "GND"):
        return False
    x, y = M(d.GetX()), M(d.GetY())
    return LABEL_BOX[0] <= x <= LABEL_BOX[2] and LABEL_BOX[1] <= y <= LABEL_BOX[3]


def remove_own():
    b = pcbnew.LoadBoard(routelib.PCB)
    old = set(json.load(open(_owned()))) if os.path.exists(_owned()) else set()
    doomed = [d for d in b.GetDrawings() if _is_label(d)]          # collect everything before the first Remove()
    doomed += [it for it in b.GetTracks() if it.m_Uuid.AsString() in old]
    for it in doomed:
        b.Remove(it)
    gone = len(doomed)
    b.Save(routelib.PCB)
    print("fix_11: removed %d own items" % gone)


def sch_uuid():
    s = open(SCH).read()
    i = s.find('(property "Reference" "J10"')
    assert i > 0, "run fix_11_btn_sch.py first"
    return re.findall(r'\(uuid "([^"]+)"\)', s[s.rfind("(symbol", 0, i):i])[-1]


def add_j10(b):
    btn = b.FindNet("/BTN")
    if btn is None:
        btn = pcbnew.NETINFO_ITEM(b, "/BTN"); b.Add(btn)
    for p in b.FindFootprintByReference("J1").Pads():
        if p.GetNumber() == "7":
            p.SetNet(btn)
    j10 = b.FindFootprintByReference("J10")
    if j10 is None:
        j10 = pcbnew.FootprintLoad(STOCK + LIB + ".pretty", FPNAME)
        j10.SetFPID(pcbnew.LIB_ID(LIB, FPNAME))
        j10.SetReference("J10"); j10.SetValue("BTN_EXT")
        j10.SetField("Datasheet", ""); j10.SetField("Description", DESC)
        j10.SetField("LCSC", ""); j10.SetField("MPN", "")
        for n in ("Datasheet", "Description", "LCSC", "MPN"):
            j10.GetField(n).SetVisible(False)
        j10.SetPath(pcbnew.KIID_PATH("/" + sch_uuid())); j10.SetSheetname("/"); j10.SetSheetfile("radio-hat-v08.kicad_sch")
        j10.SetAttributes(pcbnew.FP_THROUGH_HOLE | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
        j10.SetDNP(True)
        b.Add(j10)
        print("fix_11: J10 footprint added")
    gnd = b.FindNet("GND")
    for p in j10.Pads():
        p.SetNet(btn if p.GetNumber() == "1" else gnd)
    routelib.place(b, {"J10": J10_AT})
    rf = j10.Reference()
    rf.SetVisible(True); rf.SetLayer(pcbnew.F_SilkS)
    rf.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); rf.SetTextThickness(MM(0.15))
    rf.SetPosition(V(*REF_AT)); rf.SetTextAngleDegrees(0)
    vf = j10.Value()
    vf.SetLayer(pcbnew.F_Fab); vf.SetPosition(V(J10_AT[0] + 1.27, J10_AT[1])); vf.SetVisible(False)  # no room
    for g in j10.GraphicalItems():             # F.Fab ${REFERENCE}: small, on pad 2 inside the outline
        if g.GetClass() == "PCB_TEXT" and g.GetLayer() == pcbnew.F_Fab:
            g.SetTextSize(pcbnew.VECTOR2I(MM(0.5), MM(0.5))); g.SetTextThickness(MM(0.08))
            g.SetPosition(V(J10_AT[0] + 2.54, J10_AT[1])); g.SetTextAngleDegrees(0)
    n = 0
    for d in b.GetDrawings():                  # move the jack label out of the J10 outline (absolute, re-runnable)
        if d.GetClass() == "PCB_TEXT" and d.GetText() == "PHONE" and d.GetLayer() == pcbnew.F_SilkS:
            x, y = M(d.GetX()), M(d.GetY())
            if 20 < x < 30 and -64.5 < y < -59:
                d.SetPosition(V(*PHONE_AT)); n += 1
    assert n == 1, "PHONE label not found"
    c20 = b.FindFootprintByReference("C20").Reference()
    c20.SetPosition(V(*C20_REF_AT)); c20.SetTextAngleDegrees(0)


def labels(b):
    for s, x in LABELS:
        t = pcbnew.PCB_TEXT(b)
        t.SetText(s); t.SetLayer(pcbnew.B_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(MM(0.65), MM(0.8))); t.SetTextThickness(MM(0.15))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetMirrored(True); t.SetKeepUpright(False)
        t.SetPosition(V(x, LABEL_Y))
        b.Add(t)


def build(b, R):
    add_j10(b)
    for layer, pts in ROUTE:
        R.track("/BTN", W, pts, layer=layer)
    for x, y in VIAS:
        R.via("/BTN", x, y)
    labels(b)


if __name__ == "__main__":
    if "--add" in sys.argv:
        routelib.run("11", build)       # --add: no removal in this process, adds + fills + saves owned_11.json
    else:
        remove_own()                    # KiCad SWIG: no further board work in a process after Remove()
        subprocess.run([sys.executable, os.path.abspath(sys.argv[0]), "--add"], check=True)
