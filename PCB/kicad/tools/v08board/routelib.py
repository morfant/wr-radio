"""Shared helpers for the section-2+ routing scripts (run with KiCad's python, GUI closed).

Each step script defines build(b, R) that places parts / adds copper through the R helper, and calls
routelib.run("<step>", build). Re-runnable: the items a step added last time are tracked by UUID in
owned_<step>.json and removed first; the add phase then runs in a fresh process
(KiCad 10 SWIG loses item types after BOARD.Remove()).

  python3 routelib.py drc [NET ...]   -> DRC summary (copper errors, unconnected count, unconnected on NETs)
"""
import json
import os
import subprocess
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.environ.get("WR_PCB") or os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_pcb"))
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
MM = pcbnew.FromMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
COPPER = {"clearance", "shorting_items", "tracks_crossing", "track_width", "hole_clearance", "hole_to_hole",
          "annular_width", "drill_out_of_range", "via_diameter", "copper_edge_clearance", "courtyards_overlap",
          "items_not_allowed", "solder_mask_bridge", "starved_thermal", "malformed_courtyard", "pth_inside_courtyard",
          "npth_inside_courtyard", "isolated_copper", "padstack", "text_height"}


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


class Adder:
    """Adds locked copper and remembers UUIDs."""
    def __init__(self, b):
        self.b, self.ids, self.n = b, [], {"track": 0, "via": 0, "zone": 0}

    def net(self, name):
        n = self.b.FindNet(name)
        assert n is not None, name
        return n

    def _keep(self, it, kind):
        it.SetLocked(True)
        self.b.Add(it)
        self.ids.append(it.m_Uuid.AsString())
        self.n[kind] += 1

    def track(self, net, w, pts, layer=F):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2)); t.SetWidth(MM(w)); t.SetLayer(layer)
            t.SetNet(self.net(net)); self._keep(t, "track")

    def via(self, net, x, y, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(V(x, y)); v.SetLayerPair(F, B)
        v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(self.net(net)); self._keep(v, "via")

    def zone(self, name, net, poly, layer=F, prio=2, clearance=0.2):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(layer); z.SetNet(self.net(net)); z.SetZoneName(name); z.SetAssignedPriority(prio)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(0.2)); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline(); ol.NewOutline()
        for x, y in poly:
            ol.Append(MM(x), MM(y))
        self._keep(z, "zone")


def place(b, table, ref_text=None):
    """table: {ref: (x, y, deg)} absolute; ref_text: {ref: (x, y)} reference text position."""
    for ref, (x, y, r) in table.items():
        fp = b.FindFootprintByReference(ref)
        fp.SetOrientationDegrees(r); fp.SetPosition(V(x, y))
    for ref, (x, y) in (ref_text or {}).items():
        rf = b.FindFootprintByReference(ref).Reference()
        rf.SetPosition(V(x, y)); rf.SetTextAngleDegrees(0)


def _owned(step):
    return os.path.join(HERE, "owned_%s.json" % step)


def run(step, build):
    if "--add" not in sys.argv:
        b = pcbnew.LoadBoard(PCB)
        old = set(json.load(open(_owned(step)))) if os.path.exists(_owned(step)) else set()
        gone = 0
        for it in list(b.GetTracks()) + list(b.Zones()):
            if it.m_Uuid.AsString() in old:
                b.Remove(it); gone += 1
        print("%s: removed %d own items" % (step, gone))
        b.Save(PCB)
        subprocess.run([sys.executable, os.path.abspath(sys.argv[0]), "--add"], check=True)
        return
    b = pcbnew.LoadBoard(PCB)
    R = Adder(b)
    build(b, R)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    json.dump(R.ids, open(_owned(step), "w"))
    print("%s: added %s" % (step, R.n))


def drc(nets=()):
    import collections
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "drc.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--schematic-parity", "-o", out, PCB],
                   capture_output=True)
    d = json.load(open(out))
    cnt = collections.Counter(v["type"] for v in d["violations"])
    print("violations:", dict(cnt))
    for v in d["violations"]:
        if v["type"] in COPPER:
            print("  ", v["type"], "|", " / ".join(i["description"][:70] for i in v["items"]))
    print("unconnected:", len(d["unconnected_items"]), " parity:", len(d.get("schematic_parity", [])))
    for v in d["unconnected_items"]:
        desc = " / ".join(i["description"] for i in v["items"])
        if any("[%s]" % n in desc for n in nets):
            print("   unconn:", desc[:150])


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "drc":
    drc(sys.argv[2:])
