"""Section 2 placement (charger + load share + USB-C side parts). Run before route_2a/2b/2c (KiCad python, GUI closed).
Re-runnable (absolute positions). Old positions (before 2026-11-12) are in the comments.

Idea: D1 sits right of the boost so its cathode pad touches the SYS trunk and its anode pad is fed straight from
J2 VBUS pins A9/B4; U1 is turned 180 deg (VCC top-left, BAT bottom-left, status/CE bottom row) so VBUS reaches VCC
along the band above U1, BAT+ leaves to the left (Q1, then down to J3), and status lines go down and right to D2/D3.
"""
import routelib

PLACE = {
    "U1":  (45.0, -43.6, 270),    # was (46.0,-44.0) r90
    "D1":  (51.0, -49.9, 0),      # was (33.0,-46.0) r90
    "Q1":  (38.0, -46.6, 270),    # was (36.3,-40.5) r0
    "C2":  (40.76, -46.0, 270),   # VCC cap, was (48.5,-38.4) r0
    "C3":  (41.2, -40.6, 270),    # BAT cap, was (46.5,-49.0) r0
    "R3":  (49.2, -46.4, 270),    # PROG, was (44.5,-38.5) r0
    "R2":  (53.6, -47.115, 180),  # CC2, was (53.3,-52.6) r0
    "R1":  (53.6, -45.575, 180),  # CC1, was (56.5,-54.0) r0
    "D4":  (53.6, -41.25, 270),   # TVS, was (53.0,-47.8) r90
    "C1":  (50.75, -42.2, 270),   # VBUS bulk, was (53.0,-42.4) r0
    "R6":  (48.55, -42.6, 90),    # CE pull-up, was (41.6,-48.6) r0
    "Q2":  (49.6, -38.4, 90),     # CE FET, was (40.3,-44.5) r90
    "R7":  (46.9, -37.4, 90),     # Q2 gate pull-down, was (40.3,-40.6) r0
    "R24": (57.3, -40.3, 270),    # VBUS 10k pull-down, was (52.5,-38.0) r0
    "R10": (58.85, -40.3, 270),   # VBUS 100k (Q1 gate pull-down), was (32.6,-40.3) r90
    "R4":  (59.9, -36.15, 0),     # CHRG LED, was (59.6,-38.4) r0
    "R5":  (56.0, -32.6, 0),      # STDBY LED, was (59.6,-34.4) r0
}


def build(b, R):
    routelib.place(b, PLACE)


if __name__ == "__main__":
    routelib.run("place2", build)
