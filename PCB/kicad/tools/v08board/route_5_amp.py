"""Section 5: speaker amp U7 (MAX98357A) + output filter + speaker header J7 (KiCad python, GUI closed).
Re-runnable (owned_5.json). All items locked.

U7 stays at (36.0, -20.0) r0: west pins 1..4 (DIN, GAIN, GND, SD_MODE, x 34.562), south 5..8 (NC, NC, VDD, VDD,
y -18.562), east 9..12 (OUTP, OUTN, GND, NC, x 37.438), north 13..16 (NC, LRCLK, GND, BCLK, y -21.438).
- +5V: VDD pins face south, so the decoupling sits south of U7: C22 (0.1u) right under pins 7/8, C21 (10u) next
  to it. Fed by a 0.8 mm F.Cu line along y -17.5 from the +5V branch corner (30.5, -17.6). The section-3 stub
  to the old C22 spot (y -24) is removed here (and dropped from route_3_power.py) - it would dangle, and the
  space north of U7 is wanted for the section-6 I2S hops.
- GND: pins 3 / 11 / 15 tie into the EP, EP has 2 vias (diagonal, hole gap >= 0.5). Via at every GND cap pad,
  JP1.3, R22.2.
- Outputs: OUTP -> FB1 (vertical, x 39.9) -> SPK+ -> J7.2 (x 39.66); OUTN -> FB2 (x 42.2) -> SPK- -> J7.1.
  Pins leave 0.25 mm, widen to 0.5 mm once clear of the pad row; the pair runs side by side, no crossing.
  C24 (SPK-) east of FB2, C23 (SPK+) west of J7.2 (J7 courtyard leaves no room nearer).
- GAIN pin 2 -> JP1.2 straight west. SD_MODE pin 4 is boxed in by JP1.1 (+5V) and the +5V feed, so it hops:
  via (33.6,-18.95) -> B.Cu 2.5 mm under the feed -> via (32.825,-16.55) -> R22.1 / R21.2 (node, x 32.825).
- Section-6 exits: AMP_SD at R21.1 (31.175,-13.7) west (open F.Cu between J5 pins); DIN pin 1 west then north
  in the JP1/U7 gap (x ~33.6); BCLK (16) / LRCLK (14) north. U7's west/north is walled by the +5V branch
  (x 30.5) and this feed, so those three need B.Cu hops; x 31..36, y -29..-22.4 is left empty for their vias.
"""
import sys
import pcbnew
import routelib
from routelib import B, MM

P5, G, AW = "+5V", "GND", 0.5
PLACE = {
    "C22": (36.6, -16.2, -90),     # 0.1u: pad1 +5V north (-16.975), pad2 GND (-15.425)
    "C21": (34.7, -15.85, -90),    # 10u 0805: pad1 +5V (-16.8), pad2 GND (-14.9)
    "FB1": (39.9, -17.85, -90),    # pad1 AMP_OUTP north (-18.912), pad2 SPK+ (-16.788)
    "FB2": (42.2, -17.85, -90),    # pad1 AMP_OUTN, pad2 SPK-
    "C24": (44.2, -18.0, 90),      # 220p SPK-: pad1 south (-17.225), pad2 GND (-18.775)
    "C23": (36.95, -12.9, -90),    # 220p SPK+: pad1 north (-13.675), pad2 GND (-12.125)
    "R22": (32.0, -15.6, 180),     # 1.8k: pad1 SD_MODE east (32.825), pad2 GND west (31.175)
    "R21": (32.0, -13.7, 0),       # 10k: pad1 AMP_SD west (31.175), pad2 SD_MODE east (32.825)
}
STUB = ((30.5, -24.0), (35.225, -24.0))   # section-3 +5V stub to the old C22 spot


def drop_stub():
    b = pcbnew.LoadBoard(routelib.PCB)
    want = {tuple(MM(v) for v in p) for p in STUB}
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() == P5:
            ends = {(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)}
            if ends == want:
                b.Remove(t)
                b.Save(routelib.PCB)
                print("removed section-3 C22 stub")
                return


def build(b, R):
    routelib.place(b, PLACE)
    t, v = R.track, R.via
    # --- +5V feed + VDD ------------------------------------------------------------------------
    t(P5, 0.8, [(30.5, -17.6), (31.0, -17.5), (36.6, -17.5)])
    t(P5, 0.25, [(36.25, -18.562), (36.25, -17.5)])
    t(P5, 0.25, [(36.75, -18.562), (36.75, -17.5)])
    # --- GND: pins -> EP, EP vias, cap / jumper / resistor vias ------------------------------------
    t(G, 0.25, [(34.562, -19.75), (35.5, -19.75)])
    t(G, 0.25, [(37.438, -20.25), (36.5, -20.25)])
    t(G, 0.25, [(35.75, -21.438), (35.75, -20.5)])
    v(G, 35.69, -20.31)
    v(G, 36.31, -19.69)
    t(G, 0.6, [(34.7, -14.9), (35.65, -14.9), (36.6, -15.425)])      # C21.2 - C22.2
    t(G, 0.5, [(35.65, -14.9), (35.65, -14.3)])
    v(G, 35.65, -14.3)
    t(G, 0.5, [(34.7, -14.9), (34.7, -13.9)])
    v(G, 34.7, -13.9)
    t(G, 0.4, [(32.3, -21.3), (31.6, -22.4)])                         # JP1.3
    v(G, 31.6, -22.4)
    t(G, 0.4, [(31.175, -15.6), (30.35, -15.6)])                      # R22.2
    v(G, 30.35, -15.6)
    t(G, 0.4, [(44.2, -18.775), (44.2, -19.85)])                      # C24.2
    v(G, 44.2, -19.85)
    t(G, 0.4, [(36.95, -12.125), (36.95, -11.2)])                     # C23.2
    v(G, 36.95, -11.2)
    # --- outputs: U7 -> ferrites -> J7 -------------------------------------------------------------
    t("/AMP_OUTP", 0.25, [(37.438, -19.25), (38.2, -19.25), (38.45, -19.0)])
    t("/AMP_OUTP", AW, [(38.45, -19.0), (39.9, -19.0), (39.9, -18.912)])
    t("/AMP_OUTN", 0.25, [(37.438, -19.75), (38.2, -19.75), (38.5, -20.05)])
    t("/AMP_OUTN", AW, [(38.5, -20.05), (42.2, -20.05), (42.2, -18.912)])
    t("/SPK+", AW, [(39.9, -16.788), (39.9, -15.2), (39.66, -14.2)])
    t("/SPK-", AW, [(42.2, -16.788), (42.2, -14.2)])
    t("/SPK-", 0.4, [(42.2, -16.788), (43.0, -17.225), (44.2, -17.225)])   # C24.1
    t("/SPK+", 0.4, [(39.66, -14.2), (38.4, -13.675), (36.95, -13.675)])   # C23.1
    # --- GAIN, SD_MODE ---------------------------------------------------------------------------
    t("/GAIN_SLOT", 0.25, [(34.562, -20.25), (34.0, -20.25), (33.6, -20.0), (32.3, -20.0)])
    t("/SD_MODE", 0.25, [(34.562, -19.25), (33.9, -19.25), (33.6, -18.95)])
    v("/SD_MODE", 33.6, -18.95)
    t("/SD_MODE", 0.25, [(33.6, -18.95), (32.825, -16.55)], layer=B)
    v("/SD_MODE", 32.825, -16.55)
    t("/SD_MODE", 0.25, [(32.825, -16.55), (32.825, -15.6), (32.825, -13.7)])


if __name__ == "__main__":
    if "--drop" in sys.argv:
        drop_stub()
        sys.exit()
    if "--add" not in sys.argv:   # SWIG: a second LoadBoard after Remove() breaks, so drop in its own process
        import subprocess
        subprocess.run([sys.executable, sys.argv[0], "--drop"], check=True)
    routelib.run("5", build)
