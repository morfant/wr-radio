"""Copper usage summary (KiCad python): via count, F/B track length, per-net B.Cu length for section-6 nets,
and section-6 copper inside the guard boxes (boost, audio). usage: route_6_stats.py [board]"""
import collections
import sys
import pcbnew
import routelib
from route_6_prep_dsn import KEEP_NETS

GUARD = {  # board mm: x0, y0, x1, y1
    "boost U4/L1/C6": (33.0, -62.0, 52.0, -48.6),
    "U6 / HP lines": (9.5, -59.5, 28.0, -47.6),
    "U7 outputs/J7": (37.6, -22.2, 46.0, -11.0),
}
M = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1] if len(sys.argv) > 1 else routelib.PCB)
L = collections.Counter()
nb = collections.Counter()
vias = collections.Counter()
hits = []
sig = set(KEEP_NETS) | {"/BST_EN", "/VBAT_SENSE", "/VBUS_SENSE"}
for t in b.GetTracks():
    net = t.GetNetname()
    if t.GetClass() == "PCB_VIA":
        vias["all"] += 1
        if net in sig:
            vias[net] += 1
        continue
    lay = "F" if t.GetLayer() == pcbnew.F_Cu else "B"
    L[lay] += M(t.GetLength())
    if net in sig:
        L["sig" + lay] += M(t.GetLength())
        if lay == "B":
            nb[net] += M(t.GetLength())
        for name, (x0, y0, x1, y1) in GUARD.items():
            for p in (t.GetStart(), t.GetEnd()):
                if x0 < M(p.x) < x1 and y0 < M(p.y) < y1:
                    hits.append((name, net, lay, round(M(p.x), 2), round(M(p.y), 2)))
print("vias total %d, section-6 nets %d" % (vias["all"], sum(v for k, v in vias.items() if k != "all")))
print("track length F %.1f mm, B %.1f mm (section-6 nets: F %.1f, B %.1f)" % (L["F"], L["B"], L["sigF"], L["sigB"]))
for net, l in sorted(nb.items(), key=lambda kv: -kv[1]):
    print("   B.Cu %-12s %5.1f mm  vias %d" % (net, l, vias[net]))
for h in hits:
    print("   in guard box:", h)
