"""Helpers for silk_8.py: occupancy grid of silkscreen obstacles (0.1 mm cells) and text candidate search."""
import math
import pcbnew
G = 0.1  # grid cell, mm
mm = pcbnew.ToMM

def cells(x0, y0, x1, y1):
    for i in range(int(math.floor(x0 / G)), int(math.ceil(x1 / G))):
        for j in range(int(math.floor(y0 / G)), int(math.ceil(y1 / G))):
            yield (i, j)

class Grid:
    def __init__(self):
        self.hard, self.soft = set(), {}
    def rect(self, x0, y0, x1, y1, infl=0.0, soft=None):
        for c in cells(x0 - infl, y0 - infl, x1 + infl, y1 + infl):
            if soft is None: self.hard.add(c)
            else: self.soft[c] = max(self.soft.get(c, 0), soft)
    def seg(self, ax, ay, bx, by, infl, soft=None):
        n = max(1, int(math.hypot(bx - ax, by - ay) / 0.1))
        for k in range(n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            self.rect(x, y, x, y, infl, soft)
    def hit(self, r):
        h = False; s = 0.0
        for c in cells(*r):
            if c in self.hard: return None
            s += self.soft.get(c, 0)
        return s

def shape_pts(sh):
    """Polyline points (mm) approximating a footprint/board graphic; arcs/circles sampled."""
    t = sh.GetShape(); P = lambda p: (mm(p.x), mm(p.y))
    if t == pcbnew.SHAPE_T_SEGMENT: return [[P(sh.GetStart()), P(sh.GetEnd())]]
    if t in (pcbnew.SHAPE_T_RECT, pcbnew.SHAPE_T_RECTANGLE):
        a, b = P(sh.GetStart()), P(sh.GetEnd())
        c = [a, (b[0], a[1]), b, (a[0], b[1]), a]
        return [c] if not sh.IsSolidFill() else [[(a[0] + (b[0] - a[0]) * u / 4, a[1] + (b[1] - a[1]) * v / 4) for u in range(5)] for v in range(5)]
    if t == pcbnew.SHAPE_T_POLY:
        o = sh.GetPolyShape().Outline(0)
        pts = [P(o.CPoint(i)) for i in range(o.PointCount())]
        return [pts + pts[:1]]
    bb = sh.GetBoundingBox()
    if t == pcbnew.SHAPE_T_CIRCLE:
        c = P(sh.GetCenter()); r = mm(sh.GetRadius())
        return [[(c[0] + r * math.cos(a / 8 * 6.2832), c[1] + r * math.sin(a / 8 * 6.2832)) for a in range(9)]]
    return [[(mm(bb.GetLeft()), mm(bb.GetTop())), (mm(bb.GetRight()), mm(bb.GetBottom()))]]  # arc: diagonal of bbox

def add_shape(g, sh, infl, soft=None):
    w = mm(sh.GetWidth()) / 2 + infl
    for pl in shape_pts(sh):
        for a, b in zip(pl, pl[1:]): g.seg(a[0], a[1], b[0], b[1], w, soft)

def text_ext(t, ang):
    """Half extents + centre offset of text t at angle ang when placed with centre-justified position."""
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetTextAngleDegrees(ang); t.SetPosition(pcbnew.VECTOR2I(0, 0))
    b = t.GetBoundingBox()
    return mm(b.GetWidth()) / 2, mm(b.GetHeight()) / 2, mm(b.GetLeft() + b.GetRight()) / 2, mm(b.GetTop() + b.GetBottom()) / 2

def candidates(bb, hx, hy, sides="TBLR", maxgap=3.0, step=0.2, ostep=0.4):
    """Centres around bbox (x0,y0,x1,y1) ordered later by cost: yields (cx, cy, cost)."""
    cx0, cy0 = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    hw, hh = (bb[2] - bb[0]) / 2, (bb[3] - bb[1]) / 2
    gap = 0.0
    while gap <= maxgap:
        for s in sides:
            span = (hw if s in "TB" else hh) + 0.5
            k = 0
            while k * ostep <= span:
                for sg in ((1, -1) if k else (1,)):
                    o = sg * k * ostep
                    if s == "T": yield cx0 + o, bb[1] - gap - hy, gap + abs(o) * 0.15
                    if s == "B": yield cx0 + o, bb[3] + gap + hy, gap + abs(o) * 0.15
                    if s == "L": yield bb[0] - gap - hx, cy0 + o, gap + abs(o) * 0.15
                    if s == "R": yield bb[2] + gap + hx, cy0 + o, gap + abs(o) * 0.15
                k += 1
        gap += step
