#!/bin/zsh
# Section 6 (signal nets) - full reproducible sequence. KiCad GUI must be closed.
#   1. route_6a_hand.py      BST_EN, VBAT/VBUS_SENSE, UART (hand-routed, locked)
#   2. export DSN from the board, route_6_prep_dsn.py (only section-6 nets, B.Cu windows, keepouts)
#   3. Freerouting 2.5.0 with route_6_freerouting.rules (via cost 40, F.Cu 1.0, B.Cu 5.0)
#   4. route_6b_import_ses.py  adds route_6_freerouting.ses as locked copper
# usage: route_6_freerouting.sh [--reroute]   (without --reroute the committed .ses is used as is)
set -e
cd "$(dirname "$0")"
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
pgrep -lf "MacOS/(kicad|pcbnew)" && { echo "close KiCad first"; exit 1; }
$KP route_6a_hand.py          # re-runnable: removes its own items first
if [[ "$1" == "--reroute" ]]; then
  T=$(mktemp -d)
  $KP -c "import pcbnew,routelib; pcbnew.ExportSpecctraDSN(pcbnew.LoadBoard(routelib.PCB), '$T/raw.dsn')"
  python3 route_6_prep_dsn.py $T/raw.dsn $T/route_6.dsn
  $(brew --prefix openjdk)/bin/java -jar ~/Applications/freerouting/freerouting-2.5.0.jar \
    -de $T/route_6.dsn -dr route_6_freerouting.rules -do route_6_freerouting.ses \
    --router.autorouter.max_passes=150 --router.fanout.enabled=false --router.optimizer.enabled=true \
    --gui.enabled=false
fi
$KP route_6b_import_ses.py
$KP routelib.py drc
