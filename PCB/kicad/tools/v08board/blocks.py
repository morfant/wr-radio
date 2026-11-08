"""Block overlay for the placement render. Step 1 (KiCad python): dump group courtyard boxes to JSON.
Step 2 (system python3 with PIL): draw translucent boxes over placement_top.png -> placement_blocks.png.
  KiCad python:  python3 blocks.py dump      System python: python3 blocks.py draw"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.abspath(os.path.join(HERE, "..", "..", "radio-hat-v08"))
JS = os.path.join(HERE, "placement_blocks.json")
GROUPS = [  # name, refs (or a fixed box "x0,y0,x1,y1"), RGB   -- 2026-11-08 A3 case layout
    ("Pi GPIO J1", "J1", (180, 180, 180)),
    ("UART dbg J9", "J9", (220, 220, 220)),
    ("Plug zone (Dupont, 15 mm)", "@8.66,-41.30,23.66,2.79", (255, 255, 255)),
    ("Plug zone J7", "@37.84,-10.16,44.02,4.84", (255, 255, 255)),
    ("SW J4 / ENC J6 / LCD J5", "J4 J6 J5", (150, 200, 255)),
    ("USB-C in + TVS", "J2 D4 C1 R1 R2 R24", (255, 90, 90)),
    ("Charge LEDs", "D2 D3 R4 R5", (255, 160, 200)),
    ("Charger TP4056 + CE", "U1 C2 R3 C3 Q2 R6 R7", (255, 150, 40)),
    ("Load share", "D1 Q1 R10", (255, 220, 60)),
    ("Protection + BAT J3", "U2 U3 C4 R8 R9 J3", (200, 120, 255)),
    ("Boost 5V", "U4 L1 C5 C6 C7 C8 C26 C27 R11 R12 R13", (255, 60, 60)),
    ("ADC ADS1115", "U5 C11 R14 R15 R16 R17 C9 C10", (80, 220, 255)),
    ("Headphone DAC", "U6 C12 C13 C14 C15 C16 C17 C18 R18 R19 R20 C19 C20", (80, 255, 120)),
    ("HP jack + detect", "J8 R23 C25", (40, 200, 160)),
    ("Speaker amp + J7", "U7 FB1 FB2 C21 C22 C23 C24 JP1 R21 R22 J7", (120, 255, 60)),
]
if sys.argv[1] == "dump":
    import pcbnew
    from pcbnew import ToMM
    b = pcbnew.LoadBoard(os.path.join(D, "radio-hat-v08.kicad_pcb"))
    out = []
    for name, refs, col in GROUPS:
        if refs.startswith("@"):
            out.append((name, [float(v) for v in refs[1:].split(",")], col)); continue
        xs0 = []
        for r in refs.split():
            f = b.FindFootprintByReference(r); c = f.GetCourtyard(pcbnew.F_CrtYd)
            bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
            xs0.append((ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom())))
        box = [min(a[0] for a in xs0), min(a[1] for a in xs0), max(a[2] for a in xs0), max(a[3] for a in xs0)]
        if name.startswith("Pi"): box[0] = 0.2
        out.append((name, box, col))
    json.dump(out, open(JS, "w"), indent=1)
else:
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(os.path.join(D, "placement_top.png")).convert("RGBA")
    # calibration from the render: hole H3 (5.12,-59.6) and H4 (58.42,-59.6) centres in pixels
    px3, px4, py = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    s = (px4 - px3) / (58.42 - 5.12)
    X = lambda x: px3 + (x - 5.12) * s
    Y = lambda y: py + (y + 59.6) * s
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
    for name, (x0, y0, x1, y1), col in json.load(open(JS)):
        r = (X(x0) - 4, Y(y0) - 4, X(x1) + 4, Y(y1) + 4)
        if name.startswith("Plug zone"):
            dr.rectangle(r, fill=(255, 255, 255, 40), outline=(255, 255, 255, 255), width=3)
        else:
            dr.rectangle(r, fill=tuple(col) + (60,), outline=tuple(col) + (255,), width=4)
    LABEL_AT = {}
    LABEL_MM = {  # label top-left in board mm where the default (below the box) collides
        "Pi GPIO J1": (0.5, -30), "UART dbg J9": (0.6, -41.0), "Plug zone (Dupont, 15 mm)": (9.0, -14.5),
        "SW J4 / ENC J6 / LCD J5": (9.0, 3.2), "Plug zone J7": (35.0, 1.5), "HP jack + detect": (9.6, -64.6), "Headphone DAC": (13.0, -43.2),
        "Boost 5V": (52.0, -64.0), "Load share": (29.2, -51.6), "Charger TP4056 + CE": (37.6, -50.5),
        "USB-C in + TVS": (46.3, -36.6), "Charge LEDs": (52.5, -31.5), "ADC ADS1115": (31.0, -29.6),
        "Speaker amp + J7": (30.5, -27.0), "Protection + BAT J3": (44.2, -23.3),
    }
    for name, (x0, y0, x1, y1), col in json.load(open(JS)):
        tb = dr.textbbox((0, 0), name, font=font); tw, th = tb[2] - tb[0], tb[3] - tb[1]
        tx = min(max(X(x0), 4), im.size[0] - tw - 10); ty = Y(y1) + 8
        if ty + th > im.size[1] - 4: ty = Y(y0) - th - 16
        tx, ty = LABEL_AT.get(name, (tx, ty)) if name not in LABEL_MM else (X(LABEL_MM[name][0]), Y(LABEL_MM[name][1]))
        dr.rectangle((tx - 4, ty - 2, tx + tw + 6, ty + th + 8), fill=(0, 0, 0, 190))
        dr.text((tx, ty), name, font=font, fill=tuple(col) + (255,))
    Image.alpha_composite(im, ov).convert("RGB").save(os.path.join(D, "placement_blocks.png"))
    print("saved placement_blocks.png")
