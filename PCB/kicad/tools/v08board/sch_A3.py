"""A3 case changes to the schematic (2026-11-08). Edits radio-hat-v08.kicad_sch in place:
symbol Value/Footprint/LCSC/MPN updates + new J9 UART debug pads (J1 pin 8/10 no-connects
replaced by UART_TX/UART_RX labels). Idempotent: run from the .bak_before_A3 copy or the
current file (J9 is only added once).  System python3:  python3 sch_A3.py"""
import os, re, uuid
HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_sch"))
ROOT = "/6b69aaf6-1094-5d34-9d42-29487523bd5a"
HDR = "Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Horizontal"
SIDE_LED = "LED_SMD:LED_Kingbright_APA1606_1.6x0.6mm_Horizontal"
UPD = {  # ref: {property: value}
    "D2": {"Value": "RED", "Footprint": SIDE_LED, "LCSC": "C965860", "MPN": "XL-1606SURC"},
    "D3": {"Value": "GREEN", "Footprint": SIDE_LED, "LCSC": "C409794", "MPN": "MHS190UGCT"},
    "J3": {"Footprint": "Connector_JST:JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal", "LCSC": "C157931", "MPN": "S2B-XH-A(LF)(SN)"},
    "J4": {"Footprint": HDR % 3, "LCSC": "C492411", "MPN": "PZ254R-11-03P"},
    "J5": {"Footprint": HDR % 8, "LCSC": "C492416", "MPN": "PZ254R-11-08P"},
    "J6": {"Footprint": HDR % 5, "LCSC": "C492413", "MPN": "PZ254R-11-05P"},
    "J7": {"Footprint": HDR % 2, "LCSC": "C492410", "MPN": "PZ254R-11-02P"},
    "U1": {"Footprint": "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm"},
}
s = open(SCH).read()

def sym_span(ref):
    i = s.find('(property "Reference" "%s"' % ref)
    assert i > 0, ref
    j = s.rfind("\t(symbol\n", 0, i)
    # matching paren
    depth = 0
    for k in range(j + 1, len(s)):
        c = s[k]
        if c == "(": depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0: return j + 1, k + 1
    raise RuntimeError

for ref, props in UPD.items():
    a, b = sym_span(ref)
    blk = s[a:b]
    for p, v in props.items():
        blk, n = re.subn(r'(\(property "%s" )"[^"]*"' % p, lambda m: m.group(1) + '"%s"' % v, blk, count=1)
        assert n == 1, (ref, p)
    s = s[:a] + blk + s[b:]

U = lambda: str(uuid.uuid4())
def prop(name, val, x, y, hide=True, ang=0):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %g %g %d)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t\t)\n%s\t\t\t)\n\t\t)\n') % (name, val, x, y, ang, "\t\t\t\t(hide yes)\n" if hide else "")
def wire(x1, y1, x2, y2):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %g %g)\n\t\t\t(xy %g %g)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n'
            '\t\t)\n\t\t(uuid "%s")\n\t)\n') % (x1, y1, x2, y2, U())
def label(name, x, y):
    return ('\t(label "%s"\n\t\t(at %g %g 180)\n\t\t(fields_autoplaced yes)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t)\n\t\t\t(justify right bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (name, x, y, U())

new = ""
if '(property "Reference" "J9"' not in s:
    # J1 pins 8 (GPIO14/TXD) and 10 (GPIO15/RXD): drop the no-connect flags, add labels
    for y, net in ((142.24, "UART_TX"), (144.78, "UART_RX")):
        s, n = re.subn(r'\t\(no_connect\s+\(at 294\.64 %s\)\s+\(uuid "[^"]+"\)\s*\)\n' % re.escape("%g" % y), "", s)
        assert n == 1, y
        new += wire(294.64, y, 292.1, y) + label(net, 292.1, y)
    pw = max(int(n) for n in re.findall(r'"#PWR(\d+)"', s)) + 1
    X, Y = 340.36, 111.76          # J9 symbol; pins at x-5.08, y-2.54 / y / y+2.54
    new += ('\t(symbol\n\t\t(lib_id "Connector_Generic:Conn_01x03")\n\t\t(at %g %g 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n'
            '\t\t(in_bom no)\n\t\t(on_board yes)\n\t\t(dnp yes)\n\t\t(uuid "%s")\n') % (X, Y, U())
    new += prop("Reference", "J9", X, Y - 5.08, False) + prop("Value", "UART_DBG", X, Y + 5.08, False)
    new += prop("Footprint", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", X, Y)
    new += prop("Datasheet", "", X, Y) + prop("Description", "Serial debug pads, no part fitted (1=GND 2=Pi TXD GPIO14 3=Pi RXD GPIO15)", X, Y)
    new += prop("LCSC", "", X, Y) + prop("MPN", "", X, Y)
    for p in "123":
        new += '\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (p, U())
    new += ('\t\t(instances\n\t\t\t(project "radio-hat-v08"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "J9")\n\t\t\t\t\t(unit 1)\n'
            '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n') % ROOT
    px = X - 5.08
    new += wire(px, Y - 2.54, px - 2.54, Y - 2.54)
    new += ('\t(symbol\n\t\t(lib_id "power:GND")\n\t\t(at %g %g 270)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n'
            '\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n') % (px - 2.54, Y - 2.54, U())
    new += prop("Reference", "#PWR%03d" % pw, px - 2.54, Y - 2.54) + prop("Value", "GND", px - 8.79, Y - 3.44, False, 90)
    new += prop("Footprint", "", px - 2.54, Y - 2.54) + prop("Datasheet", "", px - 2.54, Y - 2.54)
    new += prop("Description", 'Power symbol creates a global label with name \\"GND\\" , ground', px - 2.54, Y - 2.54)
    new += '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n' % U()
    new += ('\t\t(instances\n\t\t\t(project "radio-hat-v08"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "#PWR%03d")\n\t\t\t\t\t(unit 1)\n'
            '\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n') % (ROOT, pw)
    new += wire(px, Y, px - 2.54, Y) + label("UART_TX", px - 2.54, Y)
    new += wire(px, Y + 2.54, px - 2.54, Y + 2.54) + label("UART_RX", px - 2.54, Y + 2.54)
    new += ('\t(text "J9 UART debug pads (no part fitted, DNP): 1=GND 2=UART_TX (Pi GPIO14 TXD) 3=UART_RX (Pi GPIO15 RXD)\\n'
            'Net names from the Pi side. 3.3 V logic. 2026-11-08 A3"\n\t\t(exclude_from_sim no)\n\t\t(at %g %g 0)\n\t\t(effects\n'
            '\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n') % (X - 22, Y - 9, U())
    k = s.rfind("\t(sheet_instances")
    s = s[:k] + new + s[k:]
open(SCH, "w").write(s)
print("ok")
