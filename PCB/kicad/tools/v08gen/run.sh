#!/bin/sh
# regenerate footprints + schematic, then ERC + netlist check + PDF/SVG/PNG renders.
# Intermediate files (erc.rpt, net.net, expected.json, svg/, *.png) go to $V08_WORK (default: ./build).
D=$(cd "$(dirname "$0")" && pwd)
O=$(cd "$D/../../radio-hat-v08" && pwd)
W=${V08_WORK:-$D/build}; export V08_WORK="$W"; mkdir -p "$W"
K=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
python3 "$D/gen_fp.py" || exit 1
python3 "$D/gen.py" || exit 1
cd "$O"
$K sch erc -o "$W/erc.rpt" radio-hat-v08.kicad_sch 2>&1 | grep -v Fontconfig
$K sch export netlist --format kicadsexpr -o "$W/net.net" radio-hat-v08.kicad_sch 2>&1 | grep -v Fontconfig
$K sch export pdf -o radio-hat-v08.pdf radio-hat-v08.kicad_sch 2>&1 | grep -v Fontconfig
$K sch export svg -o "$W/svg" radio-hat-v08.kicad_sch 2>&1 | grep -v Fontconfig
$K sch export bom --fields 'Reference,Value,Footprint,LCSC,MPN,${QUANTITY}' --labels 'Reference,Value,Footprint,LCSC,MPN,Qty' \
    --group-by 'Value,Footprint,LCSC' --ref-range-delimiter '' -o radio-hat-v08_bom.csv radio-hat-v08.kicad_sch 2>&1 | grep -v Fontconfig
cd "$W"
grep "^\[" erc.rpt | sort | uniq -c
python3 "$D/check_netlist.py" | grep -v ^PASS
sips -s format png "$O/radio-hat-v08.pdf" --out full.png -Z 4000 >/dev/null
python3 -c "
from PIL import Image
im=Image.open('full.png'); W,H=im.size
im.resize((1600,int(1600*H/W))).save('overview.png')
for i,(x,y) in enumerate([(0,0),(1,0),(0,1),(1,1)]):
    im.crop((x*W//2,y*H//2,(x+1)*W//2,(y+1)*H//2)).save(f'q{i}.png')
"
