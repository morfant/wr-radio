#!/bin/sh
# Regenerate JLC gerbers + drills into radio-hat-v08/jlc/ (read-only on the board). BOM/CPL in jlc/ are edited by hand (see jlc/README.md).
set -e
K=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
cd "$(dirname "$0")/../../radio-hat-v08"
G=jlc/gerbers; rm -rf $G; mkdir -p $G
$K pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts --no-x2 --no-netlist --check-zones -o $G radio-hat-v08.kicad_pcb 2>&1 | grep -v Fontconfig
$K pcb export drill --format excellon --excellon-units mm --excellon-separate-th --generate-map --map-format gerberx2 -o $G/ radio-hat-v08.kicad_pcb 2>&1 | grep -v Fontconfig
rm -f jlc/radio-hat-v08_gerbers.zip
(cd $G && zip -q ../radio-hat-v08_gerbers.zip *.gtl *.gbl *.gtp *.gbp *.gto *.gbo *.gts *.gbs *.gm1 *.drl)
unzip -l jlc/radio-hat-v08_gerbers.zip | tail -1
