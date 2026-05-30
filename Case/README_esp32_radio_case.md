
# ESP32 Portable Radio Case (Standard) — OpenSCAD

This folder contains a **parametric OpenSCAD** model for a two-part portable enclosure:
- **Base**
- **Lid (front panel)**
- **Battery door** (rear)

## Default Target
- 150 × 90 × 50 mm outer size
- 50 mm speaker (front grill)
- 0.96" OLED (SSD1306) window (toggle to 1.8" TFT if needed)
- Rotary encoder on the front
- 3.5 mm jack on the right
- Power switch on the left
- Micro‑USB slot on the back (optional toggle)
- Internal bosses/standoffs for ESP32 and small DAC/AMP boards
- Battery door fits typical 4×AA (2×2) holder

## How to Use
1. Install **OpenSCAD**.
2. Open `esp32_radio_case.scad`.
3. At the top, set `show_part` to `"base"`, render (F6), then `File → Export → STL`.
4. Repeat with `"lid"` and `"door"`.
5. Print each STL. Suggested: PETG/ABS, 0.2 mm layer, 15–25% infill, ≥3 perimeters.

## Adjustments
- Edit the **Parameters** section to match your exact modules:
  - `spk_d`, `oled_win`/`tft_win`, `enc_hole_d`, `jack_hole_d`, etc.
  - Positions: `spk_pos`, `oled_pos`/`tft_pos`, `enc_pos`, side cutouts, etc.
- Corner bosses accept **M3** (inserts or self-tapping). 
  - Hole defaults: `m3_hole` (clearance in lid), `m3_pilot` (pilot in base boss).

## Notes
- The *speaker grill* is a perforated hole pattern. Adjust `hole_r`/spacing inside `drill_grill()`.
- The **battery door** is a simple plate; you can tape/magnetize or add a tiny screw if desired.
- The file includes a basic **USB cutout**; set `usb_on_back=false` to remove.

## Next Steps
- After a first test print, measure your parts and tweak tolerances (`tol`, `lip_tol`).
- If you switch to a **1.8" TFT**, set `use_oled=false` and adjust `tft_win`/`tft_pos`.
- For very tight builds, consider moving to a custom PCB for cable reduction.

Happy printing! 🎧
