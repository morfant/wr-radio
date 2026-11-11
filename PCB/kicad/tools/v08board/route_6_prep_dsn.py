"""Section 6: turn KiCad's raw Specctra DSN into the Freerouting input (system python3).
usage: route_6_prep_dsn.py raw.dsn out.dsn
 - drops the practice B.Cu GND plane (section 7 pours the real one; as a plane it would block B.Cu)
 - keeps only the section-6 signal nets (KEEP_NETS) in the network: every other net (GND = section 7,
   +3V3, power, already-routed nets) is dropped, so its pads/copper are plain fixed obstacles and
   Freerouting can never add copper to it. +3V3 J1.1/J1.17 groups stay unjoined (joined inside the Pi).
 - turns the remaining (F.Cu, locked) zones into keepouts
 - adds wire/via keepouts (KEEPOUTS, board mm, KiCad y)
All existing copper is (type fix) in the export because every track/via is locked."""
import os
import re
import sys

KEEP_NETS = ["/AMP_SD", "/CHG_DIS", "/ENC_KEY", "/ENC_S1", "/ENC_S2", "/HP_DET", "/I2S_BCLK", "/I2S_DIN",
             "/I2S_LRCLK", "/LCD_BL", "/LCD_CLK", "/LCD_CS", "/LCD_DC", "/LCD_DIN", "/LCD_RST", "/SDA", "/SCL",
             "/UART_RX", "/UART_TX"]  # BST_EN, VBAT/VBUS_SENSE, UART: route_6a_hand.py (already routed -> no-op)
if os.environ.get("KEEP_ONLY"):     # second pass: route only these nets (comma separated)
    KEEP_NETS = os.environ["KEEP_ONLY"].split(",")
# (name, layer or "signal" = both, x0, y0, x1, y1) in board mm (KiCad coordinates, y down)
KEEPOUTS = [
    ("boost", "signal", 33.0, -62.0, 52.0, -48.6),      # U4/L1/C6/C7/C8 switching area
    ("dac_out", "signal", 9.5, -59.5, 28.0, -47.6),     # U6 top half, charge pump, HP_L/HP_R/jack
    ("amp_out", "signal", 37.6, -22.2, 46.0, -11.0),    # U7 outputs, FB1/FB2, J7
]


def block_end(s, i):
    """index just past the s-expression that starts with '(' at i"""
    depth, q = 0, False
    for k in range(i, len(s)):
        c = s[k]
        if c == '"':
            q = not q
        elif not q and c == "(":
            depth += 1
        elif not q and c == ")":
            depth -= 1
            if depth == 0:
                return k + 1
    raise ValueError("unbalanced")


def cut(s, pattern):
    n = 0
    while True:
        m = re.search(pattern, s)
        if not m:
            return s, n
        s = s[:m.start()] + s[block_end(s, m.start()):]
        n += 1


# B.Cu must stay a mostly solid GND plane: Freerouting may use B.Cu only inside these windows
# (board mm, KiCad y). Everything else on B.Cu becomes keepout rectangles (b_tiles()).
BOARD = (-1.0, -66.0, 65.0, 6.0)
B_WINDOWS = [
    ("west", 0.5, -49.5, 16.0, -34.0),     # J1 / J9 / C25 tangle (UART, BCLK, HP_DET, SDA/SCL)
    ("door", 22.0, -31.5, 36.0, -22.4),    # under J6 gaps, +3V3 (x 29.2), +5V branch (x 30.5) into the U7-north via field
    ("north", 24.5, -46.5, 36.0, -38.9),   # under +5V / BST_EN / SYS north of J4.3
    ("u7", 30.5, -22.4, 38.0, -14.5),      # under the U7 +5V feed (y -17.5)
    ("chg", 45.8, -36.5, 48.2, -28.4),     # CHG_DIS exit via south under the status/VBUS lines
    ("j1south", 2.5, -17.0, 10.0, -2.5),   # J1 bottom: LCD / I2S order fix-ups
    ("cprime", 28.8, -24.0, 32.5, -18.5),  # strip between +3V3 (x 29.2) and +5V (x 30.5) -> under +5V to U7/U5 side
    ("j1edge", 0.3, -29.5, 4.5, -26.5),    # west board edge -> J1.22 (CHG_DIS)
]
HOLES = [(59.44, -29.16), (5.1, 0.0), (5.12, -59.6), (58.42, -59.6), (58.44, 0.0)]  # NPTH 2.7, keep 0.3 more


if os.environ.get("EXTRA_WIN"):     # second pass: extra B.Cu windows "x0,y0,x1,y1;..."
    B_WINDOWS = B_WINDOWS + [("extra",) + tuple(map(float, w.split(","))) for w in os.environ["EXTRA_WIN"].split(";")]


def b_tiles(windows):
    xs = sorted({BOARD[0], BOARD[2]} | {w[1] for w in windows} | {w[3] for w in windows})
    tiles = []
    for xa, xb in zip(xs, xs[1:]):
        cov = sorted((w[2], w[4]) for w in windows if w[1] <= xa and w[3] >= xb)
        y = BOARD[1]
        for ya, yb in cov:
            if ya > y:
                tiles.append((xa, y, xb, ya))
            y = max(y, yb)
        if y < BOARD[3]:
            tiles.append((xa, y, xb, BOARD[3]))
    return tiles


def um(v):
    return "%d" % round(v * 1000)


def main(src, dst):
    s = open(src).read()
    s, n = cut(s, r"\(plane GND \(polygon B\.Cu")
    print("removed B.Cu GND plane:", n)
    names = [r for r in re.findall(r'\(net ("[^"]*"|\S+)\s*\n\s*\(pins', s)]
    if True:   # drop every other net: its pads/copper become plain fixed obstacles
        # the locked F.Cu zones (other nets) stay as plain copper obstacles
        s, n = re.subn(r'\(plane ("[^"]*"|\S+) \(polygon', r'(keepout "zone_\1" (polygon', s)
        s = s.replace('"zone_"', '"zone_').replace('""', '"')
        print("F.Cu zones -> keepouts:", n)
        dropped = 0
        for raw in names:
            if raw.strip('"') not in KEEP_NETS:
                s, n = cut(s, r"\(net %s\s*\n\s*\(pins" % re.escape(raw))
                dropped += n
        print("dropped nets:", dropped, "kept:", len(names) - dropped)
    s, n = cut(s, r"\(class ")
    print("classes removed:", n)
    cls = ('    (class signal6 %s\n      (circuit (use_via "Via[0-1]_600:300_um"))\n'
           '      (rule (width 250) (clearance 200))\n    )\n' % " ".join(KEEP_NETS))
    i = s.index("  (wiring")
    j = s.rindex(")", 0, i)          # closing paren of (network
    s = s[:j] + cls + "  " + s[j:]
    ko = []
    for name, layer, x0, y0, x1, y1 in KEEPOUTS:
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        poly = " ".join("%s %s" % (um(x), um(-y)) for x, y in pts)
        ko.append('    (keepout "%s" (polygon %s 0 %s))\n' % (name, layer, poly))
    for k, (x, y) in enumerate(HOLES):
        ko.append('    (keepout "hole%d" (circle signal %s %s %s))\n' % (k, um(2 * (1.35 + 0.3)), um(x), um(-y)))
    for k, (x0, y0, x1, y1) in enumerate(b_tiles(B_WINDOWS)):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        poly = " ".join("%s %s" % (um(x), um(-y)) for x, y in pts)
        ko.append('    (keepout "bcu%d" (polygon B.Cu 0 %s))\n' % (k, poly))
    i = s.index("    (via \"Via[0-1]_600")
    s = s[:i] + "".join(ko) + s[i:]
    open(dst, "w").write(s)
    print("wrote", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
