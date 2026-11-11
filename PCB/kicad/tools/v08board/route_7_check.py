"""Section 7 checks (KiCad python, read-only on the board file): pour fragments, islands removed, B.Cu necks.
usage: route_7_check.py [board]
  - fragments of GND_F / GND_B and how many GND vias / THT pads tie each one to the other layer
  - islands removed = fragments with island removal NEVER minus ALWAYS (refilled in memory, not saved)
  - B.Cu necks: GND_B opened by r (deflate then inflate). Pieces that come apart at r were joined only through
    a neck narrower than 2r on B.Cu; each piece is listed with its own stitch count (F.Cu ties it back if > 0).
"""
import sys
import pcbnew
import routelib

M, MM = pcbnew.ToMM, pcbnew.FromMM
CORNER = pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS
b = pcbnew.LoadBoard(sys.argv[1] if len(sys.argv) > 1 else routelib.PCB)
pours = {z.GetZoneName(): z for z in b.Zones() if z.GetZoneName() in ("GND_F", "GND_B")}
ties = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
nvia = len(ties)
ties += [p.GetPosition() for fp in b.GetFootprints() for p in fp.Pads()
         if p.GetNetname() == "GND" and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]


def pieces(s, min_area=0.0):
    out = []
    for i in range(s.OutlineCount()):
        one = pcbnew.SHAPE_POLY_SET(); one.AddOutline(s.Outline(i))
        for h in range(s.HoleCount(i)):
            one.AddHole(s.Hole(i, h))
        a = one.Area() / 1e12
        if a >= min_area:
            bb = s.Outline(i).BBox()
            n = sum(1 for p in ties if one.Contains(p))
            out.append((a, n, (M(bb.GetX()), M(bb.GetY()), M(bb.GetRight()), M(bb.GetBottom()))))
    return sorted(out, reverse=True)


def show(rows, limit=12):
    for a, n, bb in rows[:limit]:
        print("    %7.1f mm2  ties %3d  bbox x %.1f..%.1f  y %.1f..%.1f" % (a, n, bb[0], bb[2], bb[1], bb[3]))


print("GND vias on board:", nvia)
for name, z in sorted(pours.items()):
    rows = pieces(z.GetFilledPolysList(z.GetLayer()))
    print("%s: %d fragments, total %.0f mm2, untied %d" % (name, len(rows), sum(r[0] for r in rows),
                                                        sum(1 for r in rows if r[1] == 0)))
    show([r for r in rows if r[1] == 0] + rows[:3])
for z in pours.values():
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
for name, z in sorted(pours.items()):
    print("%s with islands kept: %d fragments" % (name, z.GetFilledPolysList(z.GetLayer()).OutlineCount()))
for z in pours.values():
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
zb = pours["GND_B"]
for r in (0.5, 1.0, 1.5):
    s = pcbnew.SHAPE_POLY_SET(zb.GetFilledPolysList(pcbnew.B_Cu)); s.Unfracture()
    s.Inflate(MM(-r), CORNER, MM(0.01)); s.Inflate(MM(r), CORNER, MM(0.01))
    rows = pieces(s, 1.0)
    print("GND_B opened r=%.1f (neck < %.1f mm): %d pieces >= 1 mm2" % (r, 2 * r, len(rows)))
    show(rows[1:] if len(rows) > 1 else [], 15)
