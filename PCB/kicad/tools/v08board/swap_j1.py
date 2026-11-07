"""Replace J1 (stock header flipped to B.Cu) with radio-hat-v08:PinHeader_2x20_P2.54mm_Horizontal_PiSide on F.Cu."""
import pcbnew
from pcbnew import FromMM as mm, VECTOR2I
import os
HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))           # PCB/kicad
PCB_FILE = os.path.join(KICAD_DIR, "radio-hat-v08", "radio-hat-v08.kicad_pcb")
PRJ_LIB = os.path.join(KICAD_DIR, "radio-hat-v08", "radio-hat-v08.pretty")
V07_BRD = os.path.join(KICAD_DIR, "..", "radio-hat-v07.brd")             # Eagle v07, loaded via KiCad importer
PCB = PCB_FILE
LIB = PRJ_LIB
b = pcbnew.LoadBoard(PCB)
old = b.FindFootprintByReference("J1")
print("old", old.GetFPID().GetUniStringLibItemName(), old.GetLayerName(), old.GetOrientationDegrees())
b.Remove(old)
j = pcbnew.FootprintLoad(LIB, "PinHeader_2x20_P2.54mm_Horizontal_PiSide")
j.SetFPID(pcbnew.LIB_ID("radio-hat-v08", "PinHeader_2x20_P2.54mm_Horizontal_PiSide"))
j.SetReference("J1"); j.SetValue("Raspberry_Pi_40pin")
j.SetPosition(VECTOR2I(mm(6.49), mm(-53.505)))
j.SetLocked(True)
b.Add(j)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PCB)
print("new", j.GetFPID().GetUniStringLibItemName(), j.GetLayerName(), j.GetOrientationDegrees(), j.IsLocked())
