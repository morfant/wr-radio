#!/usr/bin/env python3
"""Generate wr-radio HAT v08 KiCad 10 schematic from PCB/kicad/v08_design_spec.md.

Run:  python3 gen.py   (or ./run.sh for generate + ERC + netlist check + PDF)
Writes into OUTDIR (../../radio-hat-v08): radio-hat-v08.kicad_sch/.kicad_pro/.kicad_sym, sym-lib-table, fp-lib-table.
Also writes expected.json (ref -> {pin: net}) into WORK (env V08_WORK, default ./build) for check_netlist.py.
Footprints for the project library are made by gen_fp.py.
"""
import json
import math
import os
import sys
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import Sym, dump, find, findall, flatten, pins_of, q, fmtnum, parse  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))                 # PCB/kicad
OUTDIR = os.path.join(KICAD_DIR, "radio-hat-v08")
PRO_TEMPLATE = os.path.join(KICAD_DIR, "..", "wr-radio-kicad", "wr-radio-kicad.kicad_pro")
WORK = os.environ.get("V08_WORK", os.path.join(HERE, "build"))
PROJ = "radio-hat-v08"
CUSTOM_LIB = PROJ
NS = uuidlib.UUID("6b1d2f0e-08a8-4c1e-9d55-7a0d0c0e0808")
_uid_n = [0]


def uid(tag=None):
    _uid_n[0] += 1
    return str(uuidlib.uuid5(NS, f"{tag}-{_uid_n[0]}"))


ROOT_UUID = str(uuidlib.uuid5(NS, "root-sheet"))
STUB = 2.54
POWER_NETS = {"GND": "power:GND", "+5V": "power:+5V", "+3V3": "power:+3V3", "VBUS": "power:VBUS"}

# ---------------------------------------------------------------- footprints
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"
FP_C08 = "Capacitor_SMD:C_0805_2012Metric"
FP_LED = "LED_SMD:LED_0603_1608Metric"
FP_FB = "Inductor_SMD:L_0805_2012Metric"

# ---------------------------------------------------------------- LCSC / MPN (from PCB/kicad/v08_parts.md, 2026-11-08)
# passives keyed by (kind, value); other parts keyed by reference.  (LCSC, MPN)
LCSC_PASSIVE = {
    ("R", "100"): ("C22775", "0603WAF1000T5E"), ("R", "1k"): ("C21190", "0603WAF1001T5E"),
    ("R", "1.2k"): ("C22765", "0603WAF1201T5E"), ("R", "1.8k"): ("C4177", "0603WAF1801T5E"), ("R", "2.0k"): ("C22975", "0603WAF2001T5E"),
    ("R", "5.1k"): ("C23186", "0603WAF5101T5E"), ("R", "10k"): ("C25804", "0603WAF1002T5E"),
    ("R", "30k"): ("C22984", "0603WAF3002T5E"), ("R", "100k"): ("C25803", "0603WAF1003T5E"),
    ("R", "220k"): ("C22961", "0603WAF2203T5E"),
    ("R", "4.7k"): ("C23162", "0603WAF4701T5E"), ("R", "510k"): ("C23192", "0603WAF5103T5E"),
    ("R", "68k"): ("C23231", "0603WAF6802T5E"), ("C", "330pF"): ("C1664", "CL10C331JB8NNNC"),
    ("TVS", "SMAJ5.0A"): ("C2925443", "SMAJ5.0A"),
    ("C", "220pF"): ("C1603", "CL10B221KB8NNNC"), ("C", "2.2nF"): ("C1604", "0603B222K500NT"),
    ("C", "0.1uF"): ("C14663", "CC0603KRX7R9BB104"), ("C", "100nF"): ("C14663", "CC0603KRX7R9BB104"),
    ("C", "2.2uF"): ("C23630", "CL10A225KO8NNNC"), ("C", "4.7uF"): ("C19666", "CL10A475KO8NNNC"),
    ("C", "10uF"): ("C15850", "CL21A106KAYNNNE"), ("C", "22uF"): ("C45783", "CL21A226MAQNNNE"),
    ("CP", "220uF"): ("C970695", "RVT1C221M0607"),
    ("LED", "RED"): ("C2286", "KT-0603R"), ("LED", "WHITE"): ("C2290", "KT-0603W"),
    ("FB", "FerriteBead"): ("C85840", "BLM21PG221SN1D"), ("L", "1uH"): ("C53426685", "FXL0420-1R0-MA1"),
    ("D", "SS34"): ("C8678", "SS34"),
}
LCSC_REF = {
    "U1": ("C16581", "TP4056-42-ESOP8"), "U2": ("C351410", "DW01A"), "U3": ("C148371", "WSP8814"),
    "U4": ("C919459", "TPS61023DRLR"), "U5": ("C37593", "ADS1115IDGSR"), "U6": ("C107671", "PCM5102APWR"),
    "U7": ("C910544", "MAX98357AETE+T"), "Q1": ("C15127", "AO3401A"), "Q2": ("C8545", "2N7002"),
    "J2": ("C165948", "TYPE-C-31-M-12"), "J3": ("C158012", "B2B-XH-A(LF)(SN)"), "J8": ("C16684", "PJ-307C"),
}
# deliberately without LCSC: hand-soldered 2.54mm headers + Pi header, mounting holes, solder jumper (copper only)
NO_LCSC = {"J1", "J4", "J5", "J6", "J7", "JP1", "H1", "H2", "H3", "H4", "H5"}
_cur_kind = [None]

# ---------------------------------------------------------------- custom symbols


def _prop(name, val, x=0, y=0, hide=False, justify=None):
    eff = [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]]]
    if justify:
        eff.append([Sym('justify')] + [Sym(j) for j in justify.split()])
    if hide:
        eff.append([Sym('hide'), Sym('yes')])
    return [Sym('property'), name, val, [Sym('at'), x, y, 0], eff]


def _pin(typ, num, name, x, y, rot):
    f = [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]]]
    return [Sym('pin'), Sym(typ), Sym('line'), [Sym('at'), x, y, rot], [Sym('length'), 2.54],
            [Sym('name'), name, f], [Sym('number'), str(num), f]]


def _custom(name, ref, fp, ds, desc, rect, pins):
    (x1, y1, x2, y2) = rect
    body = [Sym('symbol'), f"{name}_0_1",
            [Sym('rectangle'), [Sym('start'), x1, y1], [Sym('end'), x2, y2],
             [Sym('stroke'), [Sym('width'), 0.254], [Sym('type'), Sym('default')]],
             [Sym('fill'), [Sym('type'), Sym('background')]]]]
    pinsub = [Sym('symbol'), f"{name}_1_1"] + [_pin(*p) for p in pins]
    return [Sym('symbol'), name,
            [Sym('pin_names'), [Sym('offset'), 1.016]],
            [Sym('exclude_from_sim'), Sym('no')], [Sym('in_bom'), Sym('yes')], [Sym('on_board'), Sym('yes')],
            _prop("Reference", ref, x1, y1 + 1.27, justify="left bottom"),
            _prop("Value", name, x1, y2 - 1.27, justify="left top"),
            _prop("Footprint", fp, 0, 0, hide=True),
            _prop("Datasheet", ds, 0, 0, hide=True),
            _prop("Description", desc, 0, 0, hide=True),
            _prop("LCSC", "", 0, 0, hide=True),
            body, pinsub, [Sym('embedded_fonts'), Sym('no')]]


CUSTOM = {
    "TPS61023": _custom(
        "TPS61023", "U", "Package_TO_SOT_SMD:SOT-563",
        "https://www.ti.com/lit/ds/symlink/tps61023.pdf",
        "TPS61023 3.7A synchronous boost converter, SOT-563 (TI SLVSF14B). VOUT pin typed passive so the +5V net "
        "can carry the Raspberry Pi symbol's power_out 5V pins and a PWR_FLAG without ERC conflicts.",
        (-7.62, 5.08, 7.62, -5.08),
        [("power_in", 3, "VIN", -10.16, 2.54, 0), ("input", 2, "EN", -10.16, -2.54, 0),
         ("passive", 5, "SW", 10.16, 2.54, 180), ("passive", 6, "VOUT", 10.16, 0, 180),
         ("input", 1, "FB", 10.16, -2.54, 180), ("power_in", 4, "GND", 0, -7.62, 90)]),
    "WSP8814": _custom(
        "WSP8814", "U", "Package_SO:TSSOP-8_4.4x3mm_P0.65mm",
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2211141230_Winsok-Semicon-WSP8814_C148371.pdf",
        "Winsok WSP8814 dual N-MOSFET 20V, common drain (pins 1/8), TSSOP-8, LCSC C148371. Rds(on) 7.6/9.5 mOhm "
        "typ/max @4.5V, 9.5/13 @2.5V. Pinout per Winsok datasheet: 1=D 2,3=S1 4=G1 5=G2 6,7=S2 8=D (8205A-style)",
        (-7.62, 7.62, 7.62, -5.08),
        [("passive", 1, "D1", -10.16, 5.08, 0), ("passive", 2, "S1", -10.16, 2.54, 0),
         ("passive", 3, "S1", -10.16, 0, 0), ("input", 4, "G1", -10.16, -2.54, 0),
         ("passive", 8, "D2", 10.16, 5.08, 180), ("passive", 7, "S2", 10.16, 2.54, 180),
         ("passive", 6, "S2", 10.16, 0, 180), ("input", 5, "G2", 10.16, -2.54, 180)]),
}


def _pj307c():
    """PJ-307C (Boom, LCSC C16684): graphics of Connector_Audio:AudioJack3_SwitchTR with pins renumbered to the
    datasheet pin numbers so they match the footprint pads 1..5. Pin names keep the T/TN/R/RN/S meaning."""
    s = flatten("Connector_Audio", "AudioJack3_SwitchTR")
    name = "PJ-307C"
    s[1] = name
    ren = {"S": "1", "R": "2", "RN": "3", "TN": "4", "T": "5"}
    for e in s:
        if isinstance(e, list) and e and e[0] == 'symbol':
            e[1] = name + e[1][len("AudioJack3_SwitchTR"):]
            for p in findall(e, 'pin'):
                num = find(p, 'number')
                nm = find(p, 'name')
                old = num[1]
                num[1] = ren[old]
                nm[1] = old
        if isinstance(e, list) and e and e[0] == 'property':
            if e[1] == 'Value':
                e[2] = name
            elif e[1] == 'Footprint':
                e[2] = f"{CUSTOM_LIB}:Jack_3.5mm_PJ-307C_Horizontal"
            elif e[1] == 'Datasheet':
                e[2] = "https://www.lcsc.com/product-detail/C16684.html"
            elif e[1] == 'Description':
                e[2] = ("PJ-307C 3.5mm stereo jack, THT horizontal, tip and ring normally-closed switches (no sleeve "
                        "switch). Pins: 1=S sleeve, 5=T tip spring, 4=TN tip NC contact, 2=R ring spring, 3=RN ring NC "
                        "contact. LCSC C16684")
    # hide pin names (graphics already show the function); numbers stay visible
    pn = find(s, 'pin_names')
    if pn is None:
        s.insert(2, [Sym('pin_names'), [Sym('offset'), 1.016], [Sym('hide'), Sym('yes')]])
    idx = max(i for i, e in enumerate(s) if isinstance(e, list) and e[0] == 'property')
    s.insert(idx + 1, _prop("LCSC", "", 0, 0, hide=True))
    return s


CUSTOM["PJ-307C"] = _pj307c()


def lib_symbol(lib_id):
    lib, name = lib_id.split(':')
    if lib == CUSTOM_LIB:
        import copy
        s = copy.deepcopy(CUSTOM[name])
    else:
        s = flatten(lib, name)
    s[1] = lib_id
    return s


# ---------------------------------------------------------------- geometry


def rot_vec(x, y, theta):
    """lib vector (Y up) -> schematic screen vector (Y down) for symbol rotation theta (deg, CCW)."""
    sx, sy = x, -y
    c, s = round(math.cos(math.radians(theta))), round(math.sin(math.radians(theta)))
    return (sx * c + sy * s, -sx * s + sy * c)


def g(v):
    """snap to 2.54 mm grid"""
    return round(round(v / 2.54) * 2.54, 4)


# ---------------------------------------------------------------- schematic items
items = []        # top-level s-expr items (wires, labels, symbols, ...)
used_libs = {}    # lib_id -> lib symbol
expected = {}     # ref -> {pin: net}
pwr_count = [0]
_placed_pwr = []
flg_count = [0]


def text_effects(size=1.27, justify=None, hide=False, bold=False):
    font = [Sym('font'), [Sym('size'), size, size]]
    if bold:
        font.append([Sym('bold'), Sym('yes')])
    eff = [Sym('effects'), font]
    if justify:
        eff.append([Sym('justify')] + [Sym(j) for j in justify.split()])
    if hide:
        eff.append([Sym('hide'), Sym('yes')])
    return eff


def place_symbol(lib_id, ref, value, x, y, rot=0, fp="", props_pos=None, extra_props=None, ds=None, desc=None):
    if lib_id not in used_libs:
        used_libs[lib_id] = lib_symbol(lib_id)
    ls = used_libs[lib_id]
    lprops = {p[1]: p for p in findall(ls, 'property')}
    lib_bom = find(ls, 'in_bom')
    in_bom = not ref.startswith('#') and not (lib_bom and lib_bom[1] == 'no')
    sym = [Sym('symbol'), [Sym('lib_id'), lib_id], [Sym('at'), x, y, rot], [Sym('unit'), 1],
           [Sym('exclude_from_sim'), Sym('no')], [Sym('in_bom'), Sym('yes' if in_bom else 'no')],
           [Sym('on_board'), Sym('yes')], [Sym('dnp'), Sym('no')], [Sym('uuid'), uid(ref)]]
    if props_pos is None:
        props_pos = {}
    fields = [("Reference", ref), ("Value", value), ("Footprint", fp),
              ("Datasheet", ds if ds is not None else (lprops['Datasheet'][2] if 'Datasheet' in lprops else "")),
              ("Description", desc if desc is not None else (lprops['Description'][2] if 'Description' in lprops else ""))]
    if extra_props:
        fields += list(extra_props.items())
    for name, val in fields:
        fang = 0
        if name in props_pos:
            px, py, just, hide = props_pos[name][:4]
            if len(props_pos[name]) > 4:
                fang = props_pos[name][4]
            eff = text_effects(justify=just, hide=hide)
        elif name in ('Reference', 'Value') and name in lprops and rot == 0:
            lp = lprops[name]
            at = find(lp, 'at')
            px, py = x + at[1], y - at[2]
            eff = [e for e in find(lp, 'effects')]
            eff = [x_ for x_ in eff if not (isinstance(x_, list) and x_[0] == 'hide')]
            if ref.startswith('#') and name == 'Reference':
                eff.append([Sym('hide'), Sym('yes')])
        else:
            px, py = x, y
            eff = text_effects(hide=True)
        sym.append([Sym('property'), name, val, [Sym('at'), px, py, fang], eff])
    for p in sorted({p['number'] for p in pins_of(ls)}):
        sym.append([Sym('pin'), p, [Sym('uuid'), uid(ref + p)]])
    sym.append([Sym('instances'), [Sym('project'), PROJ,
                [Sym('path'), '/' + ROOT_UUID, [Sym('reference'), ref], [Sym('unit'), 1]]]])
    items.append(sym)
    return ls


def wire(x1, y1, x2, y2):
    items.append([Sym('wire'), [Sym('pts'), [Sym('xy'), x1, y1], [Sym('xy'), x2, y2]],
                  [Sym('stroke'), [Sym('width'), 0], [Sym('type'), Sym('default')]],
                  [Sym('uuid'), uid('w')]])


def no_connect(x, y):
    items.append([Sym('no_connect'), [Sym('at'), x, y], [Sym('uuid'), uid('nc')]])


def label(name, x, y, d):
    ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
    just = "left bottom" if ang in (0, 90) else "right bottom"
    items.append([Sym('label'), name, [Sym('at'), x, y, ang], [Sym('fields_autoplaced'), Sym('yes')],
                  text_effects(justify=just), [Sym('uuid'), uid('lbl')]])


def power_symbol(net, x, y, d):
    """Place power symbol whose body points in screen direction d from (x,y)."""
    lib_id = POWER_NETS[net]
    if lib_id not in used_libs:
        used_libs[lib_id] = lib_symbol(lib_id)
    pin = pins_of(used_libs[lib_id])[0]
    # body direction in lib = pin direction (pin points from connection toward body)
    bx, by = math.cos(math.radians(pin['rot'])), math.sin(math.radians(pin['rot']))
    for th in (0, 90, 180, 270):
        v = rot_vec(bx, by, th)
        if (round(v[0]), round(v[1])) == d:
            break
    pwr_count[0] += 1
    ref = "#PWR%03d" % pwr_count[0]
    off = 5.2 if d == (0, -1) else 6.2 if d == (0, 1) else 4.6 + 0.55 * len(net)
    tx, ty = x + d[0] * off, y + d[1] * off - (0.9 if d[1] == 0 else 0)
    # hide the value text if a same-net symbol pointing the same way sits right next to this one
    hide = any(n == net and dd == d and (abs(xx - x) < 7 and abs(yy - y) < 0.1 if d[0] == 0 else
                                         abs(yy - y) < 4 and abs(xx - x) < 0.1)
               for (n, xx, yy, dd) in _placed_pwr)
    _placed_pwr.append((net, x, y, d))
    if net == "GND" and d[1] == 0:
        hide = True   # sideways GND: the symbol shape is enough, text only clutters
    fang = 90 if th in (90, 270) else 0
    place_symbol(lib_id, ref, net, x, y, th,
                 props_pos={"Value": (tx, ty, None, hide, fang), "Reference": (x, y, None, True)})


def terminal(net, x, y, d):
    if net in POWER_NETS:
        power_symbol(net, x, y, d)
    else:
        label(net, x, y, d)


def part(lib_id, ref, value, x, y, rot=0, fp="", nets=None, nc=(), props_pos=None, ds=None, desc=None, stub=STUB):
    """Place a part, then attach every pin to its net via a stub + label/power symbol."""
    nets = dict(nets or {})
    x, y = g(x), g(y)
    if ref in NO_LCSC:
        lc, mpn = "", ""
    elif ref in LCSC_REF:
        lc, mpn = LCSC_REF[ref]
    elif (_cur_kind[0], value) in LCSC_PASSIVE:
        lc, mpn = LCSC_PASSIVE[(_cur_kind[0], value)]
    else:
        raise SystemExit(f"{ref} {value}: no LCSC entry")
    _cur_kind[0] = None
    ls = place_symbol(lib_id, ref, value, x, y, rot, fp, props_pos=props_pos,
                      extra_props={"LCSC": lc, "MPN": mpn}, ds=ds, desc=desc)
    pins = pins_of(ls)
    allnums = {p['number'] for p in pins}
    for n in list(nets) + list(nc):
        if n not in allnums:
            raise SystemExit(f"{ref}: pin {n} not in symbol {lib_id}")
    missing = allnums - set(nets) - set(nc)
    if missing:
        raise SystemExit(f"{ref}: pins not assigned: {sorted(missing)}")
    expected[ref] = {n: v for n, v in nets.items()}
    for n in nc:
        expected[ref][n] = None
    # group by location
    locs = {}
    for p in pins:
        ox, oy = rot_vec(p['x'], p['y'], rot)
        key = (round(x + ox, 3), round(y + oy, 3))
        locs.setdefault(key, []).append(p)
    for (px, py), plist in locs.items():
        targets = {nets.get(p['number'], None) for p in plist}
        if len(targets) != 1:
            raise SystemExit(f"{ref}: stacked pins {[p['number'] for p in plist]} map to different nets {targets}")
        net = targets.pop()
        if net is None:
            no_connect(px, py)
            continue
        p = plist[0]
        ix, iy = rot_vec(math.cos(math.radians(p['rot'])), math.sin(math.radians(p['rot'])), rot)
        d = (-round(ix), -round(iy))
        ex, ey = px + d[0] * stub, py + d[1] * stub
        wire(px, py, ex, ey)
        terminal(net, ex, ey, d)


def passive(kind, ref, value, x, y, n1, n2, fp=None, rot=90):
    """2-pin passive drawn horizontally (pin1 left, pin2 right)."""
    lib = {"R": "Device:R", "C": "Device:C", "CP": "Device:C_Polarized", "L": "Device:L",
           "FB": "Device:FerriteBead", "LED": "Device:LED", "D": "Diode:SS34", "TVS": "Device:D_Zener"}[kind]
    if fp is None:
        fp = {"R": FP_R, "C": FP_C, "LED": FP_LED, "FB": FP_FB}[kind]
    if kind in ("LED", "D", "TVS"):
        rot = 0   # K(1) left, A(2) right already
    fa = 90 if rot in (90, 270) else 0
    pp = {"Reference": (g(x) - 1.0, g(y) - 2.6, "left" if fa else "right", False, fa),
          "Value": (g(x) + 1.0, g(y) - 2.6, "right" if fa else "left", False, fa)}
    _cur_kind[0] = kind
    part(lib, ref, value, x, y, rot, fp, nets={"1": n1, "2": n2}, props_pos=pp)


def note(txt, x, y, size=2.0, bold=True, face=None):
    eff = text_effects(size=size, justify="left bottom", bold=bold)
    if face:   # TrueType face, e.g. for Hangul (KiCad's stroke font has no Hangul glyphs)
        eff[1].insert(1, [Sym('face'), face])
    items.append([Sym('text'), txt, [Sym('exclude_from_sim'), Sym('no')], [Sym('at'), x, y, 0],
                  eff, [Sym('uuid'), uid('txt')]])


def box(x1, y1, x2, y2):
    items.append([Sym('rectangle'), [Sym('start'), x1, y1], [Sym('end'), x2, y2],
                  [Sym('stroke'), [Sym('width'), 0.15], [Sym('type'), Sym('dash')]],
                  [Sym('fill'), [Sym('type'), Sym('none')]], [Sym('uuid'), uid('box')]])


def group(title, x1, y1, x2, y2, sub=None):
    box(x1, y1, x2, y2)
    note(title, x1 + 1.27, y1 + 3.81)
    if sub:
        note(sub, x1 + 1.27, y1 + 7.0, size=1.27, bold=False)


def pwr_flag(net, x, y):
    x, y = g(x), g(y)
    flg_count[0] += 1
    ref = "#FLG%02d" % flg_count[0]
    place_symbol("power:PWR_FLAG", ref, "PWR_FLAG", x, y, 0,
                 props_pos={"Reference": (x, y, None, True), "Value": (x, y - 3.2, None, False)})
    wire(x, y, x, y + STUB)
    terminal(net, x, y + STUB, (0, 1))
    expected.setdefault("#FLAGS", {})[ref] = net


# ================================================================= the design
def column(x, y0, specs, dy=7.62):
    y = y0
    for s in specs:
        passive(*s[:1], *s[1:3], x, y, *s[3:])
        y += dy


def build():
    # ------------------------------------------------------------ A: USB-C input
    group("USB-C input", 12, 22, 92, 112, "J2 USB-C (sink, 5.1k CC pulldowns)")
    part("Connector:USB_C_Receptacle_USB2.0_16P", "J2", "USB_C_Receptacle_USB2.0_16P", 32, 62, 0,
         "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
         nets={"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A5": "CC1", "B5": "CC2",
               "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND"},
         nc=["A6", "B6", "A7", "B7", "A8", "B8"])
    column(76, 40, [("R", "R1", "5.1k", "CC1", "GND"),
                    ("R", "R2", "5.1k", "CC2", "GND"),
                    ("C", "C1", "10uF", "VBUS", "GND", FP_C08),
                    ("TVS", "D4", "SMAJ5.0A", "VBUS", "GND", "Diode_SMD:D_SMA")], dy=10.16)
    note("D4 (2026-11-08 2nd): VBUS TVS, K=VBUS A=GND", 60, 86, size=1.0, bold=False)

    # ------------------------------------------------------------ B: charger
    group("Charger TP4056 + charge inhibit", 96, 22, 196, 112,
          "PROG 1.2k = ~1A (0.2C, >=5000mAh). GPIO25 CHG_DIS HIGH = charge OFF; LOW/float = ON")
    part("Battery_Management:TP4056-42-ESOP8", "U1", "TP4056", 128, 52, 0,
         "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm_ThermalVias",
         nets={"4": "VBUS", "5": "BAT+", "2": "PROG", "1": "GND", "3": "GND", "9": "GND",
               "7": "CHRG_N", "6": "STDBY_N", "8": "CHG_CE"})
    part("Transistor_FET:2N7002", "Q2", "2N7002", 128, 92, 0, "Package_TO_SOT_SMD:SOT-23",
         nets={"3": "CHG_CE", "2": "GND", "1": "CHG_DIS"})
    column(176, 34, [("C", "C2", "10uF", "VBUS", "GND", FP_C08),
                     ("C", "C3", "10uF", "BAT+", "GND", FP_C08),
                     ("R", "R3", "1.2k", "PROG", "GND"),
                     ("R", "R4", "1k", "VBUS", "LED_CHRG_A"),
                     ("LED", "D2", "RED", "CHRG_N", "LED_CHRG_A"),
                     ("R", "R5", "1k", "VBUS", "LED_STDBY_A"),
                     ("LED", "D3", "WHITE", "STDBY_N", "LED_STDBY_A"),
                     ("R", "R6", "10k", "CHG_CE", "VBUS"),
                     ("R", "R7", "100k", "CHG_DIS", "GND")], dy=8.89)

    # ------------------------------------------------------------ C: load sharing
    group("Load sharing", 200, 22, 262, 112, "VBUS present: Q1 OFF, SYS from USB via D1")
    passive("D", "D1", "SS34", 230, 42, "SYS", "VBUS", fp="Diode_SMD:D_SMA")
    part("Transistor_FET:AO3401A", "Q1", "AO3401A", 228, 68, 0, "Package_TO_SOT_SMD:SOT-23",
         nets={"2": "SYS", "3": "BAT+", "1": "VBUS"})
    passive("R", "R10", "100k", 230, 90, "VBUS", "GND")
    passive("R", "R24", "10k", 230, 102, "VBUS", "GND")
    note("R24: VBUS pull-down vs SS34 leakage (2026-11-08 2nd)", 203, 109, size=1.0, bold=False)

    # ------------------------------------------------------------ D: protection
    group("Battery protection DW01A + WSP8814", 266, 22, 408, 112,
          "B- = cell negative; system GND = P-. OC trip ~150mV / (2 x Rds): ~4.6-12 A")
    part("Connector_Generic:Conn_01x02", "J3", "BAT", 290, 40, 0,
         "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", nets={"1": "BAT+", "2": "B-"})
    for i, line in enumerate(["J3 JST XH 3A (2026-11-08 2nd): crimp the battery lead",
                              "with + on pin 1. NO reverse-polarity protection."]):
        note(line, 270, 50 + i * 2.6, size=1.0, bold=False)
    part("Battery_Management:DW01A", "U2", "DW01A", 296, 78, 0, "Package_TO_SOT_SMD:SOT-23-6",
         nets={"5": "DW_VCC", "6": "B-", "2": "DW_CS", "1": "OD", "3": "OC"}, nc=["4"])
    part(f"{CUSTOM_LIB}:WSP8814", "U3", "WSP8814", 346, 78, 0, "Package_SO:TSSOP-8_4.4x3mm_P0.65mm",
         nets={"1": "FET_D", "8": "FET_D", "2": "B-", "3": "B-", "4": "OD", "5": "OC", "6": "GND", "7": "GND"})
    column(388, 36, [("R", "R8", "100", "BAT+", "DW_VCC"),
                     ("C", "C4", "0.1uF", "DW_VCC", "B-"),
                     ("R", "R9", "1k", "DW_CS", "GND")], dy=10.16)

    # ------------------------------------------------------------ E: boost
    group("Boost 5V TPS61023", 12, 118, 128, 200,
          "FB 510k/68k -> 5.06V, CFF C26 330pF (TI 8.2.2.4). J4 = power switch")
    part(f"{CUSTOM_LIB}:TPS61023", "U4", "TPS61023", 40, 148, 0, "Package_TO_SOT_SMD:SOT-563",
         nets={"3": "SYS", "4": "GND", "5": "SW", "6": "+5V", "1": "FB", "2": "BST_EN"})
    part("Connector_Generic:Conn_01x03", "J4", "PWR_SW", 40, 180, 0,
         "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
         nets={"1": "SYS", "2": "BST_EN", "3": "GND"})
    column(98, 130, [("C", "C5", "10uF", "SYS", "GND", FP_C08),
                     ("L", "L1", "1uH", "SW", "SYS", "Inductor_SMD:L_Changjiang_FXL0420"),
                     ("C", "C6", "22uF", "+5V", "GND", FP_C08),
                     ("C", "C7", "22uF", "+5V", "GND", FP_C08),
                     ("CP", "C8", "220uF", "+5V", "GND", "Capacitor_SMD:CP_Elec_6.3x7.7"),
                     ("R", "R11", "510k", "+5V", "FB"),
                     ("R", "R12", "68k", "FB", "GND"),
                     ("R", "R13", "100k", "BST_EN", "GND")], dy=8.89)
    passive("C", "C27", "22uF", 74, 136, "SYS", "GND", fp=FP_C08)      # 2026-11-08 2nd: extra boost input cap
    passive("C", "C26", "330pF", 74, 168, "+5V", "FB")                  # 2026-11-08 2nd: feedforward across R11

    # ------------------------------------------------------------ F: ADC
    group("Voltage sense ADS1115 (0x48)", 132, 118, 246, 200, "A0 = BAT+/2, A1 = VBUS/2")
    column(152, 132, [("R", "R14", "100k", "BAT+", "VBAT_SENSE"),
                      ("R", "R15", "100k", "VBAT_SENSE", "GND"),
                      ("C", "C9", "100nF", "VBAT_SENSE", "GND"),
                      ("R", "R16", "100k", "VBUS", "VBUS_SENSE"),
                      ("R", "R17", "100k", "VBUS_SENSE", "GND"),
                      ("C", "C10", "100nF", "VBUS_SENSE", "GND"),
                      ("C", "C11", "0.1uF", "+3V3", "GND")], dy=8.89)
    part("Analog_ADC:ADS1115IDGS", "U5", "ADS1115IDGS", 214, 158, 0, "Package_SO:TSSOP-10_3x3mm_P0.5mm",
         nets={"8": "+3V3", "3": "GND", "9": "SDA", "10": "SCL", "1": "GND",
               "4": "VBAT_SENSE", "5": "VBUS_SENSE"}, nc=["2", "6", "7"])

    # ------------------------------------------------------------ G: Pi header
    group("Raspberry Pi 40-pin header", 250, 118, 408, 200, "Right-angle 2x20 (Pi Zero 2W side-by-side)")
    gnd = {n: "GND" for n in ["6", "9", "14", "20", "25", "30", "34", "39"]}
    pinets = {"1": "+3V3", "17": "+3V3", "2": "+5V", "4": "+5V", "3": "SDA", "5": "SCL",
              "12": "I2S_BCLK", "35": "I2S_LRCLK", "40": "I2S_DIN",
              "19": "LCD_DIN", "23": "LCD_CLK", "37": "LCD_CS", "33": "LCD_DC", "31": "LCD_RST", "32": "LCD_BL",
              "11": "ENC_S1", "13": "ENC_S2", "15": "ENC_KEY", "16": "HP_DET", "18": "AMP_SD", "22": "CHG_DIS"}
    pinets.update(gnd)
    part("Connector:Raspberry_Pi_4", "J1", "Raspberry_Pi_40pin", 328, 158, 0,
         f"{CUSTOM_LIB}:PinHeader_2x20_P2.54mm_Horizontal_PiSide",
         props_pos={"Reference": (296, 128, "left", False), "Value": (340, 189, "left", False)},
         nets=pinets, nc=["7", "8", "10", "21", "24", "26", "27", "28", "29", "36", "38"])

    # ------------------------------------------------------------ H: DAC + jack
    group("Headphone DAC PCM5102A + jack", 12, 206, 196, 283,
          "I2S slave, SCK=GND (PLL from BCK). Jack PJ-307C, insertion detect via tip NC switch (see note)")
    part("Audio:PCM5102A", "U6", "PCM5102A", 42, 246, 0, "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
         nets={"8": "+3V3", "20": "+3V3", "1": "+3V3", "9": "GND", "19": "GND", "3": "GND",
               "2": "CAPP", "4": "CAPM", "5": "VNEG", "18": "LDOO",
               "13": "I2S_BCLK", "15": "I2S_LRCLK", "14": "I2S_DIN", "12": "GND",
               "16": "GND", "10": "GND", "11": "GND", "17": "XSMT", "6": "DAC_L", "7": "DAC_R"})
    column(96, 218, [("C", "C12", "0.1uF", "+3V3", "GND"),
                     ("C", "C13", "0.1uF", "+3V3", "GND"),
                     ("C", "C14", "0.1uF", "+3V3", "GND"),
                     ("C", "C15", "10uF", "+3V3", "GND", FP_C08),
                     ("C", "C16", "2.2uF", "CAPP", "CAPM"),
                     ("C", "C17", "2.2uF", "VNEG", "GND"),
                     ("C", "C18", "2.2uF", "LDOO", "GND")], dy=8.89)
    column(140, 218, [("R", "R18", "10k", "XSMT", "+3V3"),
                      ("R", "R19", "100", "DAC_L", "HP_L"),
                      ("R", "R20", "100", "DAC_R", "HP_R"),
                      ("C", "C19", "2.2nF", "HP_L", "GND"),
                      ("C", "C20", "2.2nF", "HP_R", "GND")], dy=8.89)
    # PJ-307C: 1=S 2=R 3=RN 4=TN 5=T (datasheet pin numbers = symbol pin numbers = footprint pads)
    part(f"{CUSTOM_LIB}:PJ-307C", "J8", "PJ-307C", 174, 224, 0,
         f"{CUSTOM_LIB}:Jack_3.5mm_PJ-307C_Horizontal",
         nets={"1": "GND", "5": "HP_L", "4": "HP_TN", "2": "HP_R"}, nc=["3"])
    passive("R", "R23", "4.7k", 170, 248, "HP_TN", "HP_DET")
    passive("C", "C25", "22uF", 170, 257, "HP_DET", "GND", fp=FP_C08)
    for i, line in enumerate([
            "HP_DET (2026-11-08, 2nd): J8 pin 4 (tip NC) -4.7k- HP_DET",
            "(GPIO23, Pi pin 16), 22uF to GND. No external pull-up:",
            "the Pi internal pull-up is used, as the software does now.",
            "No plug: tip touches pin 4, HP_DET sees the ground-centred DAC",
            "output low-passed (tau ~100 ms), DC = 3.3 x 4.7/(4.7+50) ~ 0.28 V -> LOW.",
            "Plug in: contact opens -> pull-up -> HIGH (HIGH = inserted)."]):
        note(line, 117, 264 + i * 3.0, size=1.27, bold=False)

    # ------------------------------------------------------------ I: amp
    group("Speaker amp MAX98357A", 200, 206, 300, 283,
          "SD_MODE: GPIO24 10k / 1.8k -> ~0.50V = (L+R)/2 mono. Gain: open 9dB, A=6dB, B=12dB")
    part("Audio:MAX98357A", "U7", "MAX98357A", 232, 240, 0,
         "Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm",
         nets={"7": "+5V", "8": "+5V", "3": "GND", "11": "GND", "15": "GND", "17": "GND",
               "1": "I2S_DIN", "16": "I2S_BCLK", "14": "I2S_LRCLK", "2": "GAIN_SLOT", "4": "SD_MODE",
               "9": "AMP_OUTP", "10": "AMP_OUTN"}, nc=["5", "6", "12", "13"])
    part("Jumper:SolderJumper_3_Open", "JP1", "GAIN", 250, 262, 0,
         "Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm",
         nets={"1": "+5V", "2": "GAIN_SLOT", "3": "GND"})
    note("JP1: 한쪽만 브리지할 것 — 양쪽 다 브리지하면 5V–GND 단락", 202, 277, size=1.2, bold=False,
         face="Apple SD Gothic Neo")
    note("(JP1: bridge ONE side only; both sides = 5V-GND short)", 202, 280.5, size=1.0, bold=False)
    column(284, 216, [("C", "C21", "10uF", "+5V", "GND", FP_C08),
                      ("C", "C22", "0.1uF", "+5V", "GND"),
                      ("R", "R21", "10k", "AMP_SD", "SD_MODE"),
                      ("R", "R22", "1.8k", "SD_MODE", "GND"),
                      ("FB", "FB1", "FerriteBead", "AMP_OUTP", "SPK+"),
                      ("FB", "FB2", "FerriteBead", "AMP_OUTN", "SPK-"),
                      ("C", "C23", "220pF", "SPK+", "GND"),
                      ("C", "C24", "220pF", "SPK-", "GND")], dy=8.0)
    part("Connector_Generic:Conn_01x02", "J7", "SPK", 266, 272, 0,
         "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", nets={"1": "SPK-", "2": "SPK+"})

    # ------------------------------------------------------------ J: connectors / flags / holes
    group("LCD / encoder / PWR_FLAG / holes", 304, 206, 408, 250)
    part("Connector_Generic:Conn_01x08", "J5", "LCD", 330, 236, 0,
         "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
         nets={"1": "LCD_BL", "2": "LCD_RST", "3": "LCD_DC", "4": "LCD_CS", "5": "LCD_CLK", "6": "LCD_DIN",
               "7": "GND", "8": "+5V"})
    part("Connector_Generic:Conn_01x05", "J6", "ENC", 362, 236, 0,
         "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
         nets={"1": "+3V3", "2": "ENC_KEY", "3": "ENC_S2", "4": "ENC_S1", "5": "GND"})
    for i, line in enumerate(["J6 VCC = +3V3 (2026-11-08):", "encoder module pull-ups go to", "its VCC; 5V would overdrive",
                              "the 3.3V-only Pi GPIOs."]):
        note(line, 370, 239.5 + i * 2.4, size=1.0, bold=False)
    for i in range(5):
        ref = f"H{i + 1}"
        place_symbol("Mechanical:MountingHole", ref, "MountingHole", g(382 + (i % 3) * 9), g(222 + (i // 3) * 12), 0,
                     "MountingHole:MountingHole_2.7mm_M2.5",
                     props_pos={"Reference": (382 + (i % 3) * 9, 218 + (i // 3) * 12, None, False),
                                "Value": (382 + (i % 3) * 9, 222 + (i // 3) * 12, None, True)},
                     extra_props={"LCSC": "", "MPN": ""})
    # BAT+, +5V, +3V3, GND are already driven by power_out pins (TP4056 BAT, Pi 5V/3V3/GND);
    # a PWR_FLAG there is a power_out-power_out ERC error, so those flags are omitted.
    flag_nets = ["VBUS", "B-", "SYS", "DW_VCC"]
    for i, n in enumerate(flag_nets):
        pwr_flag(n, 312 + i * 15, 216)


NETCLASS_JSON = os.path.join(HERE, "..", "v08board", "netclasses.json")
# board design_settings.rules from the `notes` field of netclasses.json
BOARD_RULES = {"min_track_width": 0.15, "min_clearance": 0.15, "min_via_diameter": 0.6,
               "min_through_hole_diameter": 0.3, "min_via_annular_width": 0.15, "min_hole_to_hole": 0.5,
               "min_copper_edge_clearance": 0.3, "min_silk_clearance": 0.15}


def merge_netclasses(tpl):
    nc = json.load(open(NETCLASS_JSON))
    ns = tpl['net_settings']
    base = next(c for c in ns['classes'] if c['name'] == 'Default')
    classes, patterns = [], []
    for prio, c in enumerate(nc['classes']):
        d = dict(base)
        d.update({k: v for k, v in c.items() if k != 'nets'})
        if c['name'] != 'Default':
            d['priority'] = prio
            for n in c.get('nets', []):
                # power-symbol nets are bare ("GND"); label nets on the root sheet are "/NAME" -> match both
                patterns += [{"netclass": c['name'], "pattern": n}, {"netclass": c['name'], "pattern": "/" + n}]
        classes.append(d)
    ns['classes'] = classes
    ns['netclass_patterns'] = patterns
    tpl['board']['design_settings']['rules'].update(BOARD_RULES)


def write_fp_lib_table():
    with open(f"{OUTDIR}/fp-lib-table", "w") as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "%s") (type "KiCad") (uri "${KIPRJMOD}/%s.pretty") '
                '(options "") (descr "wr-radio HAT v08 custom footprints (PJ-307C jack, Pi-side 2x20 header)"))\n)\n'
                % (PROJ, PROJ))


def write_all():
    write_fp_lib_table()
    os.makedirs(OUTDIR, exist_ok=True)
    build()
    sch = [Sym('kicad_sch'), [Sym('version'), Sym('20260306')], [Sym('generator'), "eeschema"],
           [Sym('generator_version'), "10.0"], [Sym('uuid'), ROOT_UUID], [Sym('paper'), "A3"],
           [Sym('title_block'), [Sym('title'), "wr-radio HAT v08"], [Sym('date'), "2026-11-08"],
            [Sym('rev'), "v08"], [Sym('comment'), 1, "Generated from PCB/kicad/v08_design_spec.md"]],
           [Sym('lib_symbols')] + list(used_libs.values())]
    sch += items
    sch += [[Sym('sheet_instances'), [Sym('path'), "/", [Sym('page'), "1"]]], [Sym('embedded_fonts'), Sym('no')]]
    with open(f"{OUTDIR}/{PROJ}.kicad_sch", "w", encoding="utf-8") as f:
        f.write(dump(sch) + "\n")

    lib = [Sym('kicad_symbol_lib'), [Sym('version'), Sym('20251024')], [Sym('generator'), "v08gen"],
           [Sym('generator_version'), "10.0"]] + list(CUSTOM.values())
    with open(f"{OUTDIR}/{PROJ}.kicad_sym", "w", encoding="utf-8") as f:
        f.write(dump(lib) + "\n")

    with open(f"{OUTDIR}/sym-lib-table", "w") as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "%s") (type "KiCad") (uri "${KIPRJMOD}/%s.kicad_sym") '
                '(options "") (descr "wr-radio HAT v08 custom symbols (TPS61023, WSP8814, PJ-307C)"))\n)\n' % (PROJ, PROJ))

    tpl = json.load(open(PRO_TEMPLATE))
    tpl['meta']['filename'] = f"{PROJ}.kicad_pro"
    tpl['schematic']['top_level_sheets'] = [{"filename": f"{PROJ}.kicad_sch", "name": PROJ, "uuid": ROOT_UUID}]
    tpl['sheets'] = [[ROOT_UUID, "Root"]]
    merge_netclasses(tpl)
    with open(f"{OUTDIR}/{PROJ}.kicad_pro", "w") as f:
        json.dump(tpl, f, indent=2)

    os.makedirs(WORK, exist_ok=True)
    json.dump(expected, open(os.path.join(WORK, "expected.json"), "w"), indent=1)
    print("parts:", len([k for k in expected if not k.startswith('#')]), "items:", len(items))


if __name__ == "__main__":
    write_all()
