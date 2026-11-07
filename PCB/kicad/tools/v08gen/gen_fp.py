#!/usr/bin/env python3
"""Generate project footprints into radio-hat-v08.pretty:
  - Jack_3.5mm_PJ-307C_Horizontal   (from Boom PJ-307C datasheet, LCSC C16684)
  - PinHeader_2x20_P2.54mm_Horizontal_PiSide  (stock 2x20 horizontal header mirrored in X)
"""
import re

import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "radio-hat-v08", "radio-hat-v08.pretty")
STOCK = ("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Connector_PinHeader_2.54mm.pretty/"
         "PinHeader_2x20_P2.54mm_Horizontal.kicad_mod")


def f(v):
    v = round(v, 4)
    return str(int(v)) if v == int(v) else ('%.4f' % v).rstrip('0').rstrip('.')


# ===================================================================== PiSide header
def pi_side():
    """Stock PinHeader_2x20_P2.54mm_Horizontal with every X coordinate negated (mirror about the pin-1 column).

    Placed on F.Cu at rotation 0 with pad 1 at v07's Pi-pin-1 position, the plastic body points to -X (off the
    board's left edge), pad 2 sits 2.54 mm left of pad 1 and pins ascend downward: exactly the pad set of the
    stock footprint flipped to B.Cu, but with the body/silk on the top side.  Pad numbers = Pi pin numbers.
    """
    s = open(STOCK).read()
    s = s.replace('(footprint "PinHeader_2x20_P2.54mm_Horizontal"',
                  '(footprint "PinHeader_2x20_P2.54mm_Horizontal_PiSide"', 1)
    s = s.replace('(property "Value" "PinHeader_2x20_P2.54mm_Horizontal"',
                  '(property "Value" "PinHeader_2x20_P2.54mm_Horizontal_PiSide"', 1)
    s = re.sub(r'\(descr "[^"]*"\)',
               '(descr "Through hole angled pin header 2x20 2.54mm, mirrored copy of '
               'Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Horizontal for wr-radio HAT v08: body on the '
               'component side pointing to -X, pad 2 at -2.54 mm, pad n = Raspberry Pi pin n when the Pi lies '
               'face-up beside the HAT")', s, count=1)

    def mx(m):
        return f"({m.group(1)} {f(-float(m.group(2)))} {m.group(3)}"
    s = re.sub(r'\((at|start|end|mid|xy|center) (-?[\d.]+) (-?[\d.]+)', mx, s)
    # 3D model: rotate 180 deg about Z (maps (x,y)->(-x,-y)) then shift rows back down by 19*2.54 mm
    # (KiCad model offset Y is in 3D coords, +Y = up = -board Y).
    m = re.search(r'\(model "[^"]*"(.*?)\n\t\)', s, re.S)
    blk = m.group(0)
    nb = re.sub(r'\(offset\s*\(xyz [^)]*\)\s*\)', '(offset (xyz 0 -48.26 0))', blk)
    nb = re.sub(r'\(rotate\s*\(xyz [^)]*\)\s*\)', '(rotate (xyz 0 0 180))', nb)
    s = s.replace(blk, nb)
    open(f"{OUT}/PinHeader_2x20_P2.54mm_Horizontal_PiSide.kicad_mod", "w").write(s)


# ===================================================================== PJ-307C
# Datasheet (LCSC C16684, "封装尺寸图" page), all in mm.  Frame here: origin = pad 1, +X = into the jack (away
# from the plug opening), +Y = toward pad 5.  Datasheet layout is a TOP VIEW with the plug opening on the left,
# pad 2 at the top and pad 5 at the bottom, so datasheet coordinates map directly (KiCad +Y = down).
BODY_FRONT = -3.5     # main body front face: pad 1 column is 3.5 mm behind it (dims "1" + "2.5" from front face)
BODY_DEPTH = 11.0     # "11"
BODY_W = 12.0         # "12" (front view width)
NOSE_LEN = 3.0        # "3" (plug barrel in front of the body)
NOSE_W = 6.0          # barrel diameter "phi X" not given -> 6.0 assumed (scaled from the layout drawing)
PIN_COL = 8.5 + BODY_FRONT   # pads 2..5 and rear peg: 8.5 mm from the front face -> x = 5.0
SLOT = (1.5, 0.8)     # "5-(1.5x0.8)" terminal holes
SLOT_PAD_EXTRA = 0.7  # annular ring 0.35 mm each side (assumption)
PEG_D = 1.2           # "5-phi1.2" round holes (locating pegs, NPTH assumption)

PADS = [  # num, x, y, slot along X?
    ("1", 0.0, 0.0, False),          # sleeve: slot drawn vertical (long axis along Y)
    ("2", PIN_COL, -5.0, True),      # ring spring
    ("3", PIN_COL, -2.5, True),      # ring NC contact
    ("4", PIN_COL, 2.5, True),       # tip NC contact
    ("5", PIN_COL, 5.0, True),       # tip spring
]
PEGS = [(BODY_FRONT + 1.0, -5.0), (BODY_FRONT + 3.5, -5.0), (BODY_FRONT + 1.0, 5.0), (BODY_FRONT + 3.5, 5.0),
        (PIN_COL, 0.0)]


def line(x1, y1, x2, y2, layer, w):
    return (f'\t(fp_line (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) (stroke (width {w}) (type solid)) '
            f'(layer "{layer}"))\n')


def rect(x1, y1, x2, y2, layer, w):
    return (f'\t(fp_rect (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) (stroke (width {w}) (type solid)) '
            f'(fill no) (layer "{layer}"))\n')


def text(kind, txt, x, y, layer, size=1.0, hide=False):
    h = ' (hide yes)' if hide else ''
    th = round(size * 0.15, 3)
    if kind == 'user':
        return (f'\t(fp_text user "{txt}" (at {f(x)} {f(y)} 0) (layer "{layer}") '
                f'(effects (font (size {size} {size}) (thickness {th}))))\n')
    return (f'\t(property "{kind}" "{txt}" (at {f(x)} {f(y)} 0) (layer "{layer}"){h} '
            f'(effects (font (size {size} {size}) (thickness {th}))))\n')


def pj307c():
    x0, x1 = BODY_FRONT, BODY_FRONT + BODY_DEPTH
    y0, y1 = -BODY_W / 2, BODY_W / 2
    nx0 = BODY_FRONT - NOSE_LEN
    s = ('(footprint "Jack_3.5mm_PJ-307C_Horizontal"\n\t(version 20241229)\n\t(generator "v08gen")\n'
         '\t(layer "F.Cu")\n'
         '\t(descr "3.5mm stereo jack, Boom PJ-307C (LCSC C16684), THT horizontal, tip and ring NC switches. '
         'Pads = datasheet pins: 1 sleeve, 2 ring, 3 ring NC, 4 tip NC, 5 tip. Plug opening at -X")\n'
         '\t(tags "audio jack 3.5mm stereo switched PJ-307C PJ307C")\n')
    s += text("Reference", "REF**", 1.5, y0 - 1.6, "F.SilkS")
    s += text("Value", "PJ-307C", 1.5, y1 + 1.6, "F.Fab")
    s += text("Footprint", "", 0, 0, "F.Fab", hide=True)
    s += text("Datasheet", "https://www.lcsc.com/product-detail/C16684.html", 0, 0, "F.Fab", hide=True)
    s += text("Description", "PJ-307C 3.5mm switched stereo jack", 0, 0, "F.Fab", hide=True)
    s += '\t(attr through_hole)\n'
    # F.Fab: body + barrel
    s += rect(x0, y0, x1, y1, "F.Fab", 0.1)
    s += rect(nx0, -NOSE_W / 2, x0, NOSE_W / 2, "F.Fab", 0.1)
    s += text('user', "${REFERENCE}", 1.5, 0 + 3.0, "F.Fab", size=0.8)
    s += text('user', "PLUG", nx0 + 1.5, -NOSE_W / 2 - 0.9, "F.Fab", size=0.6)
    # F.SilkS: body outline 0.11 outside fab (no pads lie on the outline), barrel, plug-opening arrow
    o = 0.11
    sx0, sx1, sy0, sy1 = x0 - o, x1 + o, y0 - o, y1 + o
    s += line(sx0, sy0, sx1, sy0, "F.SilkS", 0.12)
    s += line(sx1, sy0, sx1, sy1, "F.SilkS", 0.12)
    s += line(sx1, sy1, sx0, sy1, "F.SilkS", 0.12)
    s += line(sx0, sy1, sx0, NOSE_W / 2 + o, "F.SilkS", 0.12)
    s += line(sx0, sy0, sx0, -NOSE_W / 2 - o, "F.SilkS", 0.12)
    nxs = nx0 - o
    s += line(sx0, -NOSE_W / 2 - o, nxs, -NOSE_W / 2 - o, "F.SilkS", 0.12)
    s += line(sx0, NOSE_W / 2 + o, nxs, NOSE_W / 2 + o, "F.SilkS", 0.12)
    s += line(nxs, -NOSE_W / 2 - o, nxs, NOSE_W / 2 + o, "F.SilkS", 0.2)   # plug-opening edge (thicker)
    # arrow inside the barrel outline pointing out through the opening (stays on-board if the barrel overhangs)
    ax = nx0 + 0.5
    s += line(ax, 0, ax + 2.0, 0, "F.SilkS", 0.12)
    s += line(ax + 0.6, -0.5, ax, 0, "F.SilkS", 0.12)
    s += line(ax + 0.6, 0.5, ax, 0, "F.SilkS", 0.12)
    # pin-1 marker next to pad 1
    s += line(-1.6, -1.6, -1.6, -0.6, "F.SilkS", 0.12)
    # F.CrtYd: union of body+barrel+pads, 0.25 clearance, on 0.05 grid
    c = 0.25
    cx0, cx1, cy0, cy1 = x0 - c, x1 + c, y0 - c, y1 + c
    ncx0 = nx0 - c
    ny0, ny1 = -NOSE_W / 2 - c, NOSE_W / 2 + c
    pts = [(ncx0, ny0), (cx0, ny0), (cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1), (cx0, ny1), (ncx0, ny1)]
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        s += line(a[0], a[1], b[0], b[1], "F.CrtYd", 0.05)
    # pads
    for num, x, y, along_x in PADS:
        dl, ds = SLOT
        pl, pw = dl + SLOT_PAD_EXTRA, ds + SLOT_PAD_EXTRA
        sx, sy = (pl, pw) if along_x else (pw, pl)
        hx, hy = (dl, ds) if along_x else (ds, dl)
        shape = "rect" if num == "1" else "oval"
        s += (f'\t(pad "{num}" thru_hole {shape} (at {f(x)} {f(y)}) (size {f(sx)} {f(sy)}) '
              f'(drill oval {f(hx)} {f(hy)}) (layers "*.Cu" "*.Mask") (remove_unused_layers no))\n')
    for (x, y) in PEGS:
        s += (f'\t(pad "" np_thru_hole circle (at {f(x)} {f(y)}) (size {PEG_D} {PEG_D}) (drill {PEG_D}) '
              f'(layers "*.Cu" "*.Mask"))\n')
    s += '\t(embedded_fonts no)\n)\n'
    open(f"{OUT}/Jack_3.5mm_PJ-307C_Horizontal.kicad_mod", "w").write(s)


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    pi_side()
    pj307c()
    print("footprints written to", OUT)
