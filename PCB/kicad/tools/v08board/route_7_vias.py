"""Section 7 via planner: where may a GND via (0.6/0.3) go, and where should it go.

Allowed spot = the via disk lies wholly inside BOTH first-pass GND fills (GND_F, GND_B) - so it keeps the pour
clearance (>= 0.25) to every other net on both layers and the edge rule - and also:
  - >= 0.5 mm (copper) from every pad of any net (no via-in-pad, keeps thermal reliefs intact),
  - outside SMD courtyards (no vias under parts) and outside the boost box (hot loop, U4/L1 SW copper),
  - hole-to-hole >= 0.5 + margin to every drill, and >= MIN_SEP centre spacing to every existing via.
Passes (in order, each greedy on a 0.2 mm grid of allowed spots):
  1. FIX   : named spots for GND pads the pour cannot reach (from the section-6 log).
  2. CUT   : both sides of every non-GND B.Cu track (the cuts in the B.Cu plane), ~3.5 mm pitch.
  3. AUDIO : U6 / HP lines / U7 boxes, ~3 mm pitch.
  4. EDGE  : band 0.6..1.8 mm inside the board edge, ~5 mm pitch.
  5. GAP   : farthest-point fill until every allowed spot is within GAP_R of a GND via / THT pad
             (this also puts a via into every F.Cu fragment that has room for one).
"""
import math
import pcbnew

M, MM = pcbnew.ToMM, pcbnew.FromMM
STEP, VIA_R, DRILL = 0.2, 0.3, 0.3
MIN_SEP = 1.0
BOOST = (33.0, -62.0, 52.0, -48.6)
AUDIO = [(9.5, -59.5, 28.0, -40.5), (30.0, -24.5, 46.0, -10.5)]   # U6+HP lines+jack, U7+outputs+J7
EDGE = (0.0, -64.9, 63.48, 5.08)
FIX = [(33.2, -29.4)]            # U5.1/U5.3 GND (log, section 6)
CUT_PITCH, AUDIO_PITCH, EDGE_PITCH, GAP_R = 3.5, 3.0, 5.0, 4.5
CORNER = pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS


def _poly(s, grow):
    s = pcbnew.SHAPE_POLY_SET(s)
    s.Unfracture()
    s.Inflate(MM(grow), CORNER, MM(0.005))
    return s


def _rect(x0, y0, x1, y1):
    s = pcbnew.SHAPE_POLY_SET(); s.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        s.Append(MM(x), MM(y))
    return s


class Spots:
    def __init__(self, b):
        fills = {}
        for z in b.Zones():
            if z.GetZoneName() in ("GND_F", "GND_B"):
                fills[z.GetZoneName()] = _poly(z.GetFilledPolysList(z.GetLayer()), -VIA_R - 0.01)
        ok = fills["GND_F"]; ok.BooleanIntersection(fills["GND_B"])
        bad = pcbnew.SHAPE_POLY_SET()
        for fp in b.GetFootprints():
            for pd in fp.Pads():
                for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if pd.IsOnLayer(lay):
                        bad.Append(pd.GetEffectivePolygon(lay, pcbnew.ERROR_OUTSIDE))
            if fp.GetAttributes() & pcbnew.FP_SMD:
                bad.Append(fp.GetCourtyard(pcbnew.F_Cu))
        bad.Simplify()
        bad = _poly(bad, 0.5 + VIA_R)
        bad.Append(_rect(*BOOST))
        bad.Simplify()
        ok.BooleanSubtract(bad)
        self.drills = []          # (x, y, r) for hole-to-hole
        self.stitch = []          # GND vias + GND THT pads (count as plane ties)
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                self.drills.append((M(p.x), M(p.y), M(t.GetDrillValue()) / 2, True))
                if t.GetNetname() == "GND":
                    self.stitch.append((M(p.x), M(p.y)))
        for fp in b.GetFootprints():
            for pd in fp.Pads():
                if pd.HasHole():
                    p = pd.GetPosition()
                    self.drills.append((M(p.x), M(p.y), M(max(pd.GetDrillSize().x, pd.GetDrillSize().y)) / 2, False))
                    if pd.GetNetname() == "GND" and pd.IsOnLayer(pcbnew.F_Cu) and pd.IsOnLayer(pcbnew.B_Cu):
                        self.stitch.append((M(p.x), M(p.y)))
        x0, y0, x1, y1 = EDGE
        self.pts = []
        nx, ny = int((x1 - x0) / STEP), int((y1 - y0) / STEP)
        for i in range(nx + 1):
            for j in range(ny + 1):
                x, y = round(x0 + i * STEP, 2), round(y0 + j * STEP, 2)
                if ok.Contains(pcbnew.VECTOR2I(MM(x), MM(y))) and self._holes_ok(x, y):
                    self.pts.append((x, y))
        self.placed = []          # (x, y, kind)

    def _holes_ok(self, x, y):
        for hx, hy, r, is_via in self.drills:
            d = math.hypot(x - hx, y - hy)
            if d < DRILL / 2 + r + 0.55 or (is_via and d < MIN_SEP):
                return False
        return True

    def free(self, x, y, sep):
        return all(math.hypot(x - px, y - py) >= sep for px, py, _ in self.placed)

    def near_stitch(self, x, y):
        return min([math.hypot(x - px, y - py) for px, py in self.stitch] +
                   [math.hypot(x - px, y - py) for px, py, _ in self.placed] + [99.0])

    def take(self, tx, ty, reach, sep, kind):
        """Nearest allowed spot to (tx, ty) within reach that keeps sep to placed vias and MIN_SEP to stitches."""
        best = None
        for x, y in self.pts:
            d = math.hypot(x - tx, y - ty)
            if d <= reach and (best is None or d < best[0]) and self.free(x, y, sep) \
                    and all(math.hypot(x - px, y - py) >= MIN_SEP for px, py in self.stitch):
                best = (d, x, y)
        if best:
            self.placed.append((best[1], best[2], kind))
        return best is not None
