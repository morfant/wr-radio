/*
WR-Radio Base Plate (Raspberry Pi Zero 2W + radio-hat-v07) — OpenSCAD
Units: millimeters

Layout (NOT a stacked HAT): the Pi Zero 2W and the radio-hat PCB lie COPLANAR,
side by side, joined by a 90° right-angle 2x20 header. The HAT's GPIO connector
(J1) is on its LEFT edge, so the Pi sits to the LEFT of the HAT.

This file is just the BASE: a flat plate with M2.5 standoff posts under both
boards. Walls / front panel / battery bay come later.

All board dimensions and hole positions are taken from the Gerber/drill output of
PCB/radio-hat-v07_2026-06-06 (drill format METRIC TZ 000.000, FSLAX34Y34).

Usage:
  1) Open in OpenSCAD.
  2) show_part = "preview" to eyeball board alignment, "base" to export.
  3) Verify pi_gap / pi_y_offset against the physical right-angle header, tweak,
     then F6 (Render) -> File > Export > STL.
*/

/////////////// WHAT TO SHOW \\\\\\\\\\\\\

show_part = "preview";   // "preview" | "base"

/////////////// PARAMETERS \\\\\\\\\\\\\

// --- radio HAT (radio-hat-v07), origin at board bottom-left ---
hat_w = 63.48;           // board width  (x)
hat_h = 69.98;           // board height (y)
// 5x M2.5 mounting holes, gerber coords shifted +5.08 in y so board min = (0,0)
HAT_HOLES = [
    [ 5.10,  5.08],
    [58.44,  5.08],
    [ 5.12, 64.68],
    [58.42, 64.68],
    [59.44, 34.24],      // extra hole, right edge mid-height
];

// --- Raspberry Pi Zero 2W ---
pi_long  = 65;           // long edge
pi_short = 30;           // short edge
// Pi is rotated 90° CW so its long edge runs along Y and the GPIO header faces
// the HAT (+x). It is placed to the LEFT of the HAT.
pi_gap      = 7.45;      // gap between Pi right edge and HAT left edge — measured: 7.3 (bottom) / 7.6 (top), avg 7.45
pi_y_offset = 1.75;      // shift Pi along Y to align header with J1 — measured offset ~0.75mm down from 2.5

// derived Pi placement (do not edit; driven by the two params above)
pi_x0 = -(pi_short + pi_gap);   // Pi bounding-box min x
pi_y0 = pi_y_offset;            // Pi bounding-box min y
// Pi M2.5 holes (58x23 pattern, 3.5 mm from each edge) in base coords
PI_HOLES = [
    [pi_x0 + 3.5,  pi_y0 + 3.5],
    [pi_x0 + 3.5,  pi_y0 + 61.5],
    [pi_x0 + 26.5, pi_y0 + 3.5],
    [pi_x0 + 26.5, pi_y0 + 61.5],
];

// --- base plate ---
base_th   = 2.5;         // plate thickness
margin    = 5.0;         // extra plate border beyond board footprints
corner_r  = 4.0;         // base outer fillet
post_h    = 4.0;         // standoff height (lifts boards off the plate)
post_od   = 5.5;         // standoff outer diameter
screw_d   = 2.1;         // pilot hole for M2.5 self-tapping screw (use 2.6 for inserts)
screw_depth = post_h + base_th;   // how deep the pilot goes

$fn = 48;

/////////////// DERIVED EXTENTS \\\\\\\\\\\\\

// footprint bounds across both boards
min_x = pi_x0 - margin;
max_x = hat_w + margin;
min_y = min(0, pi_y0) - margin;
max_y = max(hat_h, pi_y0 + pi_long) + margin;
plate_w = max_x - min_x;
plate_h = max_y - min_y;

/////////////// MODULES \\\\\\\\\\\\\

module rrect(sz, r) {
    offset(r=r) offset(delta=-r) square(sz, center=false);
}

module standoff(pos) {
    translate([pos[0], pos[1], 0]) {
        difference() {
            cylinder(h = base_th + post_h, d = post_od);
            translate([0, 0, base_th + post_h - screw_depth + 0.01])
                cylinder(h = screw_depth, d = screw_d);
        }
    }
}

module base_plate() {
    // plate
    translate([min_x, min_y, 0])
        linear_extrude(base_th)
            rrect([plate_w, plate_h], corner_r);
    // standoffs
    for (p = HAT_HOLES) standoff(p);
    for (p = PI_HOLES)  standoff(p);
}

// --- preview-only board ghosts (sit on top of the standoffs) ---
module hat_ghost() {
    color([0.2, 0.5, 0.9, 0.35])
        translate([0, 0, base_th + post_h])
            linear_extrude(1.6)
                difference() {
                    square([hat_w, hat_h]);
                    for (p = HAT_HOLES) translate(p) circle(d = 2.75);
                }
}

module pi_ghost() {
    color([0.2, 0.8, 0.4, 0.35])
        translate([pi_x0, pi_y0, base_th + post_h])
            linear_extrude(1.6)
                difference() {
                    square([pi_short, pi_long]);
                    for (p = PI_HOLES) translate([p[0]-pi_x0, p[1]-pi_y0]) circle(d = 2.75);
                }
    // GPIO header block on the Pi edge facing the HAT (visual only)
    color([0.1, 0.1, 0.1, 0.5])
        translate([pi_x0 + pi_short - 5, pi_y0 + (pi_long-50.8)/2, base_th + post_h + 1.6])
            cube([5, 50.8, 8.5]);
}

/////////////// OUTPUT \\\\\\\\\\\\\

if (show_part == "base") {
    base_plate();
} else {
    base_plate();
    hat_ghost();
    pi_ghost();
}
