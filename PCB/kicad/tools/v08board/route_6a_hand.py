"""Section 6a: hand-routed signal nets (run with KiCad's python, GUI closed).
BST_EN (R13.1 -> J4.2) along the lane section 1/3 left free:
R13.1 (37.775, -51.5) -> west on y -51.5 (north of the SYS 0.5/0.8 run at y -49.0/-49.5, south of R12/C26)
-> x 30.4 south between the +5V branch (x 29.3, 0.8) and SYS (x 31.5, 0.5) -> y -36.95 west -> J4.2 (27.7, -36.95).
All F.Cu, 0.25 mm, no via.
VBAT_SENSE / VBUS_SENSE (ADC divider midpoints -> U5.4 / U5.5): the dividers sit east of the BAT+ trunk (x 36.9,
then diagonal to (45.9, -27)); U5 is west of it. Midpoints joined on F.Cu (R14.2-R15.1-C9.1, R16.2-R17.1-C10.1;
VBUS_SENSE leaves R16.2 down the 0.75 gap between C9 and R16), then one via each in the strip between the
divider row and the BAT+ diagonal, B.Cu (0.25, ~6.7 + ~7.3 mm) under the trunk corner, via just south of U5.
UART_TX / UART_RX (J1.8 / J1.10 -> J9.2 / J9.3): on B.Cu, pad to pad (all THT, no via), stepping between the J1
rows at y -47.155 / -44.615. This leaves the F.Cu strip between J1 and J9 to SDA/SCL/BCLK, which otherwise
must cross the UART lines (the only F.Cu way from J1.3/J1.5 to the board interior runs through it).
The rest of section 6 is Freerouting (route_6_prep_dsn.py / route_6b_import_ses.py)."""
import routelib


def build(b, R):
    R.track("/BST_EN", 0.25, [(37.775, -51.5), (30.4, -51.5), (30.4, -36.95), (27.7, -36.95)])
    # UART (B.Cu, THT pad to THT pad)
    R.track("/UART_TX", 0.25, [(3.95, -45.885), (5.22, -47.155), (8.6, -47.155), (10.5, -45.885)], routelib.B)
    R.track("/UART_RX", 0.25, [(3.95, -43.345), (5.22, -44.615), (8.6, -44.615), (10.5, -43.345)], routelib.B)
    # VBAT_SENSE
    R.track("/VBAT_SENSE", 0.25, [(38.5, -33.025), (40.2, -31.375), (41.05, -31.4), (41.9, -31.425)])
    R.track("/VBAT_SENSE", 0.25, [(41.05, -31.4), (41.05, -30.25)])  # T joint at a segment end (Freerouting sees it)
    R.via("/VBAT_SENSE", 41.05, -30.25)
    R.track("/VBAT_SENSE", 0.25, [(41.05, -30.25), (34.5, -28.95)], routelib.B)
    R.via("/VBAT_SENSE", 34.5, -28.95)
    R.track("/VBAT_SENSE", 0.25, [(34.5, -28.95), (34.5, -30.85)])
    # VBUS_SENSE
    R.track("/VBUS_SENSE", 0.25, [(43.6, -33.025), (45.3, -31.375), (47.0, -31.425)])
    R.track("/VBUS_SENSE", 0.25, [(43.6, -33.025), (42.75, -32.175), (42.75, -29.55)])
    R.via("/VBUS_SENSE", 42.75, -29.55)
    R.track("/VBUS_SENSE", 0.25, [(42.75, -29.55), (35.6, -28.3)], routelib.B)
    R.via("/VBUS_SENSE", 35.6, -28.3)
    R.track("/VBUS_SENSE", 0.25, [(35.6, -28.3), (35.6, -29.1), (35.0, -29.7), (35.0, -30.85)])


routelib.run("6a", build)
