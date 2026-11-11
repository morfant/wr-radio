"""Silk part of fix_9.py (review N9/N10). Re-runnable: removes its own labels (matched by text + area) first.
- J9 debug pads (x 10.5; pin 1 GND y -48.42, 2 UART_TX -45.88, 3 UART_RX -43.34): one label right beside
  each pad on B.SilkS (mirrored; B has only THT pads there). The old F labels GND/TX/RX (TX 4 mm away) are
  deleted: on F the J9 silk box (x to 11.94), R23 (pad x 13.35, ref) and C12 leave no room beside the pads.
- "DO NOT POWER PI VIA USB" along the J1 plug-free strip (F.SilkS, vertical) - HAT feeds Pi 5V via J1.2/4.
"""
import pcbnew

MM = pcbnew.FromMM
J9 = (("GND", -48.42), ("TX", -45.88), ("RX", -43.34))
J9_X0 = 11.55                       # text starts 0.2 mm right of the pad edge (x 11.35)
J9_BOX = (9.0, -53.0, 18.0, -38.0)  # where old/own J9 labels may sit
PI_TXT, PI_AT = "DO NOT POWER PI VIA USB", (12.4, -17.5)


def _text(b, s, layer, x, y, ang=0, mirror=False, w=0.8):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(s); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(w), MM(0.8))); t.SetTextThickness(MM(0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetTextAngleDegrees(ang); t.SetMirrored(mirror); t.SetKeepUpright(False)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    b.Add(t)
    return t


def _in(d, box):
    x, y = pcbnew.ToMM(d.GetX()), pcbnew.ToMM(d.GetY())
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def apply(b):
    names = {s for s, _ in J9}
    for d in list(b.GetDrawings()):
        if d.GetClass() != "PCB_TEXT":
            continue
        if (d.GetText() in names and _in(d, J9_BOX)) or d.GetText() == PI_TXT:
            b.Remove(d)
    for s, y in J9:
        for layer, mir in ((pcbnew.B_SilkS, True),):
            t = _text(b, s, layer, 0, y, 0, mir, 0.65)     # narrow: GND must clear C12.1 (x 14.17)
            w = pcbnew.ToMM(t.GetBoundingBox().GetWidth())
            t.SetPosition(pcbnew.VECTOR2I(MM(J9_X0 + w / 2), MM(y)))
    _text(b, PI_TXT, pcbnew.F_SilkS, PI_AT[0], PI_AT[1], 90)
    print("fix_9_silk: J9 labels on B, Pi warning")
