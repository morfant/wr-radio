"""Section 9: fixes from the independent layout review (v08_layout_review.md), KiCad python, GUI closed.
Re-runnable: items this script added last run are tracked in owned_9.json and removed first (routelib.run);
the review targets it replaces (old SW neck tracks, the 6 old U1 EP vias) are deleted by geometry, so a second
run finds nothing old and re-adds the same new items. Run AFTER any section script that is re-run later.
  python3 fix_9.py            (board = $WR_PCB or the project board)

S1  SYS battery->boost path: F.Cu zone FIX9_SYS_F (prio 2) Q1.2 -> C5.1 -> L1.2/D1 cathode, merges CHG_SYS_F.
    B- exit: zone FIX9_BM_F over U3 S1 pins 2/3 and down the 1.2 mm stem.
S2  SW neck: 0.25 (between U4 pins) -> 0.35 (between pin rows, 0.2 to both rows) -> 0.8 from x 43.2 to L1.1.
S3  U1 EP: 6 vias -> 12 (4x3, pitch 0.85, 0.6/0.3) inside the 3.3x2.41 EP.
S4  D1 VBUS side: zone FIX9_VBUS_F south of CHG_VBUS_F (anode copper).
S5  GND stitching vias beside the HP_TN / DAC_R B.Cu cuts (route_7_vias.Spots rules).
M1  D2/D3 -> local footprint radio-hat-v08:LED_XINGLIGHT_XL-1606_Horizontal (pads 0.77x0.95 @ +-0.815).
Silk (N9/N10) is in fix_9_silk.py (called at the end).
"""
import math
import pcbnew
import routelib
from routelib import F, B, MM, V
import route_7_vias
import fix_9_silk

M = pcbnew.ToMM
EP_OLD = (43.35, -44.805, 46.65, -42.395)           # U1.9 pad box
EP_X, EP_Y = (43.725, 44.575, 45.425, 46.275), (-42.75, -43.6, -44.45)
SYS_POLY = [(36.5, -47.0), (37.7, -47.0), (37.7, -48.95), (51.3, -48.95), (51.3, -53.3), (47.5, -53.3),
            (47.5, -52.7), (43.0, -52.7), (43.0, -50.7), (36.5, -50.7)]
VBUS_POLY = [(51.6, -49.0), (54.8, -49.0), (54.8, -52.8), (51.6, -52.8)]
BM_POLY = [(53.0, -14.05), (56.5, -14.05), (56.5, -12.95), (55.6, -12.95), (55.6, -7.5), (54.2, -7.5),
           (54.2, -12.95), (53.0, -12.95)]
# stitching targets: (x, y) beside HP_TN (B.Cu x 13.55, y -56.4..-47.4) and DAC_R (y -53.6, x 18..24.7)
STITCH = [(x, y) for y in (-55.0, -53.0, -51.0, -49.0) for x in (12.5, 14.6)] + \
         [(x, y) for x in (18.5, 20.5, 22.5, 24.0) for y in (-52.6, -54.6)]
LED_FP = pcbnew.LIB_ID("radio-hat-v08", "LED_XINGLIGHT_XL-1606_Horizontal")


def remove_old():
    """Delete the review targets that this script replaces (no-op on a re-run)."""
    b = pcbnew.LoadBoard(routelib.PCB)
    gone = 0
    for t in list(b.GetTracks()):
        if t.GetNetname() == "/SW":
            b.Remove(t); gone += 1
        elif t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND":
            x, y = M(t.GetX()), M(t.GetY())
            if EP_OLD[0] < x < EP_OLD[2] and EP_OLD[1] < y < EP_OLD[3] and \
                    min(abs(x - ex) for ex in EP_X) > 0.05:      # old grid, not ours
                b.Remove(t); gone += 1
    b.Save(routelib.PCB)
    print("fix_9: removed %d review targets" % gone)


def leds(b):
    for ref in ("D2", "D3"):
        fp = b.FindFootprintByReference(ref)
        fp.SetFPID(LED_FP)
        for p in fp.Pads():
            sx = -1 if p.GetNumber() == "1" else 1
            p.SetSize(pcbnew.VECTOR2I(MM(0.77), MM(0.95)))
            p.SetFPRelativePosition(pcbnew.VECTOR2I(MM(0.815 * sx), 0))
    d3 = b.FindFootprintByReference("D3")                  # board copy of the schematic fields (parity)
    for k, v in (("LCSC", "C965863"), ("MPN", "XL-1606UGC")):
        d3.SetField(k, v)


def stitch(b, R):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    sp = route_7_vias.Spots(b)
    got = []
    for x, y in STITCH:
        if sp.take(x, y, 1.5, 1.4, "FIX9"):
            px, py, _ = sp.placed[-1]
            R.via("GND", px, py); got.append((px, py))
    print("fix_9: stitching vias", len(got), got)


def build(b, R):
    # S2 SW neck
    R.track("/SW", 0.25, [(42.0, -55.013), (42.0, -54.3)])
    R.track("/SW", 0.35, [(42.0, -54.3), (43.2, -54.3)])
    R.track("/SW", 0.8, [(43.2, -54.3), (44.75, -54.3)])
    # S3 EP vias
    for x in EP_X:
        for y in EP_Y:
            R.via("GND", x, y)
    # S1 / S4 zones
    # prio 3: same-net overlap with the prio-2 CHG_SYS_F / CHG_VBUS_F is then not a zones_intersect error
    R.zone("FIX9_SYS_F", "/SYS", SYS_POLY, prio=3)
    R.zone("FIX9_VBUS_F", "VBUS", VBUS_POLY, prio=3)
    R.zone("FIX9_BM_F", "/B-", BM_POLY, prio=3)
    leds(b)
    stitch(b, R)
    fix_9_silk.apply(b)


if __name__ == "__main__":
    import subprocess
    import sys
    if "--add" in sys.argv or "--own" in sys.argv:
        routelib.run("9", build)          # removes owned_9 items, then adds in a fresh process
    else:
        remove_old()                      # KiCad SWIG: no further board work in a process after Remove()
        subprocess.run([sys.executable, sys.argv[0], "--own"], check=True)
