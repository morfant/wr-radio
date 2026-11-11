"""Section 4b: DAC outputs -> 100R / 2.2nF -> jack J8, and the tip-NC headphone detect (KiCad python, GUI closed).
Run after route_4a_dac.py. Re-runnable (owned_4b.json). All items locked.

U6 OUTL (pin 6) sits right of OUTR (pin 7) while the jack has L (J8.5) left of R (J8.2), so one L/R crossing is
unavoidable; it is done on B.Cu by DAC_R (low-impedance DAC side). The +5V trunk (y -54.04) closes the jack
area, so every jack line crosses it on B.Cu.
- L: pin 6 -> north, west at y -51.4 -> R19 (row y -52.3, west of the pin-9/10 GND via) -> HP_L node
  (R19.2, C19.1) -> via V_L (12.75,-52.6) -> B.Cu -> J8.5.
- R: pin 7 -> via (18.0,-50.45) -> B.Cu under C17 / trunk -> via (24.725,-55.35) inside the jack area ->
  R20 (100R) -> HP_R node (R20.2, C20.1) -> J8.2 on F.Cu. RF shunt C20 sits at the jack.
- Detect: J8.4 (TN) -> B.Cu x ~13.55 (also passes under the section-3 +3V3 feed J1.1->C12, which walls the
  jack side off from the south) -> via V_T (13.6,-47.4) -> F (west of R18) -> R23 (4.7k)
  -> HP_DET node (R23.2, C25.1). C25 (22u) moved out of the jack area to (11.25,-40.3), GND via beside it.
  HP_DET exit for section 6: from R23.2 (13.82,-41.925) / C25.1 (12.2,-40.3) toward J1.16 (3.95,-35.725).
"""
import routelib
from routelib import B

AU = 0.3
PLACE = {
    "R19": (15.45, -52.3, 180),    # pad1 DAC_L 16.275, pad2 HP_L 14.625
    "C19": (13.1, -50.6, -90),     # pad1 HP_L top (-51.375), pad2 GND (-49.825)
    "R20": (23.9, -56.3, 180),     # pad1 DAC_R 24.725, pad2 HP_R 23.075
    "C20": (23.9, -58.0, 0),       # pad1 HP_R 23.125, pad2 GND 24.675
    "R23": (13.82, -42.75, -90),   # pad1 HP_TN top (-43.575), pad2 HP_DET (-41.925)
    "C25": (11.25, -40.3, 180),    # pad1 HP_DET 12.2, pad2 GND 10.3
}


def build(b, R):
    routelib.place(b, PLACE)
    t, v = R.track, R.via
    # --- left channel --------------------------------------------------------------------------
    t("/DAC_L", AU, [(18.675, -48.862), (18.675, -51.4), (16.275, -51.4), (16.275, -52.3)])
    t("/HP_L", AU, [(14.625, -52.3), (12.75, -52.6)])
    t("/HP_L", AU, [(12.75, -52.6), (13.1, -51.375)])
    v("/HP_L", 12.75, -52.6)
    t("/HP_L", AU, [(12.75, -52.6), (11.0, -56.4)], layer=B)
    t("GND", 0.4, [(13.1, -49.825), (14.65, -49.775)])            # C19.2 -> C12.2 and its GND via
    # --- right channel -------------------------------------------------------------------------
    t("/DAC_R", AU, [(18.025, -48.862), (18.0, -50.45)])
    v("/DAC_R", 18.0, -50.45)
    t("/DAC_R", AU, [(18.0, -50.45), (19.5, -53.6), (23.0, -53.6), (24.725, -55.35)], layer=B)
    v("/DAC_R", 24.725, -55.35)
    t("/DAC_R", AU, [(24.725, -55.35), (24.725, -56.3)])
    t("/HP_R", AU, [(23.075, -56.3), (21.0, -56.3)])
    t("/HP_R", AU, [(23.075, -56.3), (23.125, -58.0)])
    t("GND", 0.4, [(24.675, -58.0), (25.8, -58.0)])
    v("GND", 25.8, -58.0)
    # --- headphone detect ----------------------------------------------------------------------
    t("/HP_TN", 0.25, [(13.5, -56.4), (13.6, -47.4)], layer=B)    # under the +3V3 J1.1->C12 feed
    v("/HP_TN", 13.6, -47.4)
    t("/HP_TN", 0.25, [(13.6, -47.4), (13.82, -43.575)])
    t("/HP_DET", 0.25, [(13.82, -41.925), (12.2, -40.3)])
    t("GND", 0.4, [(10.3, -40.3), (10.3, -38.9)])
    v("GND", 10.3, -38.9)


if __name__ == "__main__":
    routelib.run("4b", build)
