"""Section 2c: battery J3 -> BAT+ trunk (to Q1 / U1 / C3) and protection DW01A U2 + WSP8814 U3 on B-.
Run after route_2b_charger.py. KiCad python, GUI closed. Re-runnable (owned_2c.json). Also places U2/U3/C4/R8/R9.

BAT+ trunk (1.2-1.5 mm, F.Cu): Q1 drain/C3 -> down between U5 and the ADC divider row -> diagonal under that row
-> down left of U3 -> J3.1. It passes R14.1 (VBAT_SENSE divider top) and R8.1 (DW01A supply).
B- (1.2 mm): U3 S1 pins 2/3 -> right of U3 -> J3.2. U3 S2 pins 6/7 (system GND) -> small F.Cu zone under the
package with 4 vias to the B.Cu GND plane. FET drains 1/8 joined under the body.
Gate lines: OC straight from U3.5 to U2.3; OD from U3.4 runs under U2's body to U2.1. U2 VCC sits on the
right (with C4), R8 on the left next to the trunk, so VCC crosses with one short thin B.Cu hop.
"""
import routelib
from routelib import B

G, BAT, BM = "GND", "/BAT+", "/B-"
PLACE = {
    "U3": (50.5, -13.5, 180),     # was (50.0,-13.5) r180
    "U2": (50.5, -19.5, 0),       # was (50.0,-18.5) r0
    "C4": (53.6, -19.9, 90),      # was (53.8,-18.5) r90
    "R8": (47.2, -19.6, 270),     # was (46.5,-18.5) r90
    "R9": (49.0, -22.4, 0),       # was (50.0,-9.5) r0
}


def build(b, R):
    routelib.place(b, PLACE)
    t = R.track
    # --- BAT+ trunk -----------------------------------------------------------------------------
    t(BAT, 1.5, [(38.0, -44.4), (36.9, -43.3), (36.9, -29.6), (45.9, -27.0)])
    t(BAT, 1.2, [(45.9, -27.0), (45.9, -7.5), (47.5, -5.5), (47.5, -4.17)])
    t(BAT, 0.3, [(36.9, -31.375), (38.5, -31.375)])         # -> R14 (VBAT_SENSE divider)
    t(BAT, 0.3, [(45.9, -20.425), (47.2, -20.425)])         # -> R8 (DW01A supply)
    # --- B- : U3 S1 -> J3.2, DW01A B- and C4 -----------------------------------------------------
    t(BM, 0.4, [(53.362, -13.175), (55.0, -13.5)])
    t(BM, 0.4, [(53.362, -13.825), (55.0, -13.5)])
    t(BM, 1.2, [(55.0, -13.5), (55.0, -8.0), (50.0, -5.2), (50.0, -4.17)])
    t(BM, 0.25, [(51.638, -20.45), (53.6, -20.675)])
    t(BM, 0.25, [(53.6, -20.675), (54.9, -20.675), (54.9, -14.2), (55.0, -13.5)])
    # --- system GND side of U3 (pins 6/7) -------------------------------------------------------
    R.zone("BAT_GND_F", G, [(46.9, -14.0), (52.3, -14.0), (52.3, -13.0), (46.9, -13.0)])
    for x in (48.8, 49.8, 50.8, 51.8):
        R.via(G, x, -13.5)
    t("/FET_D", 0.4, [(47.638, -12.525), (53.362, -12.525)])
    # --- gates ------------------------------------------------------------------------------------
    t("/OC", 0.25, [(47.638, -14.475), (47.638, -15.2), (48.9, -17.6), (48.9, -18.55), (49.362, -18.55)])
    t("/OD", 0.2, [(53.0, -14.475), (52.4, -15.6), (50.5, -15.6), (50.5, -20.45), (49.362, -20.45)])
    # --- DW01A supply: R8 (left) -> B.Cu hop -> C4.1 / U2.5 (right) -------------------------------
    t("/DW_VCC", 0.25, [(51.638, -19.5), (52.6, -19.125), (53.6, -19.125), (53.6, -17.8)])
    t("/DW_VCC", 0.25, [(47.2, -18.775), (47.2, -17.8)])
    R.via("/DW_VCC", 47.2, -17.8)
    R.via("/DW_VCC", 53.6, -17.8)
    t("/DW_VCC", 0.3, [(47.2, -17.8), (53.6, -17.8)], layer=B)
    # --- CS -> R9 -> GND ---------------------------------------------------------------------------
    t("/DW_CS", 0.25, [(49.362, -19.5), (48.25, -19.5), (48.25, -22.0), (48.175, -22.4)])
    t(G, 0.4, [(49.825, -22.4), (50.9, -22.4)])
    R.via(G, 50.9, -22.4)


if __name__ == "__main__":
    routelib.run("2c", build)
