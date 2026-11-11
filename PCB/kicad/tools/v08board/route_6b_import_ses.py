"""Section 6b: add the Freerouting result (Specctra .ses) to the board as locked copper (KiCad python, GUI closed).
usage: route_6b_import_ses.py            (reads route_6_freerouting.ses next to this script, or $WR_SES)
Only wires/vias of route_6_prep_dsn.KEEP_NETS are taken (the .ses holds only Freerouting's new copper; the
fixed copper is not written back). pcbnew.ImportSpecctraSES is NOT used: it rewrites every track on the board.
SES units: (resolution um 10) -> 0.1 um, y up -> board y = -v."""
import os
import re
import routelib
from route_6_prep_dsn import KEEP_NETS, block_end

SES = os.environ.get("WR_SES") or os.path.join(routelib.HERE, "route_6_freerouting.ses")
LAYER = {"F.Cu": routelib.F, "B.Cu": routelib.B}


def parse(path):
    s = open(path).read()
    out = []                                  # (net, "wire", layer, w_mm, pts) | (net, "via", x, y, d, drill)
    for m in re.finditer(r'\(net ("[^"]*"|\S+)\s*\n', s):
        net = m.group(1).strip('"')
        body = s[m.start():block_end(s, m.start())]
        if net not in KEEP_NETS:
            raise SystemExit("unexpected net in .ses: %s" % net)
        for w in re.finditer(r"\(path (\S+) (\d+)\s+([-\d\s]+)\)", body):
            v = [int(t) for t in w.group(3).split()]
            pts = [(v[i] / 1e4, -v[i + 1] / 1e4) for i in range(0, len(v), 2)]
            out.append((net, "wire", w.group(1), int(w.group(2)) / 1e4, pts))
        for v in re.finditer(r'\(via "Via\[0-1\]_(\d+):(\d+)_um" (-?\d+) (-?\d+)', body):
            out.append((net, "via", int(v.group(3)) / 1e4, -int(v.group(4)) / 1e4,
                        int(v.group(1)) / 1e3, int(v.group(2)) / 1e3))
    return out


def build(b, R):
    for it in parse(SES):
        if it[1] == "wire":
            net, _, layer, w, pts = it
            pts = [(round(x, 4), round(y, 4)) for x, y in pts]
            pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]   # Freerouting writes 0-length stubs
            if len(pts) > 1:
                R.track(net, w, pts, LAYER[layer])
        else:
            net, _, x, y, d, drill = it
            R.via(net, x, y, d, drill)


if __name__ == "__main__":
    routelib.run("6b", build)
