"""Plot a dump_region.py JSON with matplotlib (system python3).
usage: plot_region.py in.json out.png [title] [notes.json]   notes: [[x, y, text, tx, ty], ...] arrows in board mm"""
import sys, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
D = json.load(open(sys.argv[1])); x0, y0, x1, y1 = D["region"]
fig, ax = plt.subplots(figsize=(14, 14 * (y1 - y0) / (x1 - x0)), dpi=150)
ax.set_facecolor("#101010")
for z in D["zones"]:
    c = "#2a4f9a" if z["layer"] == "B" else "#8a2a2a"
    for p in z["polys"]:
        ax.add_patch(Polygon(p, closed=True, fc=c, ec="none", alpha=0.35 if z["layer"] == "B" else 0.55, zorder=1))
for t in D["tracks"]:
    c = "#3f7fff" if t["layer"] == "B" else "#e03030"
    ptmm = fig.get_size_inches()[0] * 72 / (x1 - x0) * 0.93
    ax.plot([t["x1"], t["x2"]], [t["y1"], t["y2"]], color=c, lw=t["w"] * ptmm,
            solid_capstyle="round", alpha=0.85 if t["layer"] == "F" else 0.7, zorder=3 if t["layer"] == "F" else 2)
for p in D["pads"]:
    c = "#d8b030" if p["layer"] == "F" else "#5060c0"
    if p["layer"] == "B" and not p["th"]: continue
    for poly in p["poly"]:
        ax.add_patch(Polygon(poly, closed=True, fc=c, ec="k", lw=0.3, alpha=0.9, zorder=4))
for v in D["vias"]:
    ax.add_patch(Circle((v["x"], v["y"]), v["d"] / 2, fc="#c0c0c0", ec="k", lw=0.3, zorder=6))
    ax.add_patch(Circle((v["x"], v["y"]), v["drill"] / 2, fc="#101010", zorder=7))
for f in D["fps"]:
    for poly in f["crtyd"]:
        ax.add_patch(Polygon(poly, closed=True, fill=False, ec="#a0a0a0", lw=0.5, ls="--", zorder=5))
seen = set()
for p in D["pads"]:
    if p["layer"] != "F" and not p["th"]: continue
    if not (x0 < p["x"] < x1 and y0 < p["y"] < y1): continue
    k = (p["ref"], p["num"])
    if k in seen: continue
    seen.add(k)
    net = p["net"].lstrip("/")
    ax.text(p["x"], p["y"], "%s\n%s" % (p["num"], net[:8]), color="k", fontsize=5.5, ha="center", va="center", zorder=9)
for f in D["fps"]:
    if x0 < f["x"] < x1 and y0 < f["y"] < y1:
        ys = [pt[1] for poly in f["crtyd"] for pt in poly] or [f["y"]]
        ax.text(f["x"], min(ys) - 0.15, f["ref"], color="white", fontsize=8, ha="center", va="bottom", weight="bold", zorder=10)
if len(sys.argv) > 4:
    for x, y, txt, tx, ty in json.load(open(sys.argv[4])):
        ax.annotate(txt, (x, y), (tx, ty), color="#ffe060", fontsize=9, weight="bold", zorder=12,
                    arrowprops=dict(arrowstyle="->", color="#ffe060", lw=1.5),
                    bbox=dict(fc="#000000", ec="#ffe060", alpha=0.7, boxstyle="round,pad=0.2"))
for z in D["zones"]:
    if z["name"] and z["polys"]:
        xs = [p[0] for p in z["polys"][0]]; ys = [p[1] for p in z["polys"][0]]
        if not (x0 < sum(xs) / len(xs) < x1 and y0 < min(ys) + 0.45 < y1): continue
        ax.text(sum(xs) / len(xs), min(ys) + 0.45, z["name"], color="#ffb0b0", fontsize=7, ha="center", zorder=11)
ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal")
ax.grid(True, color="#303030", lw=0.4)
ax.set_title(sys.argv[3] if len(sys.argv) > 3 else "", color="k")
ax.tick_params(labelsize=7)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], color="#e03030", lw=4, label="F.Cu track"), Line2D([], [], color="#3f7fff", lw=4, label="B.Cu track"),
                   Line2D([], [], color="#8a2a2a", lw=8, alpha=.6, label="F.Cu zone"), Line2D([], [], color="#2a4f9a", lw=8, alpha=.4, label="B.Cu GND zone"),
                   Line2D([], [], marker="o", color="#c0c0c0", ls="", label="via"), Line2D([], [], color="#a0a0a0", ls="--", label="courtyard")],
          loc="upper right", fontsize=7, framealpha=0.8)
fig.tight_layout(); fig.savefig(sys.argv[2]); print("saved", sys.argv[2])
