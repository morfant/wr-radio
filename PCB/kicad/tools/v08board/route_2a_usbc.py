"""Section 2a: USB-C J2 -> VBUS network (TVS D4, CC resistors R1/R2, R24/R10 pull-downs, C1, U1 VCC + C2, R6, Q1 gate).
Run place_2.py first. KiCad python, GUI closed. Re-runnable (removes its own items via owned_2a.json).

VBUS pins A9/B4 feed D1's anode pad directly (load path); from that pad a 0.8 mm band runs left above U1 to
U1 VCC (pin 4), C2 and Q1 gate. Pins A4/B9 feed D4, C1, R6, R24/R10 and the LED feed. The two pin groups are
joined by a short B.Cu hop (vias right beside the pins); CC1/CC2 stay on F.Cu inside that loop and their
resistors' GND goes down through one via. GND pins A1/B12, A12/B1 tie to the shell legs (THT, B.Cu plane).
"""
import routelib
from routelib import B

VB, G = "VBUS", "GND"


def build(b, R):
    t = R.track
    # --- VBUS pins A9/B4 -> D1 anode, and B.Cu hop to A4/B9 -----------------------------------
    t(VB, 0.6, [(56.735, -50.25), (55.3, -50.25)])
    t(VB, 1.0, [(55.3, -50.25), (53.6, -50.25)])
    R.via(VB, 55.4, -50.25)
    R.via(VB, 55.4, -45.35)
    t(VB, 0.6, [(55.4, -50.25), (55.4, -45.35)], layer=B)
    # --- VBUS pins A4/B9 -> D4 / C1 / R6 ------------------------------------------------------
    t(VB, 0.6, [(56.735, -45.35), (55.4, -45.35), (55.4, -44.3), (55.2, -44.3)])
    t(VB, 1.0, [(55.2, -44.3), (50.75, -44.3), (50.75, -43.15)])
    t(VB, 0.4, [(50.75, -44.3), (49.4, -44.3), (48.55, -43.45)])
    # --- band: D1 anode -> above U1 -> VCC, C2, Q1 gate --------------------------------------
    t(VB, 0.8, [(52.6, -49.4), (51.65, -48.35), (38.95, -48.35), (38.95, -47.6)])
    t(VB, 0.8, [(40.76, -48.35), (40.76, -46.95)])
    t(VB, 0.6, [(43.095, -48.35), (43.095, -46.5)])
    # --- R24 / R10 (VBUS pull-downs) under J2 -------------------------------------------------
    t(VB, 0.3, [(55.4, -44.3), (56.0, -43.7), (56.0, -41.6), (56.6, -41.125), (58.85, -41.125)])
    t(G, 0.3, [(57.3, -39.475), (58.85, -39.475)])
    t(G, 0.3, [(58.1, -39.475), (58.1, -38.45)])
    R.via(G, 58.1, -38.45)
    # --- CC lines (0.2 mm between the fine pins) ---------------------------------------------
    t("/CC1", 0.2, [(56.735, -46.55), (55.6, -46.55), (54.425, -45.575)])
    t("/CC2", 0.2, [(56.735, -49.55), (55.65, -49.55), (55.65, -47.6), (55.2, -47.115), (54.425, -47.115)])
    t(G, 0.4, [(52.775, -47.115), (52.775, -45.575)])
    t(G, 0.4, [(52.775, -46.3), (51.6, -46.3)])
    R.via(G, 51.6, -46.3)
    # --- GND: J2 pins to shell legs, D4 / C1 / C2 / R6 area ----------------------------------
    t(G, 0.5, [(57.0, -44.55), (57.5, -43.5)])
    t(G, 0.5, [(57.0, -51.05), (57.5, -52.1)])
    t(G, 0.8, [(53.6, -39.25), (51.9, -39.25)])
    t(G, 0.6, [(50.75, -41.25), (51.9, -40.4), (51.9, -39.25)])
    R.via(G, 51.9, -39.25)
    R.via(G, 51.9, -40.4)
    t(G, 0.6, [(53.6, -39.25), (55.05, -39.25)])
    R.via(G, 55.05, -39.25)
    t(G, 0.6, [(40.76, -45.05), (40.76, -44.1)])     # C2 GND
    R.via(G, 40.76, -44.1)


if __name__ == "__main__":
    routelib.run("2a", build)
