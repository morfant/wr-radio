"""Routing section 1: TPS61023 boost converter (U4, L1, C5, C6, C7, C8, C26, C27, R11, R12, R13).
Run with KiCad's python (KiCad GUI closed):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 route_1_boost.py

Re-runnable: first removes tracks/vias of the boost nets inside the boost region and the zones named BST_*,
then sets the boost part positions, adds tracks/vias/zones (all locked) and refills every zone.

Layout follows TI SLVSF14B section 10 (Figure 10-1):
  * U4 rotated 90 deg so pins 6/5/4 (VOUT/SW/GND) face up and pins 1/2/3 (FB/EN/VIN) face down.
  * Hot loop  SW -> rectifier -> VOUT(6) -> C6/C7 -> GND(4): C6 and C7 sit right above the pins with their
    +5V pads on the pin-6 side and their GND pads on the pin-4 side, joined by small F.Cu zones
    (BST_5V_F, BST_GND_F), no vias in the loop.
  * SW leaves pin 5 under the package body and exits between pins 4 and 3 to L1 (as in Fig. 10-1).
  * FB divider (R11/C26/R12) to the left, away from SW/L1; R12 GND has its own via (quiet ground).
  * EN -> R13 on F.Cu below the IC, R13 GND shares C5's GND via.
"""
import os
import subprocess
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_pcb"))
MM = pcbnew.FromMM
NETS = ["+5V", "/SW", "/SYS", "/FB", "/BST_EN", "GND"]
REGION = (30.0, -63.0, 52.5, -49.6)          # x0, y0, x1, y1 (mm) area owned by this section

# ---- part placement (absolute, mm / deg) -----------------------------------------------------------
PLACE = {
    "U4":  (42.0, -54.3, 90),     # was (42.0,-53.5) r0
    "L1":  (46.6, -54.3, 0),      # was (46.6,-53.5)
    "C6":  (41.9, -56.59, 0),     # was (42.6,-56.3) r90
    "C7":  (41.9, -58.66, 0),     # was (40.45,-57.1) r90
    "C5":  (42.4, -50.85, 180),   # was (41.9,-50.5) r0
    "R11": (39.3, -54.1, 270),    # was (38.2,-53.2) r0
    "C26": (37.7, -54.1, 270),    # was (37.9,-55.1) r0
    "R12": (36.1, -54.1, 90),     # was (38.2,-51.3) r180
    "R13": (38.6, -51.5, 0),      # was (45.5,-58.5) r0
}
# C8 (34.5,-60.8) and C27 (50.6,-53.5) unchanged.
REF_TEXT = {"R13": (38.6, -50.2), "R12": (35.4, -51.9)}   # reference text moved off pads (absolute mm, upright)

F, B = pcbnew.F_Cu, pcbnew.B_Cu
# ---- tracks: (net, width, layer, [points]) ----------------------------------------------------------
TRACKS = [
    # SW: pin5 -> under body -> between pins 4/3 -> L1.1   (narrow only where it passes between pins)
    ("/SW", 0.20, F, [(42.0, -54.9), (42.0, -54.5), (42.2, -54.3)]),
    ("/SW", 0.30, F, [(42.2, -54.3), (43.3, -54.3)]),
    ("/SW", 0.80, F, [(43.3, -54.3), (44.75, -54.3)]),
    # VIN: pin3 -> C5.1 (SYS)
    ("/SYS", 0.30, F, [(42.55, -53.35), (43.35, -52.55)]),
    ("/SYS", 0.60, F, [(43.35, -52.55), (43.35, -50.85)]),
    # SYS trunk: C5.1 -> under L1 -> L1.2 -> C27.1
    ("/SYS", 0.80, F, [(43.35, -50.85), (47.45, -50.85), (48.45, -51.85), (48.45, -53.4)]),
    ("/SYS", 0.80, F, [(48.45, -52.55), (50.6, -52.55)]),
    # EN: pin2 -> down -> left -> R13.1
    ("/BST_EN", 0.20, F, [(42.0, -53.4), (42.0, -52.4)]),
    ("/BST_EN", 0.25, F, [(42.0, -52.4), (38.2, -52.4), (37.775, -51.975), (37.775, -51.5)]),
    # FB: pin1 -> bus along the bottom pads of R11/C26/R12
    ("/FB", 0.25, F, [(41.45, -53.588), (41.263, -53.588), (40.95, -53.275), (36.1, -53.275)]),
    # +5V trunk: BST_5V_F zone -> under C8 -> C8.1 (exit to J1 continues from C8.1)
    ("+5V", 1.00, F, [(37.6, -59.0), (31.8, -59.0), (31.8, -60.8)]),
    # GND stubs to vias
    ("GND", 0.50, F, [(41.45, -50.85), (40.35, -50.85)]),           # C5.2 -> via
    ("GND", 0.40, F, [(39.425, -51.5), (40.35, -50.85)]),           # R13.2 -> same via
    ("GND", 0.40, F, [(36.1, -54.925), (36.1, -56.1)]),             # R12.2 -> via (quiet ground)
    ("GND", 0.80, F, [(37.2, -60.8), (39.6, -60.8)]),               # C8.2 -> via
    ("GND", 0.80, F, [(37.2, -60.8), (37.2, -62.25)]),              # C8.2 -> via
    ("GND", 0.60, F, [(50.6, -54.45), (51.85, -54.45)]),            # C27.2 -> via
    ("GND", 0.60, F, [(50.6, -54.45), (50.6, -55.55)]),             # C27.2 -> via
]
VIAS = [  # (net, x, y)  0.6/0.3
    ("GND", 43.75, -56.05), ("GND", 43.75, -57.25), ("GND", 43.75, -58.45), ("GND", 42.85, -60.05),  # hot-loop GND
    ("GND", 40.35, -50.85),                      # C5 / R13
    ("GND", 36.1, -56.1),                        # R12 (FB divider ground)
    ("GND", 39.6, -60.8), ("GND", 37.2, -62.25),  # C8
    ("GND", 51.85, -54.45), ("GND", 50.6, -55.55),  # C27
]
ZONES = [  # (name, net, polygon)  F.Cu, priority 2, solid pad connection
    ("BST_5V_F", "+5V", [(37.2, -59.6), (41.7, -59.6), (41.7, -54.6), (37.2, -54.6)]),
    ("BST_GND_F", "GND", [(42.2, -60.5), (44.4, -60.5), (44.4, -54.6), (42.2, -54.6)]),
]


def inside(p):
    return REGION[0] <= pcbnew.ToMM(p.x) <= REGION[2] and REGION[1] <= pcbnew.ToMM(p.y) <= REGION[3]


def main():
    b = pcbnew.LoadBoard(PCB)
    net = {n: b.FindNet(n) for n in NETS}
    for n, ni in net.items():
        assert ni is not None, n
    # 1) placement 
    for ref, (x, y, r) in PLACE.items():
        fp = b.FindFootprintByReference(ref)
        fp.SetOrientationDegrees(r)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    for ref, (x, y) in REF_TEXT.items():
        rf = b.FindFootprintByReference(ref).Reference()
        rf.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); rf.SetTextAngleDegrees(0)
    # 2) clean this section
    gone = 0
    old_zones = [z for z in (b.GetArea(i) for i in range(b.GetAreaCount())) if z.GetZoneName().startswith("BST_")]
    for t in list(b.GetTracks()):
        if t.GetNetname() not in NETS:
            continue
        if t.GetClass() == "PCB_VIA":
            hit = inside(t.GetPosition())
        else:
            hit = inside(t.GetStart()) or inside(t.GetEnd())
        if hit:
            b.Remove(t); gone += 1
    for z in old_zones:
        b.Remove(z); gone += 1
    print("removed", gone, "items")
    b.Save(PCB)
    # KiCad 10 SWIG loses item types after BOARD.Remove(), so the add phase runs in a fresh process.
    subprocess.run([sys.executable, os.path.abspath(__file__), "--add"], check=True)


def add():
    b = pcbnew.LoadBoard(PCB)
    net = {n: b.FindNet(n) for n in NETS}
    # 3) tracks / vias / zones
    nt = 0
    for nm, w, lay, pts in TRACKS:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
            t.SetWidth(MM(w)); t.SetLayer(lay); t.SetNet(net[nm]); t.SetLocked(True)
            b.Add(t); nt += 1
    for nm, x, y in VIAS:
        v = pcbnew.PCB_VIA(b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        v.SetLayerPair(F, B)
        v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3))
        v.SetNet(net[nm]); v.SetLocked(True)
        b.Add(v)
    for name, nm, poly in ZONES:
        z = pcbnew.ZONE(b)
        z.SetLayer(F); z.SetNet(net[nm]); z.SetZoneName(name)
        z.SetAssignedPriority(2)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetLocalClearance(MM(0.2))
        z.SetMinThickness(MM(0.2))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline(); ol.NewOutline()
        for x, y in poly:
            ol.Append(MM(x), MM(y))
        z.SetLocked(True)
        b.Add(z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    print("added", nt, "track segments,", len(VIAS), "vias,", len(ZONES), "zones; saved", PCB)


if __name__ == "__main__":
    add() if "--add" in sys.argv else main()
