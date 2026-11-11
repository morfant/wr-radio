"""Section 7: board-wide GND pours (GND_B on B.Cu, GND_F on F.Cu) + GND stitching vias (KiCad python, GUI closed).
Re-runnable (owned_7.json): owns both pours, the F.Cu hole keep-outs (H1..H5) and every via it adds.
The unnamed practice B.Cu GND zone from earlier sections is deleted on the first run.

- Pours: outline = board rectangle; the filler applies the 0.3 mm copper-to-edge rule (JLC) to the fill.
  Priority 0, below the section 1/2 local zones (priority 2: BST_GND_F / BAT_GND_F keep their solid pad
  connections, BST_5V_F / CHG_SYS_F / CHG_VBUS_F get normal clearance). Clearance 0.25, min width 0.25,
  thermal relief (gap 0.3, spoke 0.35) for THT and SMD pads, islands not touching GND copper removed.
- F.Cu keep-out (no fill) r 3.25 around H1..H5 (boss Ø5.5 + 0.5); holes are NPTH, not grounded.
- Vias (0.6/0.3, GND): planned by route_7_plan.plan() from the first fill - rules in route_7_vias.py.
"""
import math
import subprocess
import sys
import pcbnew
import routelib
from routelib import F, B, MM, V
import route_7_plan

G = "GND"
EDGE = (0.0, -64.9, 63.48, 5.08)
HOLES = ("H1", "H2", "H3", "H4", "H5")
BOSS_R = 3.25


def drop_practice_zone():
    b = pcbnew.LoadBoard(routelib.PCB)
    for z in list(b.Zones()):
        if z.GetNetname() == G and not z.GetZoneName() and not z.GetIsRuleArea():
            b.Remove(z)
            b.Save(routelib.PCB)
            print("removed practice GND zone")
            return


def outline(z, pts):
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(x), MM(y))


def pour(b, R, name, layer):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer); z.SetNet(R.net(G)); z.SetZoneName(name); z.SetAssignedPriority(0)
    z.SetLocalClearance(MM(0.25)); z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.35))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    x0, y0, x1, y1 = EDGE
    outline(z, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    R._keep(z, "zone")
    return z


def boss_keepout(b, R, ref):
    p = b.FindFootprintByReference(ref).GetPosition()
    cx, cy = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True); z.SetLayer(F); z.SetZoneName("KEEPOUT_" + ref)
    z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    outline(z, [(cx + BOSS_R * math.cos(a * math.pi / 24), cy + BOSS_R * math.sin(a * math.pi / 24))
                for a in range(48)])
    R._keep(z, "zone")


def solid_pads(b):
    """USB-C GND pads (A1/B12, A12/B1) sit in the fine-pitch row: only one thermal spoke fits (starved_thermal),
    so they connect solid to GND_F (pad override)."""
    for pd in b.FindFootprintByReference("J2").Pads():
        if pd.GetNetname() == G and pd.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            pd.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)


def build(b, R):
    solid_pads(b)
    pour(b, R, "GND_B", B)
    pour(b, R, "GND_F", F)
    for h in HOLES:
        boss_keepout(b, R, h)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    vias = route_7_plan.plan(b)
    for x, y, kind in vias:
        R.via(G, x, y)
    route_7_plan.report(vias)


if __name__ == "__main__":
    if "--drop" in sys.argv:            # own process: KiCad SWIG breaks on LoadBoard after Remove
        drop_practice_zone()
    else:
        if "--add" not in sys.argv:
            subprocess.run([sys.executable, sys.argv[0], "--drop"], check=True)
        routelib.run("7", build)
