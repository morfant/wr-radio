import pcbnew
"""Check v08 board J1 pads and mounting holes against v07. Run with KiCad's python:
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 chk.py"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))           # PCB/kicad
PCB_FILE = os.path.join(KICAD_DIR, "radio-hat-v08", "radio-hat-v08.kicad_pcb")
PRJ_LIB = os.path.join(KICAD_DIR, "radio-hat-v08", "radio-hat-v08.pretty")
V07_BRD = os.path.join(KICAD_DIR, "..", "radio-hat-v07.brd")             # Eagle v07, loaded via KiCad importer
v7=pcbnew.LoadBoard(V07_BRD, pcbnew.PCB_IO_MGR.EAGLE)
b=pcbnew.LoadBoard(PCB_FILE)
j7=v7.FindFootprintByReference("J1"); j8=b.FindFootprintByReference("J1")
# pi pin n -> v07 eagle pad: odd n->n+1, even n->n-1
mx=0
for n in range(1,41):
    e=n+1 if n%2 else n-1
    a=[p for p in j7.Pads() if p.GetNumber()==str(e)][0].GetPosition()
    c=[p for p in j8.Pads() if p.GetNumber()==str(n)][0].GetPosition()
    d=((a.x-c.x)**2+(a.y-c.y)**2)**.5/1e6; mx=max(mx,d)
    if n in(1,2,3,39,40): print(n,e,a.x/1e6,a.y/1e6,c.x/1e6,c.y/1e6, [p for p in j7.Pads() if p.GetNumber()==str(e)][0].GetNetname())
print("max err mm",mx, "layer",j8.GetLayerName(),j8.IsLocked(), j8.GetOrientationDegrees())
for i in range(5):
    a=v7.FindFootprintByReference("UNK_HOLE_%d"%i).GetPosition(); c=b.FindFootprintByReference("H%d"%(i+1)).GetPosition()
    print("H%d"%(i+1),a.x/1e6,a.y/1e6,c.x/1e6,c.y/1e6,b.FindFootprintByReference("H%d"%(i+1)).IsLocked())
print(b.GetBoardEdgesBoundingBox().GetWidth()/1e6,b.GetBoardEdgesBoundingBox().GetHeight()/1e6, v7.GetBoardEdgesBoundingBox().GetWidth()/1e6)
