"""Dump board copper/courtyards in a region to JSON for plot_region.py (run with KiCad's python).
usage: dump_region.py out.json x0 y0 x1 y1"""
import sys, os, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.environ.get("WR_PCB") or os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_pcb"))
out = sys.argv[1]; x0, y0, x1, y1 = map(float, sys.argv[2:6])
M = pcbnew.ToMM
b = pcbnew.LoadBoard(PCB)
def inside(x, y, m=3): return x0 - m < x < x1 + m and y0 - m < y < y1 + m
def poly(sps):
    res = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i)
        res.append([(M(o.CPoint(k).x), M(o.CPoint(k).y)) for k in range(o.PointCount())])
    return res
D = {"region": [x0, y0, x1, y1], "pads": [], "tracks": [], "vias": [], "fps": [], "zones": [], "edge": []}
for fp in b.GetFootprints():
    p = fp.GetPosition()
    if not inside(M(p.x), M(p.y), 6): continue
    cy = fp.GetCourtyard(pcbnew.F_Cu)
    D["fps"].append({"ref": fp.GetReference(), "x": M(p.x), "y": M(p.y), "crtyd": poly(cy) if cy.OutlineCount() else []})
    for pd in fp.Pads():
        q = pd.GetPosition()
        for lay, nm in ((pcbnew.F_Cu, "F"), (pcbnew.B_Cu, "B")):
            if not pd.IsOnLayer(lay): continue
            sps = pd.GetEffectivePolygon(lay, pcbnew.ERROR_INSIDE) if hasattr(pd, "GetEffectivePolygon") else None
            D["pads"].append({"ref": fp.GetReference(), "num": pd.GetNumber(), "net": pd.GetNetname(), "layer": nm,
                              "x": M(q.x), "y": M(q.y), "poly": poly(sps), "th": pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH})
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        if inside(M(p.x), M(p.y)):
            D["vias"].append({"x": M(p.x), "y": M(p.y), "d": M(t.GetWidth(pcbnew.F_Cu)), "drill": M(t.GetDrillValue()), "net": t.GetNetname()})
    else:
        s, e = t.GetStart(), t.GetEnd()
        if inside(M(s.x), M(s.y)) or inside(M(e.x), M(e.y)):
            D["tracks"].append({"x1": M(s.x), "y1": M(s.y), "x2": M(e.x), "y2": M(e.y), "w": M(t.GetWidth()),
                                "layer": "F" if t.GetLayer() == pcbnew.F_Cu else "B", "net": t.GetNetname()})
for z in b.Zones():
    for lay, nm in ((pcbnew.F_Cu, "F"), (pcbnew.B_Cu, "B")):
        if z.IsOnLayer(lay) and z.HasFilledPolysForLayer(lay):
            fill = z.GetFilledPolysList(lay)
            D["zones"].append({"name": z.GetZoneName(), "net": z.GetNetname(), "layer": nm, "polys": poly(fill)})
json.dump(D, open(out, "w"))
print("dumped", out, {k: len(v) for k, v in D.items() if isinstance(v, list)})
