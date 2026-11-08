"""Schematic <-> board consistency check (2026-11-08 A3). Exports the schematic netlist with kicad-cli,
then compares every symbol's footprint with the board footprint and every pad's net with the netlist.
Run with KiCad's python:  .../python3 chk_A3.py"""
import os, subprocess, tempfile, xml.etree.ElementTree as ET
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08"))
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
xmlf = os.path.join(tempfile.mkdtemp(), "net.xml")
subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", xmlf,
                os.path.join(D, "radio-hat-v08.kicad_sch")], check=True, capture_output=True)
root = ET.parse(xmlf).getroot()
sch_fp = {c.get("ref"): c.findtext("footprint") for c in root.iter("comp")}
sch_pin = {}
for n in root.iter("net"):
    name = n.get("name")
    for nd in n.iter("node"):
        sch_pin[(nd.get("ref"), nd.get("pin"))] = name
b = pcbnew.LoadBoard(os.path.join(D, "radio-hat-v08.kicad_pcb"))
brd = {f.GetReference(): f for f in b.GetFootprints()}
bad = []
for r, fp in sch_fp.items():
    if r not in brd: bad.append("missing on board: %s" % r); continue
    f = brd[r]
    bfp = "%s:%s" % (f.GetFPID().GetLibNickname(), f.GetFPID().GetLibItemName())
    if bfp != fp: bad.append("footprint %s sch=%s brd=%s" % (r, fp, bfp))
for r in brd:
    if r not in sch_fp and not r.startswith("H"): bad.append("extra on board: %s" % r)
npins = 0
for r, f in brd.items():
    if r not in sch_fp: continue
    for p in f.Pads():
        num = p.GetNumber()
        if not num: continue
        npins += 1
        want = sch_pin.get((r, num))
        got = p.GetNetname()
        if want is None:
            if got and not got.startswith("unconnected-"):
                bad.append("pad %s.%s brd=%s sch=<none>" % (r, num, got))
        elif want.startswith("unconnected-"):
            if got and not got.startswith("unconnected-"):
                bad.append("pad %s.%s brd=%s sch=%s" % (r, num, got, want))
        elif got != want:
            bad.append("pad %s.%s brd=%s sch=%s" % (r, num, got, want))
# every schematic pin must exist as a pad
padset = {(r, p.GetNumber()) for r, f in brd.items() for p in f.Pads()}
for k in sch_pin:
    if k not in padset: bad.append("sch pin without pad %s.%s" % k)
j9 = brd.get("J9")
print("symbols", len(sch_fp), "pads checked", npins, "mismatches", len(bad))
for x in bad: print("  ", x)
if j9:
    print("J9 DNP", j9.IsDNP(), "excl BOM", bool(j9.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM),
          "excl pos", bool(j9.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES),
          [(p.GetNumber(), p.GetNetname()) for p in j9.Pads()])
