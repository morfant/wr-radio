"""Section 3: power distribution to/from the Pi header J1 (+5V trunk, +5V branch, +3V3, J1 GND vias).
KiCad python, GUI closed. Re-runnable (removes its own items via owned_3.json). All items locked.

+5V trunk (F.Cu 1.5): C8.1 -> x 29.3 down -> band y -54.04 between the J8 pad row (bottom -55.3) and the
  C19/R19/R20/C20 row (top -52.775) -> over J1.1 (y -55.45, clear of the H3 boss r 3.25) -> J1.2 -> J1.4.
  NOTE: the jack lines J8.5/J8.2/J8.4 -> C19,R19 / R20,C20 / R23 and C25 (HP_DET) cross this band;
  J8 pads are THT, so section 4 leaves the jack pads on B.Cu (one via at the R/C end each).
+5V branch (F.Cu 0.8): from (29.3,-54.04) down right of C15 -> diagonal -> x 26.2 (between the U6 cap column
  and J4) -> east through the J4.1/J6.5 gap (y -32.55) -> x 30.5 south (right of J6) -> JP1.1 tap (y -18.7),
  J5.8 (LCD). Section 5 feeds C21/C22/U7 VDD from the branch corner (30.5,-17.6).
+3V3: J1.1 -> C12.1 (AVDD cap, 0.4). J1.17 -> 45 deg through the plug zone (0.5) -> J6.1, then x 29.2 north
  -> via -> B.Cu 0.4 hop (under the +5V branch, SYS and the BST_EN lane) -> via west of C11 -> C11.1 -> U5.8.
  U5 SDA/SCL keep the lane between SYS (x 31.5) and the U5 pins free (SDA: pin 9 up to y -36.25, then west).
GND: a 0.6/0.3 via beside each J1 GND pin (even column: x 2.35, odd column: x 8.1), F.Cu stub 0.5.
"""
import routelib
from routelib import B

P5, P3, G = "+5V", "+3V3", "GND"
J1_GND_EVEN = {6: -48.425, 14: -38.265, 20: -30.645, 30: -17.945, 34: -12.865}   # x 3.95
J1_GND_ODD = {9: -43.345, 25: -23.025, 39: -5.245}                                 # x 6.49


def build(b, R):
    t = R.track
    # --- +5V trunk: C8.1 -> J1.2 / J1.4 --------------------------------------------------------
    t(P5, 1.5, [(31.8, -60.8), (29.3, -60.8), (29.3, -54.04), (10.0, -54.04), (8.6, -55.45),
                (3.95, -55.45), (3.95, -53.505), (3.95, -50.965)])
    # --- +5V branch toward the amp / LCD -------------------------------------------------------
    t(P5, 0.8, [(29.3, -54.04), (29.3, -46.0), (26.2, -42.9), (26.2, -32.55), (30.5, -32.55),
                (30.5, -24.0), (30.5, -17.6), (27.7, -16.81)])
    # (the C22.1 stub y -24 was removed in section 5: U7's VDD pins face south, C21/C22 moved there)
    t(P5, 0.5, [(30.5, -18.7), (32.3, -18.7)])            # JP1.1 (gain jumper A = +5V)
    # --- +3V3: J1.1 -> C12 (AVDD cap) ----------------------------------------------------------
    t(P3, 0.4, [(6.49, -53.505), (7.6, -53.505), (8.6, -52.5), (12.0, -52.5), (12.0, -48.225),
                (14.4, -48.225)])
    # --- +3V3: J1.17 -> J6.1 -> hop -> C11 / U5.8 ----------------------------------------------
    t(P3, 0.5, [(6.49, -33.185), (10.0, -33.185), (22.65, -20.53), (27.7, -20.53)])
    t(P3, 0.4, [(27.7, -20.53), (28.55, -20.53), (29.2, -21.2), (29.2, -31.6)])
    R.via(P3, 29.2, -31.6)
    t(P3, 0.4, [(29.2, -31.6), (32.3, -38.7)], layer=B)
    R.via(P3, 32.3, -38.7)
    t(P3, 0.4, [(32.3, -38.7), (33.0, -38.0), (33.225, -37.7)])
    t(P3, 0.25, [(33.45, -37.45), (34.0, -36.9), (34.0, -35.15)])
    # --- J1 GND vias ---------------------------------------------------------------------------
    for y in J1_GND_EVEN.values():
        t(G, 0.5, [(3.95, y), (2.35, y)])
        R.via(G, 2.35, y)
    for y in J1_GND_ODD.values():
        t(G, 0.5, [(6.49, y), (8.1, y)])
        R.via(G, 8.1, y)


if __name__ == "__main__":
    routelib.run("3", build)
