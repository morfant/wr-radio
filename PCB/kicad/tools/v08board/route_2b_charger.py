"""Section 2b: TP4056 U1 (EP vias, PROG, BAT + C3, CE network Q2/R6/R7, CHRG/STDBY -> D2/D3 via R4/R5),
load share Q1 / D1 and the SYS links (D1 cathode -> boost trunk, Q1 source -> C5 entry, SYS -> J4.1).
Run after place_2.py and route_2a_usbc.py. KiCad python, GUI closed. Re-runnable (owned_2b.json).

Status lines run down from U1's bottom row and right to the side LEDs. R4 sits between the CHRG and STDBY
lines, so its VBUS comes through a short thin B.Cu hop (V1 -> V3 -> V2) that also feeds R5 and the
VBUS_SENSE divider R16 below the status lines.
"""
import routelib
from routelib import B

G, VB, BAT, SYS = "GND", "VBUS", "/BAT+", "/SYS"


def build(b, R):
    t = R.track
    # --- U1 exposed pad: 3 x 2 vias, GND pins 1/3 into the pad ------------------------------
    for x in (43.95, 45.0, 46.05):
        for y in (-44.15, -43.05):
            R.via(G, x, y)
    t(G, 0.5, [(44.365, -45.3), (44.365, -44.5)])
    t(G, 0.5, [(46.905, -45.3), (46.4, -44.5)])
    # --- PROG -> R3 (GND end to TEMP pin 1) ---------------------------------------------------
    t("/PROG", 0.25, [(45.635, -46.6), (45.635, -47.5), (48.8, -47.5), (49.2, -47.225)])
    t(G, 0.4, [(49.2, -45.575), (46.905, -45.575)])
    # --- BAT: Q1 drain -> C3 -> U1 pin 5 -------------------------------------------------------
    t(BAT, 1.2, [(38.0, -45.4), (38.0, -44.4), (39.6, -42.8), (41.2, -41.55)])
    t(BAT, 1.0, [(41.2, -41.55), (43.095, -41.55)])
    t(G, 0.6, [(41.2, -39.65), (41.2, -38.5)])        # C3 GND
    R.via(G, 41.2, -38.5)
    # --- SYS: D1 cathode -> boost trunk / C27, Q1 source -> C5 entry, SYS -> J4.1 ---------------
    t(SYS, 1.0, [(49.0, -49.9), (47.45, -50.85)])
    t(SYS, 1.2, [(49.6, -50.4), (50.6, -52.55)])
    t(SYS, 1.0, [(49.0, -49.9), (48.45, -51.85)])
    R.zone("CHG_SYS_F", SYS, [(47.3, -52.0), (50.3, -52.0), (50.3, -49.0), (47.3, -49.0)])      # D1 cathode heat
    R.zone("CHG_VBUS_F", VB, [(51.7, -51.0), (55.0, -51.0), (55.0, -49.0), (51.7, -49.0)])      # D1 anode heat
    t(SYS, 0.8, [(37.05, -47.6), (37.05, -49.5), (43.35, -49.5), (43.35, -50.3)])
    t(SYS, 0.5, [(37.05, -49.0), (31.5, -49.0), (31.5, -34.41), (27.7, -34.41)])
    # --- CE: U1.8 -> R6 -> Q2 drain; Q2 gate -> R7, CHG_DIS exit via ----------------------------
    t("/CHG_CE", 0.25, [(46.905, -41.775), (48.55, -41.775), (49.6, -40.6), (49.6, -39.4)])
    t("/CHG_DIS", 0.25, [(48.65, -37.0), (47.3, -36.575), (46.9, -36.575), (46.9, -35.65)])
    R.via("/CHG_DIS", 46.9, -35.65)
    t(G, 0.4, [(46.9, -38.225), (46.9, -39.4)])
    R.via(G, 46.9, -39.4)
    t(G, 0.4, [(50.55, -38.0), (51.9, -39.25)])
    # --- status lines -> side LEDs, LED resistors -----------------------------------------------
    t("/STDBY_N", 0.25, [(44.365, -40.6), (44.365, -34.15), (62.63, -34.15)])
    t("/CHRG_N", 0.25, [(45.635, -40.6), (45.635, -34.9), (52.0, -34.9), (54.5, -37.4), (62.63, -37.4)])
    t("/LED_CHRG_A", 0.25, [(60.725, -36.15), (62.63, -36.15)])
    t("/LED_STDBY_A", 0.25, [(56.825, -32.6), (57.3, -32.15), (62.63, -32.15)])
    # --- LED / sense VBUS feed: F.Cu down to V1, B.Cu hop under CHRG and STDBY -------------------
    t(VB, 0.3, [(56.0, -41.6), (56.0, -38.4)])
    for x, y in ((56.0, -38.4), (56.0, -36.0), (54.2, -33.2)):
        R.via(VB, x, y)
    t(VB, 0.3, [(56.0, -38.4), (56.0, -36.0), (54.2, -33.2)], layer=B)
    t(VB, 0.3, [(56.0, -36.0), (56.3, -36.15), (59.075, -36.15)])
    t(VB, 0.3, [(54.2, -33.2), (54.8, -32.6), (55.175, -32.6)])
    t(VB, 0.3, [(54.2, -33.2), (53.0, -30.0), (43.6, -30.0), (43.6, -31.0)])   # -> R16 (VBUS_SENSE divider)


if __name__ == "__main__":
    routelib.run("2b", build)
