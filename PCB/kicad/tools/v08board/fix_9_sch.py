"""Schematic part of fix_9 (review M1): D2/D3 on the same XINGLIGHT XL-1606 family, local footprint.
  D3: MHS190UGCT (C409794, pin 1 = anode) -> XL-1606UGC (C965863, pin 1 = cathode like D2 XL-1606SURC).
  D2/D3 Footprint -> radio-hat-v08:LED_XINGLIGHT_XL-1606_Horizontal.
Text edit of the symbol properties (re-runnable).  usage: python3 fix_9_sch.py [file.kicad_sch]"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "radio-hat-v08", "radio-hat-v08.kicad_sch")
FP = "radio-hat-v08:LED_XINGLIGHT_XL-1606_Horizontal"
NEW = {"D2": {"Footprint": FP},
       "D3": {"Footprint": FP, "LCSC": "C965863", "MPN": "XL-1606UGC"}}

s = open(SCH).read()
for ref, props in NEW.items():
    i = s.index('(property "Reference" "%s"' % ref)
    start = s.rindex("\n\t(symbol\n", 0, i)          # placed symbol block
    end = s.index("\n\t)\n", i)
    blk = s[start:end]
    for k, v in props.items():
        blk, n = re.subn(r'\(property "%s" "[^"]*"' % k, '(property "%s" "%s"' % (k, v), blk, count=1)
        assert n == 1, (ref, k)
    s = s[:start] + blk + s[end:]
open(SCH, "w").write(s)
print("fix_9_sch: D2/D3 updated in", SCH)
