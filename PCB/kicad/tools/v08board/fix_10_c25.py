"""Section 10: final review M2 -- move C25 out of the J4 plug space (x 8.66..23.66, y -41.3..+2.8).
KiCad python, GUI closed. Re-runnable like fix_9.py: the old copper this replaces is deleted by geometry
(no-op on a re-run), items this script added are tracked in owned_10.json (routelib.run).
  python3 fix_10_c25.py            (board = $WR_PCB or the project board)

Moves
  J9  (DNP UART pads)  (10.5, -48.42) -> (10.5, -50.32)   up 1.9 mm; courtyard bottom -41.525 -> -43.425
  C25 (22 uF 0805)     (11.25, -40.3) -> (10.9, -42.35) r180; body y -42.975..-41.725, courtyard bottom -41.325
  R23 (4.7k 0603)      (13.82, -42.75) -> (13.82, -42.84); courtyard bottom -41.225 -> -41.315
Reroutes
  /SCL      now passes south of C25: (12.445,-38.441) W -> 45 deg to (8.909,-41.091) -> N to -43.6 -> jog to x 8.457
  /I2S_DIN  between J9.3 and C25 (y -43.7), 45 deg into the R23 pad gap (y -42.84), then the old path
  /HP_DET   C25.1 -> R23.2 on F.Cu; via moved to (11.2, -41.13) on the old B.Cu diagonal (B.Cu cut 0.55 mm shorter)
  /HP_TN    last F.Cu segment re-ends on R23.1
  /UART_TX, /UART_RX  B.Cu tails re-end on the moved J9 pads
  Silk      fix_9_silk B.SilkS J9 labels GND/TX/RX follow the pads (re-run this after fix_9.py)
  GND       C25.2 via (9.95, -41.15); old C25 GND via (10.3,-38.9) and stub, and stitching via (11.2,-50.7)
            (now inside J9.1, hole-to-hole) removed
"""
import pcbnew
import routelib
from routelib import F, B

M = pcbnew.ToMM
J9_LABELS = {"GND": -50.32, "TX": -47.78, "RX": -45.24}   # fix_9_silk B.SilkS labels beside the moved J9 pads
PLACE = {"J9": (10.5, -50.32, 0.0), "C25": (10.9, -42.35, 180.0), "R23": (13.82, -42.84, -90.0)}

# old copper replaced by this section: (net, layer or None for via, (x1, y1), (x2, y2) or None)
OLD_TRACKS = [
    ("/SCL", F, (12.445, -38.441), (11.32, -39.566)),
    ("/SCL", F, (11.32, -39.566), (11.32, -40.9)),
    ("/SCL", F, (11.32, -40.9), (10.685, -41.535)),
    ("/SCL", F, (10.685, -41.535), (10.605, -41.535)),
    ("/SCL", F, (10.605, -41.535), (8.909, -43.231)),
    ("/SCL", F, (8.909, -43.231), (8.909, -45.003)),
    ("/SCL", F, (8.909, -45.003), (8.457, -45.454)),
    ("/SCL", F, (8.457, -45.454), (8.457, -46.458)),
    ("/I2S_DIN", F, (9.302, -47.126), (9.302, -45.416)),
    ("/I2S_DIN", F, (9.302, -45.416), (9.62, -45.098)),
    ("/I2S_DIN", F, (9.62, -45.098), (9.62, -44.93)),
    ("/I2S_DIN", F, (9.62, -44.93), (9.94, -44.61)),
    ("/I2S_DIN", F, (9.94, -44.61), (10.965, -44.61)),
    ("/I2S_DIN", F, (10.965, -44.61), (12.825, -42.75)),
    ("/I2S_DIN", F, (12.825, -42.75), (14.621, -42.75)),
    ("/I2S_DIN", F, (14.621, -42.75), (14.621, -41.992)),
    ("/HP_DET", F, (13.82, -41.925), (12.2, -40.3)),
    ("/HP_DET", F, (12.2, -40.3), (12.2, -40.909)),
    ("/HP_DET", F, (12.2, -40.909), (11.589, -41.519)),
    ("/HP_DET", B, (8.925, -38.855), (11.589, -41.519)),
    ("/HP_TN", F, (13.6, -47.4), (13.82, -43.575)),
    ("GND", F, (10.3, -40.3), (10.3, -38.9)),
    ("/UART_TX", B, (8.6, -47.155), (10.5, -45.885)),
    ("/UART_TX", B, (10.5, -45.88), (10.5, -45.885)),
    ("/UART_RX", B, (8.6, -44.615), (10.5, -43.345)),
    ("/UART_RX", B, (10.5, -43.34), (10.5, -43.345)),
]
OLD_VIAS = [("/HP_DET", (11.589, -41.519)), ("GND", (10.3, -38.9)), ("GND", (11.2, -50.7))]


def _near(a, b, tol=0.003):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def remove_old():
    b = pcbnew.LoadBoard(routelib.PCB)
    gone = 0
    for t in list(b.GetTracks()):
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            p = (M(t.GetX()), M(t.GetY()))
            if any(net == n and _near(p, q) for n, q in OLD_VIAS):
                b.Remove(t); gone += 1
            continue
        s, e = (M(t.GetStart().x), M(t.GetStart().y)), (M(t.GetEnd().x), M(t.GetEnd().y))
        for n, lay, p1, p2 in OLD_TRACKS:
            if net == n and t.GetLayer() == lay and ((_near(s, p1) and _near(e, p2)) or (_near(s, p2) and _near(e, p1))):
                b.Remove(t); gone += 1
                break
    b.Save(routelib.PCB)
    print("fix_10: removed %d old items (expected %d on first run)" % (gone, len(OLD_TRACKS) + len(OLD_VIAS)))


def j9_labels(b):
    n = 0
    for d in b.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.B_SilkS and d.GetText() in J9_LABELS:
            p = d.GetPosition()
            if 11.0 < M(p.x) < 14.5 and -52.0 < M(p.y) < -42.0:
                d.SetPosition(pcbnew.VECTOR2I(p.x, pcbnew.FromMM(J9_LABELS[d.GetText()]))); n += 1
    print("fix_10: J9 labels moved", n)


def build(b, R):
    routelib.place(b, PLACE)
    j9_labels(b)
    W = 0.25
    R.track("/SCL", W, [(12.445, -38.441), (11.559, -38.441), (8.909, -41.091), (8.909, -43.6),
                        (8.457, -44.052), (8.457, -46.458)])
    R.track("/I2S_DIN", W, [(9.302, -47.126), (9.302, -44.0), (9.602, -43.7), (12.3, -43.7), (13.16, -42.84),
                            (14.621, -42.84), (14.621, -41.992)])
    R.track("/HP_DET", W, [(8.925, -38.855), (11.2, -41.13)], layer=B)
    R.via("/HP_DET", 11.2, -41.13)
    R.track("/HP_DET", W, [(11.2, -41.13), (11.85, -41.78)])                   # into C25.1
    R.track("/HP_DET", W, [(11.85, -42.35), (12.185, -42.015), (13.82, -42.015)])  # C25.1 -> R23.2
    R.track("/HP_TN", W, [(13.6, -47.4), (13.82, -43.665)])
    R.via("GND", 9.95, -41.15)
    R.track("GND", 0.4, [(9.95, -41.15), (9.95, -42.35)])                      # C25.2
    R.track("/UART_TX", W, [(8.6, -47.155), (9.225, -47.78), (10.5, -47.78)], layer=B)
    R.track("/UART_RX", W, [(8.6, -44.615), (9.225, -45.24), (10.5, -45.24)], layer=B)


if __name__ == "__main__":
    import subprocess
    import sys
    if "--add" in sys.argv or "--own" in sys.argv:
        routelib.run("10", build)
    else:
        remove_old()                      # KiCad SWIG: no further board work in a process after Remove()
        subprocess.run([sys.executable, sys.argv[0], "--own"], check=True)
