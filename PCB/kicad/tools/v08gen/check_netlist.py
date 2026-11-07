"""Check exported netlist against (1) generator intent (expected.json) and (2) hand-written spec assertions."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, find, findall
D = os.environ.get("V08_WORK", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build"))  # net.net + expected.json
net = parse(open(f"{D}/net.net").read())
pin2net, nets = {}, {}
for n in findall(find(net, 'nets'), 'net'):
    name = find(n, 'name')[1].lstrip('/')
    for nd in findall(n, 'node'):
        r, p = find(nd, 'ref')[1], find(nd, 'pin')[1]
        pin2net[(r, p)] = name
        nets.setdefault(name, set()).add((r, p))
# component field check
comps = {find(c, 'ref')[1]: c for c in findall(find(net, 'components'), 'comp')}
bad = 0
for r, c in comps.items():
    fp = find(c, 'footprint')
    fields = {find(f, 'name')[1]: (f[2] if len(f) > 2 else '') for f in findall(find(c, 'fields') or [], 'field')}
    if not fp or not fp[1]:
        print("NO FOOTPRINT", r); bad += 1
    if 'LCSC' not in fields:
        print("NO LCSC FIELD", r); bad += 1
def val(r):
    return find(comps[r], 'value')[1]
def fpof(r):
    f = find(comps[r], 'footprint'); return f[1] if f else ""
def fld(r, name):
    for f in findall(find(comps[r], 'fields') or [], 'field'):
        if find(f, 'name')[1] == name:
            return f[2] if len(f) > 2 else ""
    return ""
exp = json.load(open(f"{D}/expected.json"))
for ref, pins in exp.items():
    if ref.startswith('#'):
        continue
    for p, want in pins.items():
        got = pin2net.get((ref, p))
        if want is None:
            if got and not got.startswith('unconnected-') and len(nets[got]) > 1:
                print("NC pin connected", ref, p, got); bad += 1
        elif got != want:
            print("MISMATCH", ref, p, "want", want, "got", got); bad += 1
# single-pin nets (label typos)
for n, s in nets.items():
    if len(s) < 2 and not n.startswith('unconnected-'):
        print("single-node net", n, s); bad += 1
print("intent check:", "OK" if bad == 0 else f"{bad} problems", "| components:", len(comps), "| nets:", len(nets))

# ---- spec assertions (independent of generator tables)
def same(*rp):
    ns = {pin2net.get(x) for x in rp}
    return len(ns) == 1 and None not in ns
def on(netname, *rp):
    return all(pin2net.get(x) == netname for x in rp)
def two(ref, a, b):  # 2-pin part between nets a and b
    return {pin2net.get((ref, '1')), pin2net.get((ref, '2'))} == {a, b}
A = []
def chk(desc, ok): A.append((desc, ok))
chk("GPIO25 Pi22 -> Q2(2N7002) gate", same(("J1", "22"), ("Q2", "1")))
chk("Q2 D=TP4056 CE, S=GND", same(("Q2", "3"), ("U1", "8")) and on("GND", ("Q2", "2")))
chk("CE 10k pullup to VBUS (R6)", two("R6", pin2net[("U1", "8")], "VBUS") and comps["R6"] and True)
chk("Q2 gate 100k pulldown (R7)", two("R7", pin2net[("Q2", "1")], "GND"))
for pi, dac, amp, nm in [("12", "13", "16", "BCLK"), ("35", "15", "14", "LRCLK"), ("40", "14", "1", "DIN")]:
    chk(f"I2S {nm}: Pi{pi} = PCM5102A {dac} = MAX98357A {amp}", same(("J1", pi), ("U6", dac), ("U7", amp)))
chk("I2C SDA Pi3 = ADS SDA9; SCL Pi5 = ADS SCL10", same(("J1", "3"), ("U5", "9")) and same(("J1", "5"), ("U5", "10")))
chk("ADS ADDR=GND, VDD=+3V3", on("GND", ("U5", "1"), ("U5", "3")) and on("+3V3", ("U5", "8"), ("J1", "1"), ("J1", "17")))
chk("VBAT divider R14 100k BAT+/R15 100k GND -> AIN0, 100nF C9", two("R14", "BAT+", pin2net[("U5", "4")]) and two("R15", pin2net[("U5", "4")], "GND") and val("R14") == val("R15") == "100k" and fld("R14", "LCSC") == "C25803" and two("C9", pin2net[("U5", "4")], "GND"))
chk("VBUS divider R16 100k VBUS/R17 100k GND -> AIN1, 100nF C10", two("R16", "VBUS", pin2net[("U5", "5")]) and two("R17", pin2net[("U5", "5")], "GND") and val("R16") == val("R17") == "100k" and two("C10", pin2net[("U5", "5")], "GND"))
chk("WSP8814 S1(2,3)=B-, G1(4)=DW01A OD, D1(1)=D2(8), G2(5)=DW01A OC, S2(6,7)=GND",
    on("B-", ("U3", "2"), ("U3", "3"), ("U2", "6"), ("J3", "2")) and same(("U3", "4"), ("U2", "1")) and same(("U3", "1"), ("U3", "8"))
    and same(("U3", "5"), ("U2", "3")) and on("GND", ("U3", "6"), ("U3", "7")) and len(nets[pin2net[("U3", "1")]]) == 2)
chk("DW01A VCC via 100R from BAT+, 0.1uF to B-, CS via 1k to GND",
    two("R8", "BAT+", pin2net[("U2", "5")]) and two("C4", pin2net[("U2", "5")], "B-") and two("R9", pin2net[("U2", "2")], "GND"))
chk("AO3401A S=SYS D=BAT+ G=VBUS", on("SYS", ("Q1", "2")) and on("BAT+", ("Q1", "3"), ("U1", "5"), ("J3", "1")) and on("VBUS", ("Q1", "1")))
chk("SS34 A=VBUS K=SYS", on("VBUS", ("D1", "2")) and on("SYS", ("D1", "1")))
chk("TP4056 VCC=VBUS, TEMP/GND/EPAD=GND, PROG resistor R3 to GND", on("VBUS", ("U1", "4"), ("J2", "A4")) and on("GND", ("U1", "1"), ("U1", "3"), ("U1", "9")) and two("R3", pin2net[("U1", "2")], "GND"))
chk("CHRG LED: VBUS-1k-LED(A->K)-CHRG", two("R4", "VBUS", pin2net[("D2", "2")]) and same(("D2", "1"), ("U1", "7")))
chk("STDBY LED: VBUS-1k-LED(A->K)-STDBY, WHITE C2290; CHRG LED RED C2286", two("R5", "VBUS", pin2net[("D3", "2")]) and same(("D3", "1"), ("U1", "6")) and val("D3") == "WHITE" and fld("D3", "LCSC") == "C2290" and val("D2") == "RED" and fld("D2", "LCSC") == "C2286")
chk("USB CC1/CC2 5.1k to GND", two("R1", pin2net[("J2", "A5")], "GND") and two("R2", pin2net[("J2", "B5")], "GND"))
chk("TPS61023 VIN=SYS, VOUT=+5V, L1 SW-SYS, EN=J4.2", on("SYS", ("U4", "3"), ("J4", "1")) and on("+5V", ("U4", "6"), ("J1", "2"), ("J1", "4"))
    and two("L1", pin2net[("U4", "5")], "SYS") and same(("U4", "2"), ("J4", "2")) and on("GND", ("J4", "3")))
chk("FB 510k(C23192) +5V-FB, 68k(C23231) FB-GND -> 5.06V; CFF 330pF C0G (C1664) across R11; EN 100k pulldown", two("R11", "+5V", pin2net[("U4", "1")]) and two("R12", pin2net[("U4", "1")], "GND") and two("R13", pin2net[("U4", "2")], "GND") and val("R11") == "510k" and val("R12") == "68k" and fld("R11", "LCSC") == "C23192" and fld("R12", "LCSC") == "C23231" and two("C26", "+5V", pin2net[("U4", "1")]) and val("C26") == "330pF" and fld("C26", "LCSC") == "C1664" and abs(0.595 * (1 + 510 / 68) - 5.06) < 0.01)
chk("C8 220uF polarized + on +5V", on("+5V", ("C8", "1")) and on("GND", ("C8", "2")))
chk("PCM5102A supplies/grounds/config", on("+3V3", ("U6", "8"), ("U6", "20"), ("U6", "1")) and on("GND", *[("U6", p) for p in ["9", "19", "3", "12", "16", "10", "11"]]))
chk("PCM5102A CAPP-CAPM 2.2u, VNEG/LDOO 2.2u to GND, XSMT 10k to +3V3",
    two("C16", pin2net[("U6", "2")], pin2net[("U6", "4")]) and two("C17", pin2net[("U6", "5")], "GND") and two("C18", pin2net[("U6", "18")], "GND") and two("R18", pin2net[("U6", "17")], "+3V3"))
# J8 = PJ-307C, pins = datasheet numbers: 1=S 2=R 3=RN 4=TN 5=T
chk("OUTL-100R-jack T(5), OUTR-100R-jack R(2), 2.2nF each",
    two("R19", pin2net[("U6", "6")], pin2net[("J8", "5")]) and two("R20", pin2net[("U6", "7")], pin2net[("J8", "2")]) and two("C19", pin2net[("J8", "5")], "GND") and two("C20", pin2net[("J8", "2")], "GND"))
chk("Jack sleeve(1)=GND, ring NC(3) unconnected", on("GND", ("J8", "1")) and (pin2net.get(("J8", "3"), "unconnected-").startswith("unconnected-") or len(nets[pin2net[("J8", "3")]]) == 1))
hpdet = pin2net.get(("J1", "16"))
chk("HP detect: J8 pad4(TN) -4.7k(R23)- HP_DET = Pi16(GPIO23); HP_DET -22uF 0805 (C25)- GND; nothing else on HP_DET/TN",
    two("R23", pin2net[("J8", "4")], hpdet) and two("C25", hpdet, "GND") and val("R23") == "4.7k" and val("C25") == "22uF"
    and fld("R23", "LCSC") == "C23162" and fld("C25", "LCSC") == "C45783" and fpof("C25") == "Capacitor_SMD:C_0805_2012Metric"
    and len(nets[hpdet]) == 3 and len(nets[pin2net[("J8", "4")]]) == 2)
chk("J8 footprint = project PJ-307C, LCSC C16684", fpof("J8") == "radio-hat-v08:Jack_3.5mm_PJ-307C_Horizontal" and fld("J8", "LCSC") == "C16684")
chk("MAX98357A VDD=+5V, GND pins, GAIN to JP1 center (A=+5V, B=GND)", on("+5V", ("U7", "7"), ("U7", "8"), ("JP1", "1")) and on("GND", ("U7", "3"), ("U7", "11"), ("U7", "15"), ("U7", "17"), ("JP1", "3")) and same(("U7", "2"), ("JP1", "2")))
chk("SD_MODE: Pi18(GPIO24)-10k-node, node-1.8k(C4177)-GND", two("R21", pin2net[("J1", "18")], pin2net[("U7", "4")]) and two("R22", pin2net[("U7", "4")], "GND") and val("R21") == "10k" and val("R22") == "1.8k" and fld("R22", "LCSC") == "C4177")
chk("Speaker per v07: J7.1 = SPK- (OUTN-FB2), J7.2 = SPK+ (OUTP-FB1), 220pF each", two("FB1", pin2net[("U7", "9")], pin2net[("J7", "2")]) and two("FB2", pin2net[("U7", "10")], pin2net[("J7", "1")]) and on("SPK-", ("J7", "1")) and on("SPK+", ("J7", "2")) and two("C23", pin2net[("J7", "2")], "GND") and two("C24", pin2net[("J7", "1")], "GND"))
# v07 Eagle LCD_CONN: 1=BL 2=RST 3=DC 4=CS 5=CLK 6=DIN 7=GND 8=VCC
chk("LCD J5 1..6 = Pi 32(BL),31(RST),33(DC),37(CS),23(CLK),19(DIN); 7=GND 8=+5V", all(same(("J5", a), ("J1", b)) for a, b in zip("123456", ["32", "31", "33", "37", "23", "19"])) and on("GND", ("J5", "7")) and on("+5V", ("J5", "8")))
chk("ENC J6 2=KEY Pi15, 3=S2 Pi13, 4=S1 Pi11; 1=+3V3 (not 5V) 5=GND", same(("J6", "2"), ("J1", "15")) and same(("J6", "3"), ("J1", "13")) and same(("J6", "4"), ("J1", "11")) and on("+3V3", ("J6", "1")) and on("GND", ("J6", "5")))
chk("J1 footprint = project PiSide 2x20 header", fpof("J1") == "radio-hat-v08:PinHeader_2x20_P2.54mm_Horizontal_PiSide")
chk("U3 = Winsok WSP8814 C148371, TSSOP-8 4.4x3", val("U3") == "WSP8814" and fld("U3", "LCSC") == "C148371" and fpof("U3") == "Package_SO:TSSOP-8_4.4x3mm_P0.65mm")
chk("VBUS 10k pull-down R24 (C25804)", two("R24", "VBUS", "GND") and val("R24") == "10k" and fld("R24", "LCSC") == "C25804")
chk("Boost input: C5 10uF + C27 22uF 0805 on SYS", two("C5", "SYS", "GND") and two("C27", "SYS", "GND") and val("C27") == "22uF" and fpof("C27") == "Capacitor_SMD:C_0805_2012Metric" and fld("C27", "LCSC") == "C45783")
chk("L1 = FXL0420-1R0-MA1 (C53426685) on L_Changjiang_FXL0420, SW-SYS", two("L1", pin2net[("U4", "5")], "SYS") and fld("L1", "LCSC") == "C53426685" and fpof("L1") == "Inductor_SMD:L_Changjiang_FXL0420")
chk("J3 = JST XH B2B-XH-A (C158012), 1=BAT+ 2=B-", fpof("J3") == "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical" and fld("J3", "LCSC") == "C158012" and on("BAT+", ("J3", "1")) and on("B-", ("J3", "2")))
chk("USB TVS D4 SMAJ5.0A (C2925443): K(1)=VBUS, A(2)=GND, D_SMA", on("VBUS", ("D4", "1")) and on("GND", ("D4", "2")) and fld("D4", "LCSC") == "C2925443" and fpof("D4") == "Diode_SMD:D_SMA")
chk("PROG R3 = 1.2k (C22765) -> ~1A", val("R3") == "1.2k" and fld("R3", "LCSC") == "C22765")
tenu = [r for r in comps if r[0] == "C" and val(r) == "10uF"]
chk(f"all 10uF ({','.join(sorted(tenu))}) = C15850 on C_0805", tenu and all(fld(r, "LCSC") == "C15850" and fpof(r) == "Capacitor_SMD:C_0805_2012Metric" for r in tenu))
EXCL = {"J1", "J4", "J5", "J6", "J7", "JP1", "H1", "H2", "H3", "H4", "H5"}
nolcsc = sorted(r for r in comps if r not in EXCL and not fld(r, "LCSC"))
chk(f"every non-excluded part has LCSC (missing: {nolcsc})", not nolcsc)
chk("no part has an empty footprint", all(fpof(r) for r in comps))
chk("Pi GND pins all GND", on("GND", *[("J1", p) for p in ["6", "9", "14", "20", "25", "30", "34", "39"]]))
for r in ["H1", "H2", "H3", "H4", "H5"]:
    chk(f"{r} present", r in comps)
fails = [d for d, ok in A if not ok]
for d, ok in A:
    print(("PASS " if ok else "FAIL ") + d)
print(f"spec assertions: {len(A) - len(fails)}/{len(A)} pass")
