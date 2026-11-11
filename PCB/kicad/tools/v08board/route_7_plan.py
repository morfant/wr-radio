"""Section 7 via passes (FIX, CUT, AUDIO, EDGE, GAP) over route_7_vias.Spots - see route_7_vias.py docstring."""
import collections
import math
import pcbnew
from route_7_vias import (Spots, M, MM, CORNER, FIX, AUDIO, EDGE, CUT_PITCH, AUDIO_PITCH, EDGE_PITCH, GAP_R, MIN_SEP)


def cut_pass(b, S):
    for t in b.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetLayer() != pcbnew.B_Cu or t.GetNetname() == "GND":
            continue
        x1, y1, x2, y2 = M(t.GetStart().x), M(t.GetStart().y), M(t.GetEnd().x), M(t.GetEnd().y)
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 0.05:
            continue
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        off = M(t.GetWidth()) / 2 + 0.75
        n = max(1, int(math.ceil(L / CUT_PITCH)))
        for k in range(n + 1):
            px, py = x1 + ux * L * k / n, y1 + uy * L * k / n
            for sgn in (1, -1):
                tx, ty = px - uy * off * sgn, py + ux * off * sgn
                if S.near_stitch(tx, ty) >= CUT_PITCH * 0.7:
                    S.take(tx, ty, 1.0, MIN_SEP, "cut")


def box_pass(S, boxes, pitch, kind):
    for x0, y0, x1, y1 in boxes:
        y = y0 + pitch / 2
        while y < y1:
            x = x0 + pitch / 2
            while x < x1:
                if S.near_stitch(x, y) >= pitch * 0.7:
                    S.take(x, y, pitch * 0.4, MIN_SEP, kind)
                x += pitch
            y += pitch


def edge_pass(S, inset=1.2, step=0.5):
    x0, y0, x1, y1 = EDGE[0] + inset, EDGE[1] + inset, EDGE[2] - inset, EDGE[3] - inset
    ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for (ax, ay), (bx, by) in zip(ring, ring[1:]):
        L = math.hypot(bx - ax, by - ay)
        for k in range(int(L / step) + 1):
            tx, ty = ax + (bx - ax) * k * step / L, ay + (by - ay) * k * step / L
            if S.near_stitch(tx, ty) >= EDGE_PITCH * 0.9:
                S.take(tx, ty, 0.7, MIN_SEP, "edge")


def gap_pass(S):
    dist = [S.near_stitch(x, y) for x, y in S.pts]
    while dist:
        i = max(range(len(dist)), key=dist.__getitem__)
        if dist[i] < GAP_R:
            break
        x, y = S.pts[i]
        S.placed.append((x, y, "gap"))
        dist = [min(d, math.hypot(px - x, py - y)) for d, (px, py) in zip(dist, S.pts)]


def neck_pass(b, S, r=1.0, min_area=3.0, want=2):
    """GND_B opened by r: a piece that comes apart was tied to the rest of B.Cu only through a neck < 2r.
    Give each such piece (>= min_area) up to `want` ties of its own so F.Cu carries it too."""
    zb = [z for z in b.Zones() if z.GetZoneName() == "GND_B"][0]
    s = pcbnew.SHAPE_POLY_SET(zb.GetFilledPolysList(pcbnew.B_Cu)); s.Unfracture()
    s.Inflate(MM(-r), CORNER, MM(0.01)); s.Inflate(MM(r), CORNER, MM(0.01))
    if s.OutlineCount() < 2:
        return
    for i in range(s.OutlineCount()):
        one = pcbnew.SHAPE_POLY_SET(); one.AddOutline(s.Outline(i))
        if one.Area() / 1e12 < min_area or one.Area() == max(s.Outline(k).Area() for k in range(s.OutlineCount())):
            continue
        inside = lambda x, y: one.Contains(pcbnew.VECTOR2I(MM(x), MM(y)))
        have = sum(1 for x, y in S.stitch if inside(x, y)) + sum(1 for x, y, _ in S.placed if inside(x, y))
        cand = [(x, y) for x, y in S.pts if inside(x, y)]
        while have < want and cand:
            x, y = max(cand, key=lambda q: S.near_stitch(*q))
            if S.near_stitch(x, y) < MIN_SEP:
                break
            S.placed.append((x, y, "neck")); have += 1


def plan(b):
    S = Spots(b)
    print("allowed grid spots: %d, existing GND stitches: %d" % (len(S.pts), len(S.stitch)))
    for x, y in FIX:
        if not S.take(x, y, 1.2, MIN_SEP, "fix"):
            print("  FIX spot (%.2f, %.2f): no allowed spot within 1.2 mm" % (x, y))
    cut_pass(b, S)
    box_pass(S, AUDIO, AUDIO_PITCH, "audio")
    edge_pass(S)
    neck_pass(b, S)
    gap_pass(S)
    return S.placed


def report(vias):
    print("stitching vias:", len(vias), dict(collections.Counter(k for _, _, k in vias)))
