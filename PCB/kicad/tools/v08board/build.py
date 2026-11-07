"""Build the v08 board TEMPLATE from scratch (outline, holes, J1, GND zone, rules). WARNING: overwrites
radio-hat-v08.kicad_pcb, discarding any layout work. Run with KiCad's python."""
import pcbnew, math
from pcbnew import FromMM as mm, VECTOR2I
import os
HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))           # PCB/kicad
PCB_FILE = os.path.join(KICAD_DIR, "radio-hat-v08", "radio-hat-v08.kicad_pcb")
PRJ_LIB = os.path.join(KICAD_DIR, "radio-hat-v08", "radio-hat-v08.pretty")
V07_BRD = os.path.join(KICAD_DIR, "..", "radio-hat-v07.brd")             # Eagle v07, loaded via KiCad importer
OUT=PCB_FILE
FP="/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
v7=pcbnew.LoadBoard(V07_BRD, pcbnew.PCB_IO_MGR.EAGLE)
b=pcbnew.CreateEmptyBoard()
b.SetCopperLayerCount(2)
# edge cuts
for d in v7.GetDrawings():
    if d.GetLayer()==pcbnew.Edge_Cuts:
        n=pcbnew.PCB_SHAPE(b); n.SetShape(d.GetShape()); n.SetLayer(pcbnew.Edge_Cuts)
        n.SetStart(d.GetStart()); n.SetEnd(d.GetEnd())
        if d.GetShape()==pcbnew.SHAPE_T_ARC:
            n.SetArcGeometry(d.GetStart(),d.GetArcMid(),d.GetEnd())
        n.SetWidth(d.GetWidth()); b.Add(n)
# holes
v7h=["UNK_HOLE_%d"%i for i in range(5)]
for i,r in enumerate(v7h):
    pos=v7.FindFootprintByReference(r).GetPosition()
    f=pcbnew.FootprintLoad(FP+"MountingHole.pretty","MountingHole_2.7mm_M2.5")
    f.SetReference("H%d"%(i+1)); f.SetPosition(pos); f.SetLocked(True); b.Add(f)
# J1
# 2026-11-08: header body on the top side -> project footprint (stock mirrored in X) on F.Cu, Pi pin n = pad n
j=pcbnew.FootprintLoad(PRJ_LIB,"PinHeader_2x20_P2.54mm_Horizontal_PiSide")
j.SetFPID(pcbnew.LIB_ID("radio-hat-v08","PinHeader_2x20_P2.54mm_Horizontal_PiSide"))
j.SetReference("J1"); j.SetValue("Raspberry_Pi_40pin"); b.Add(j)
j.SetPosition(VECTOR2I(mm(6.49),mm(-53.505)))
j.SetLocked(True)
# text
t=pcbnew.PCB_TEXT(b); t.SetText("wr-radio v0.8 (2026.11)"); t.SetLayer(pcbnew.F_SilkS)
t.SetPosition(VECTOR2I(mm(9.5),mm(2))); t.SetTextSize(VECTOR2I(mm(1.308608),mm(1.308608)))
t.SetTextThickness(mm(0.113792)); t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_BOTTOM); b.Add(t)
# title block
tb=pcbnew.TITLE_BLOCK(); tb.SetTitle("wr-radio HAT v08"); tb.SetDate("2026-11"); tb.SetRevision("v0.8"); b.SetTitleBlock(tb)
# design settings
ds=b.GetDesignSettings()
ds.m_TrackMinWidth=mm(0.15); ds.m_MinClearance=mm(0.15)
ds.m_ViasMinSize=mm(0.6); ds.m_MinThroughDrill=mm(0.3); ds.m_ViasMinAnnulus=mm(0.15)
ds.m_HoleToHoleMin=mm(0.5); ds.m_CopperEdgeClearance=mm(0.3); ds.m_SilkClearance=mm(0.15)
ds.m_CurrentViaSize=mm(0.6); ds.m_CurrentViaDrill=mm(0.3); ds.m_TrackWidthList=[0, mm(0.25),mm(0.3),mm(0.6)] if False else ds.m_TrackWidthList
try:
    sd=ds.GetStackupDescriptor()
    for it in sd.GetList():
        if it.GetType()==pcbnew.BS_ITEM_TYPE_COPPER:
            it.SetThickness(mm(0.035))
    ds.m_HasStackup=True
except Exception as e: print("stackup",e)
# GND net + zone
gnd=pcbnew.NETINFO_ITEM(b,"GND"); b.Add(gnd)
z=pcbnew.ZONE(b); z.SetLayer(pcbnew.B_Cu); z.SetNet(gnd)
ins=0.3; x0,x1,y0,y1,r=0+ins,63.48-ins,-64.9+ins,5.08-ins,4-ins
pts=[]
for cx,cy,a0 in [(x1-r,y0+r,-90),(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180)]:
    for k in range(0,10):
        a=math.radians(a0+9*k); pts.append((cx+r*math.cos(a),cy+r*math.sin(a)))
ch=pcbnew.SHAPE_LINE_CHAIN()
for x,y in pts: ch.Append(mm(x),mm(y))
ch.SetClosed(True)
z.Outline().AddOutline(ch)
z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(OUT)
