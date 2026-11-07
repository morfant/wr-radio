import sys; sys.path.insert(0,'.')
from sexp import *
for lib,name in [("Connector","Raspberry_Pi_4"),("Audio","MAX98357A"),("Audio","PCM5102A"),("Analog_ADC","ADS1115IDGS"),("Battery_Management","TP4056-42-ESOP8"),("Battery_Management","DW01A"),("Transistor_FET","AO3401A"),("Transistor_FET","2N7002"),("Diode","SS34"),("Connector","USB_C_Receptacle_USB2.0_16P"),("Connector_Audio","AudioJack3_Ground_Switch"),("Jumper","SolderJumper_3_Open"),("Device","R"),("Device","C"),("Device","LED"),("Device","FerriteBead"),("Device","C_Polarized"),("Device","L"),("Connector_Generic","Conn_01x02"),("power","GND"),("power","PWR_FLAG"),("power","VBUS"),("power","+5V"),("Mechanical","MountingHole")]:
    s=flatten(lib,name)
    fp=[p[2] for p in findall(s,'property') if p[1]=='Footprint']
    print(f"== {lib}:{name} fp={fp}")
    for p in pins_of(s):
        print("  ",p['number'],p['name'],p['x'],p['y'],p['rot'],p['type'],'U%d'%p['unit'],'H' if p['hidden'] else '')
