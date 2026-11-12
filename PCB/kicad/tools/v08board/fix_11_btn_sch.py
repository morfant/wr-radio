"""Schematic part of section 11: J10 button pads (DNP) on Pi GPIO4 (J1 pin 7).
  J1 pin 7 (GPCLK0/GPIO04): no-connect flag -> wire + label BTN.
  J10 Conn_01x02 at (396.24, 154.94), right of the J1 pin column inside the Pi box, same DNP / not-in-BOM settings as J9:
  1 = BTN, 2 = GND. Footprint Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical. No resistor (Pi pull-up).
Text edit, idempotent (J10 is only added once).  System python3:  python3 fix_11_btn_sch.py [file.kicad_sch]"""
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(
    os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_sch"))
ROOT = "/6b69aaf6-1094-5d34-9d42-29487523bd5a"
FP = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
DESC = "External button pads, no part fitted (1=BTN Pi GPIO4, 2=GND; Pi internal pull-up)"
J1_P7 = (360.68, 157.48)          # J1 pin 7 connection point (symbol at 327.66,157.48 + lib (33.02, 0))
X, Y = 396.24, 154.94             # J10 symbol; pins at (X-5.08, Y) and (X-5.08, Y+2.54)

U = lambda: str(uuid.uuid4())


def prop(name, val, x, y, hide=True, ang=0):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %g %g %d)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t\t)\n%s\t\t\t)\n\t\t)\n') % (name, val, x, y, ang, "\t\t\t\t(hide yes)\n" if hide else "")


def wire(x1, y1, x2, y2):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %g %g)\n\t\t\t(xy %g %g)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
            '\t\t)\n\t\t(uuid "%s")\n\t)\n') % (x1, y1, x2, y2, U())


def label(name, x, y, ang):
    just = "right bottom" if ang == 180 else "left bottom"
    return ('\t(label "%s"\n\t\t(at %g %g %d)\n\t\t(fields_autoplaced yes)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (name, x, y, ang, just, U())


s = open(SCH).read()
if '(property "Reference" "J10"' in s:
    print("fix_11_btn_sch: J10 already present, nothing to do")
    sys.exit(0)

# J1 pin 7: drop the no-connect flag, add a wire stub + BTN label (right column style: label at x 363.22, angle 0)
s, n = re.subn(r'\t\(no_connect\s+\(at %g %g\)\s+\(uuid "[^"]+"\)\s*\)\n' % J1_P7, "", s)
assert n == 1, "J1 pin 7 no-connect not found"
new = wire(J1_P7[0], J1_P7[1], J1_P7[0] + 2.54, J1_P7[1]) + label("BTN", J1_P7[0] + 2.54, J1_P7[1], 0)

pw = max(int(k) for k in re.findall(r'"#PWR(\d+)"', s)) + 1
new += ('\t(symbol\n\t\t(lib_id "Connector_Generic:Conn_01x02")\n\t\t(at %g %g 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n'
        '\t\t(in_bom no)\n\t\t(on_board yes)\n\t\t(dnp yes)\n\t\t(uuid "%s")\n') % (X, Y, U())
new += prop("Reference", "J10", X, Y - 2.54, False) + prop("Value", "BTN_EXT", X, Y + 6.35, False)
new += prop("Footprint", FP, X, Y) + prop("Datasheet", "", X, Y) + prop("Description", DESC, X, Y)
new += prop("LCSC", "", X, Y) + prop("MPN", "", X, Y)
for p in "12":
    new += '\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (p, U())
new += ('\t\t(instances\n\t\t\t(project "radio-hat-v08"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "J10")\n\t\t\t\t\t(unit 1)\n'
        '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n') % ROOT
px = X - 5.08
new += wire(px, Y, px - 2.54, Y) + label("BTN", px - 2.54, Y, 180)
gy = Y + 2.54
new += wire(px, gy, px - 2.54, gy)
new += ('\t(symbol\n\t\t(lib_id "power:GND")\n\t\t(at %g %g 270)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n'
        '\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n') % (px - 2.54, gy, U())
new += prop("Reference", "#PWR%03d" % pw, px - 2.54, gy) + prop("Value", "GND", px - 8.79, gy + 0.9, False, 90)
new += prop("Footprint", "", px - 2.54, gy) + prop("Datasheet", "", px - 2.54, gy)
new += prop("Description", 'Power symbol creates a global label with name \\"GND\\" , ground', px - 2.54, gy)
new += '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n' % U()
new += ('\t\t(instances\n\t\t\t(project "radio-hat-v08"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "#PWR%03d")\n\t\t\t\t\t(unit 1)\n'
        '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n') % (ROOT, pw)
new += ('\t(text "J10 button pads (DNP, no part fitted)\\n1=BTN (Pi GPIO4, J1 pin 7) 2=GND\\n'
        'Switch to GND, Pi internal pull-up. 2026-11-12"\n\t\t(exclude_from_sim no)\n\t\t(at %g %g 0)\n'
        '\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (
    370.84, 125.73, U())
k = s.rfind("\t(sheet_instances")
s = s[:k] + new + s[k:]
open(SCH, "w").write(s)
print("fix_11_btn_sch: J10 + BTN label added, #PWR%03d" % pw)
