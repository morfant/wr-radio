"""Section 4a: headphone DAC U6 (PCM5102A) pin-level wiring + its decoupling (KiCad python, GUI closed).
Re-runnable (owned_4a.json). All items locked. Outputs / jack / detect are in route_4b_jack.py.

U6 moved 1.0 mm down to (19.0, -46.0) r-90 so the charge-pump caps fit between its top pin row (y -48.862,
pins 1..10 right->left) and the +5V trunk band (y -54.04). Bottom row y -43.138 (pins 11..20 left->right).
- Charge pump: C16 (CAPP/CAPM) right above pins 2/4; C17 (VNEG) one row higher above pin 5; CPGND (pin 3)
  goes up between the C16 pads (0.2 mm) to C17.2 and its GND via. Loop CAPP-C16-CAPM < 2 mm.
- +3V3: under the U6 body a bar at y -47.7 ties AVDD (8) and CPVDD (1) and runs down x 21.925 to DVDD (20);
  left end on C12.1 (section-3 J1.1 feed), R18.2 (XSMT pull-up) taps it from below. Right: C14 (CPVDD) on pin 1,
  C13 (DVDD) on a branch y -45.6, C15 (10 uF) via a line at y -47.3.
- LDOO (18) leaves outward (south, under the J4 pin field - copper only) to C18 right of pin 20.
- XSMT (17) runs under the body at y -45.2 to R18 left of U6.
- GND: via at every GND pin/cap pad (pins 9+10 above, 11+12 / 16 / 19 under the body, pin 3 via C17.2).
- I2S BCK(13) / DIN(14) / LRCK(15) left free: their pads exit south (outward) into the J4 pin field - section 6.
"""
import routelib

P3, G = "+3V3", "GND"
YT, YB = -48.862, -43.138          # U6 top / bottom pad rows


def px(pin):
    """U6 pad x (r-90 at x 19.0): top row 1..10 right->left, bottom row 11..20 left->right."""
    return 21.925 - 0.65 * (pin - 1) if pin <= 10 else 16.075 + 0.65 * (pin - 11)


PLACE = {
    "U6": (19.0, -46.0, -90),
    "C16": (20.925, -50.75, 180),   # pad1 CAPP right (21.7), pad2 CAPM left (20.15)
    "C17": (20.3, -52.4, 0),        # pad1 VNEG (19.525), pad2 GND (21.075)
    "C14": (24.4, YT, 0),           # CPVDD 0.1u: pad1 +3V3 23.625
    "C13": (24.4, -45.6, 0),        # DVDD 0.1u
    "C18": (24.4, YB, 0),           # LDOO 2.2u: pad1 23.625
    "C12": (14.65, -49.0, 90),      # AVDD 0.1u: pad1 +3V3 bottom (-48.225, section-3 feed ends here)
    "R18": (14.65, -45.9, 90),      # XSMT 10k: pad1 XSMT bottom (-45.075), pad2 +3V3 top (-46.725)
}


def build(b, R):
    routelib.place(b, PLACE)
    t, v = R.track, R.via
    # --- charge pump ---------------------------------------------------------------------------
    t("/CAPM", 0.3, [(px(4), YT), (px(4), -50.75)])
    t("/CAPP", 0.3, [(px(2), YT), (px(2), -49.75), (21.7, -50.175), (21.7, -50.75)])
    t("/VNEG", 0.25, [(px(5), YT), (px(5), -52.4)])
    t(G, 0.2, [(px(3), YT), (px(3), -49.75), (20.925, -50.05), (20.925, -52.4)])   # CPGND -> C17.2
    t(G, 0.3, [(21.075, -52.4), (22.15, -52.4)])
    v(G, 22.15, -52.4)
    # --- +3V3 ----------------------------------------------------------------------------------
    t(P3, 0.3, [(14.65, -47.7), (px(8), -47.7), (px(1), -47.7)])            # under-body bar
    t(P3, 0.3, [(px(8), YT), (px(8), -47.7)])
    t(P3, 0.3, [(px(1), YT), (px(1), -47.7), (px(20), YB)])                  # CPVDD - DVDD
    t(P3, 0.3, [(14.65, -46.725), (14.65, -47.7)])                           # R18.2
    t(P3, 0.3, [(px(1), YT), (23.625, YT)])                                  # C14.1
    t(P3, 0.3, [(px(20), -45.6), (23.625, -45.6)])                           # C13.1
    t(P3, 0.3, [(22.8, YT), (22.8, -47.3), (27.8, -47.3), (27.8, -47.95)])   # C15.1
    # --- LDOO / XSMT ---------------------------------------------------------------------------
    t("/LDOO", 0.3, [(px(18), YB), (px(18), -41.75), (23.625, -41.75), (23.625, YB)])
    t("/XSMT", 0.25, [(px(17), YB), (px(17), -45.2), (14.65, -45.2), (14.65, -45.075)])
    # --- GND vias ------------------------------------------------------------------------------
    t(G, 0.3, [(px(9), YT), (px(9), -49.9), (16.4, -50.45)])
    t(G, 0.3, [(px(10), YT), (px(10), -49.9), (16.4, -50.45)])
    v(G, 16.4, -50.45)
    t(G, 0.3, [(px(11), YB), (px(11), -44.0), (16.4, -44.48)])
    t(G, 0.3, [(px(12), YB), (px(12), -44.0), (16.4, -44.48)])
    v(G, 16.4, -44.48)
    t(G, 0.3, [(px(16), YB), (px(16), -44.48)])
    v(G, px(16), -44.48)
    t(G, 0.3, [(px(19), YB), (21.2, -44.6)])
    v(G, 21.2, -44.6)
    for y in (YT, -45.6):                                                   # C14.2, C13.2
        t(G, 0.4, [(25.175, y), (26.25, y)])
        v(G, 26.25, y)
    t(G, 0.4, [(25.175, YB), (25.175, -41.75)])                              # C18.2
    v(G, 25.175, -41.75)
    t(G, 0.4, [(27.8, -49.85), (27.8, -50.9)])                               # C15.2
    v(G, 27.8, -50.9)
    t(G, 0.4, [(14.65, -49.775), (15.3, -50.5)])                             # C12.2
    v(G, 15.3, -50.5)


if __name__ == "__main__":
    routelib.run("4a", build)
