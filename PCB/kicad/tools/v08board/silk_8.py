"""v08 silkscreen cleanup (2026-11-12). Copper is untouched: only silk text is moved/resized/hidden/added.
Usage (KiCad GUI closed, KiCad python):  python3 silk_8.py [in.kicad_pcb [out.kicad_pcb]]   (default: project board in place, .bak_before_silk made once)
Re-runnable: refs are re-placed from scratch each run; added labels are matched by text."""
import os, sys, shutil, math
import pcbnew
from silklib_8 import *
HERE = os.path.dirname(os.path.abspath(__file__))
BRD = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_pcb"))
src = sys.argv[1] if len(sys.argv) > 1 else BRD
dst = sys.argv[2] if len(sys.argv) > 2 else src
H, TH = 0.8, 0.15
NEW = {  # text: (anchor ref, sides, angles)
    "USB-C": ("J2", "TL", (0, 90)), "BAT": ("J3", "TLR", (0, 90)), "PHONE": ("J8", "BTR", (0, 90)),
    "CHG": ("D2", "RLT", (0, 90)), "FULL": ("D3", "RLB", (0, 90))}
NOREF = ("J9", "H1", "H2", "H3", "H4", "H5")           # mounting holes: ref not needed on silk
RADIUS = {"wr-radio": 8.0, "1 SIDE ONLY": 5.0, "GND": 4.0, "TX": 4.0, "RX": 4.0}   # search radius for user labels (default 2.5)
b = pcbnew.LoadBoard(src)
if dst == BRD and not os.path.exists(BRD + ".bak_before_silk"): shutil.copy(BRD, BRD + ".bak_before_silk")
FS, ECUT = pcbnew.F_SilkS, pcbnew.Edge_Cuts
g = Grid(); eb = b.GetBoardEdgesBoundingBox(); BB = (mm(eb.GetLeft()) + 0.6, mm(eb.GetTop()) + 0.6, mm(eb.GetRight()) - 0.6, mm(eb.GetBottom()) - 0.6)
V = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox(); g.rect(mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()), 0.25)
    for sh in f.GraphicalItems():
        if sh.GetLayer() == FS and sh.GetClass() == "PCB_SHAPE": add_shape(g, sh, 0.12)
        if sh.GetLayer() == pcbnew.F_CrtYd and sh.GetClass() == "PCB_SHAPE": add_shape(g, sh, 0.15, 0.04)
for d in b.GetDrawings():
    if d.GetLayer() == ECUT and d.GetClass() == "PCB_SHAPE": add_shape(g, d, 0.5)
    if d.GetLayer() == FS and d.GetClass() == "PCB_SHAPE": add_shape(g, d, 0.12)
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA": g.seg(mm(t.GetX()), mm(t.GetY()), mm(t.GetX()), mm(t.GetY()), mm(t.GetWidth(FS)) / 2, 0.15)
    else: g.seg(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2, 0.02)

def put(t, cands, angs, maxcost=99):
    """Place text t at the cheapest collision-free candidate; cands: fn(hx,hy)->iterable of (cx,cy,cost)."""
    best = None; p0 = (t.GetPosition(), t.GetTextAngleDegrees())
    for ang in angs:
        hx, hy, ox, oy = text_ext(t, ang)
        for cx, cy, c in cands(hx, hy):
            c += 0.25 * (ang == 90) + (0 if best is None else 0)
            if best and c >= best[0]: continue
            if cx - hx < BB[0] or cy - hy < BB[1] or cx + hx > BB[2] or cy + hy > BB[3]: continue
            s = g.hit((cx - hx, cy - hy, cx + hx, cy + hy))
            if s is None: continue
            c += s
            if c < maxcost and (best is None or c < best[0]): best = (c, ang, cx - ox, cy - oy, hx, hy, ox, oy)
    if not best: t.SetPosition(p0[0]); t.SetTextAngleDegrees(p0[1]); return False
    _, ang, px, py, hx, hy, ox, oy = best
    t.SetTextAngleDegrees(ang); t.SetPosition(V(px, py))
    g.rect(px + ox - hx, py + oy - hy, px + ox + hx, py + oy + hy, 0.12)
    return True

def style(t, h=H):
    t.SetLayer(FS); t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(h), pcbnew.FromMM(h))); t.SetTextThickness(pcbnew.FromMM(TH)); t.SetKeepUpright(False)

fps = {f.GetReference(): f for f in b.GetFootprints()}
report = {"moved": [], "hidden": [], "unplaced_labels": []}
# 1. existing user labels: nearest free spot to current position, same angle
for d in list(b.GetDrawings()):
    if d.GetClass() != "PCB_TEXT" or d.GetLayer() != FS: continue
    txt = d.GetText(); big = txt.startswith("wr-radio"); style(d, max(H, mm(d.GetTextHeight())) if big else H)
    r = next((v for k, v in RADIUS.items() if txt.startswith(k)), 2.5); x0, y0 = mm(d.GetX()), mm(d.GetY())
    ang = round(d.GetTextAngleDegrees()) % 180
    def ring(hx, hy, x0=x0, y0=y0, r=r):
        n = int(r / 0.2)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1): yield x0 + i * 0.2, y0 + j * 0.2, math.hypot(i, j) * 0.2 * 0.5
    ox = text_ext(d, ang)[2:]
    if not put(d, lambda hx, hy: ((x - ox[0] + ox[0], y, c) for x, y, c in ring(hx, hy)), (ang,) if txt not in ('GND', 'TX', 'RX') else (ang, 0)): report["unplaced_labels"].append(txt)
# 2. new labels (re-run: reuse existing)
have = {d.GetText(): d for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT"}
for txt, (ref, sides, angs) in NEW.items():
    d = have.get(txt)
    if d is None: d = pcbnew.PCB_TEXT(b); d.SetText(txt); b.Add(d)
    style(d); bb = fps[ref].GetBoundingBox(False); box = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
    if not put(d, lambda hx, hy: candidates(box, hx, hy, sides, 4.0), angs): report["unplaced_labels"].append(txt); b.Remove(d)
# 3. reference designators, biggest parts first
order = sorted(fps.values(), key=lambda f: -f.GetBoundingBox(False).GetWidth() * f.GetBoundingBox(False).GetHeight())
for f in order:
    r = f.Reference(); style(r, 1.0 if False else H)
    if f.GetReference() in NOREF or f.GetReference() in ("D2", "D3"): r.SetVisible(False); report["hidden"].append(f.GetReference()); continue
    bb = f.GetBoundingBox(False); box = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
    r.SetVisible(True)
    if put(r, lambda hx, hy: candidates(box, hx, hy, "TBLR", 2.5), (0, 90)): report["moved"].append(f.GetReference())
    else: r.SetVisible(False); report["hidden"].append(f.GetReference())
pcbnew.SaveBoard(dst, b)
print("placed", len(report["moved"]), "hidden", sorted(report["hidden"]), "unplaced labels", report["unplaced_labels"])
