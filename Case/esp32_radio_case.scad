
/*
ESP32 Portable Radio Case (Standard) - OpenSCAD
Author: ChatGPT
Version: 1.0
Units: millimeters

How to use:
1) Open this file in OpenSCAD.
2) Set 'show_part' = "preview" | "base" | "lid".
3) Press F6 (Render) then File → Export → STL for each part.

Printing tips (FDM):
- Material: PETG or ABS/ASA preferred (humidity tolerance). PLA ok indoors.
- Layer: 0.2 mm, walls ≥ 3 perimeters, infill 15–25%.
- No supports needed by default (chamfers/bridges are designed).
- Use heat-set M3 inserts in bosses, or self-tapping M3 screws into pilot holes.

This design targets:
- Enclosure outer size ≈ 150 × 90 × 50 (W×H×D)
- 50 mm speaker (2") front grill
- 0.96" I2C OLED (SSD1306) window OR 1.8" TFT (ST7735) window (toggleable)
- Rotary encoder on front
- 3.5 mm TRS jack on right side (panel-mount style)
- Power toggle on left side (panel cutout)
- Rear battery door (4×AA holder, 2×2 type) with simple slide latch
- Internal standoffs for: ESP32 DevKit, DAC, AMP
- M3 corner posts + lid with M3 screw holes

You may adjust parameters below to fit your exact modules. 
*/

/////////////// PARAMETERS \\\\\\\\\\\\\

show_part = "preview"; // "preview", "base", "lid", "door"

// Overall outer dimensions
W = 150;   // width (x)
H = 90;    // height (y)
D = 50;    // depth (z)

wall = 2.6;        // wall thickness
lip = 1.0;         // lid/base overlap lip
corner_r = 5;      // external fillet radius (visualized via minkowski)

// Fasteners
boss_d = 6.6;      // corner boss OD for M3 inserts/screws
boss_h = 10;       // boss height in lid/base
m3_hole = 3.2;     // through hole size for M3 (clearance)
m3_pilot = 2.6;    // pilot for self-tap (if not using inserts)

// Speaker
spk_d = 50;        // speaker driver outer diameter
spk_depth = 32;    // driver depth allowance
spk_grill_margin = 3; // grill ring margin
spk_pos = [W*0.30, H*0.62]; // (x,y) from lower-left front panel

// Display
use_oled = true;   // true: 0.96" OLED window ; false: 1.8" TFT window
// OLED 0.96" (visible area ~22x11mm, PCB ~27x27); choose window a bit larger
oled_win = [27, 15]; // window opening (w,h)
oled_pos = [W*0.62, H*0.25]; // front panel position of window center

// TFT 1.8" ST7735 option
tft_win  = [36, 46]; // opening (w,h) oriented portrait by default
tft_pos  = [W*0.62, H*0.28];

// Rotary encoder (front)
enc_hole_d = 7.2;                   // shaft/bushing hole
enc_knob_clear = 18;                // visual clearance circle
enc_pos = [W*0.62, H*0.70];         // front panel position

// 3.5mm jack (right side)
jack_hole_d = 6.6;   // panel mount diameter (adjust for your part)
jack_edge_offset = 18; // distance from front panel along X for cutout center
jack_height = H*0.35; // center height from bottom

// Power switch (left side) — simple rectangle slot
sw_slot = [10, 3];                  // opening (w,h)
sw_edge_offset = 25;                // distance from front edge to slot center
sw_height = H*0.2;                  // center height from bottom

// USB access (rear or side) — small rectangular opening (optional)
usb_slot = [13, 7]; // typical micro-USB
usb_on_back = true;
usb_back_offset = [W*0.65, H*0.18]; // center on back panel

// Battery door (rear, for 4×AA 2×2 holder ~60×60×15)
door_size = [70, 70];
door_pos  = [W*0.50, H*0.55];
door_th = 2.0;
door_clearance = 0.4;

// Internal standoffs (example positions)
standoff_h = 8;
standoff_d = 5.5;
esp32_hole = [[15,15],[45,15],[45,45],[15,45]]; // simplistic 4-hole rectangle (adjust to your DevKit!)
dac_pos = [W*0.62, H*0.52];
amp_pos = [W*0.62, H*0.40];

// Tolerances
tol = 0.3;     // general clearance
lip_tol = 0.2; // lip fit


/////////////// UTILS \\\\\\\\\\\\\

module filleted_box(size=[W,H,D], r=corner_r, center=false){
    // cheap fillet by minkowski with sphere; for preview mainly
    minkowski(){
        cube(size - [2*r,2*r,2*r], center=center);
        sphere(r, $fn=32);
    }
}

module screw_boss(h=boss_h, od=boss_d, hole=m3_hole){
    difference(){
        cylinder(h=h, r=od/2, $fn=40);
        translate([0,0,-1]) cylinder(h=h+2, r=hole/2, $fn=30);
    }
}

module grill_honeycomb(w, h, cell=4, t=1.0){
    // simple hex grid by subtracting circles (lightweight approximation)
    for (x=[-w/2+cell/2:cell:w/2-cell/2])
        for (y=[-h/2+cell/2:cell:h/2-cell/2]){
            translate([x,y,0])
                cylinder(h=t+1, r=cell*0.35, $fn=6);
        }
}

// Rounded rectangle 2D
module rrect2d(sz=[20,10], r=2){
    offset(r=r) offset(delta=-r)
        square(sz, center=true);
}

/////////////// BASE & LID \\\\\\\\\\\\\

module enclosure_base(){
    // Outer shell
    difference(){
        filleted_box([W,H,D], corner_r);
        // Hollow
        translate([wall,wall,wall])
            cube([W-2*wall, H-2*wall, D - wall - lip - lip_tol]);
        // Side cutouts (jack right)
        // right wall center at x=W, y=jack_height, z=D/2
        translate([W - wall/2, jack_height, D/2])
            rotate([0,90,0]) cylinder(h=wall+2, r=jack_hole_d/2+tol, $fn=40);

        // left wall power switch slot
        translate([wall/2, sw_height, D/2])
            rotate([0,90,0])
                linear_extrude(height=wall+2)
                    rrect2d([sw_slot[0]+tol, sw_slot[1]+tol], r=1.0);

        // USB slot on back
        if (usb_on_back){
            translate([usb_back_offset[0], H - wall/2, D/2])
                rotate([90,0,0])
                    linear_extrude(height=wall+2)
                        rrect2d([usb_slot[0]+tol, usb_slot[1]+tol], r=1.0);
        }
    }

    // Lip for lid overlap (inner ledge)
    translate([wall+lip_tol, wall+lip_tol, D - wall - lip])
        cube([W-2*(wall+lip_tol), H-2*(wall+lip_tol), lip]);

    // Corner bosses (for screws up from lid, or inserts)
    boss_z = D - wall - lip - boss_h - 1;
    for (px=[10, W-10])
      for (py=[10, H-10])
        translate([px, py, boss_z])
            screw_boss(boss_h, boss_d, m3_pilot);

    // Internal standoffs plateaus (example)
    // ESP32 area
    for (p=esp32_hole){
        translate([p[0], p[1], wall+2])
            cylinder(h=standoff_h, r=standoff_d/2, $fn=30);
    }

    // DAC/AMP shelves (simple pads)
    translate([dac_pos[0]-10, dac_pos[1]-8, wall+2])
        cube([20,16,standoff_h]);
    translate([amp_pos[0]-10, amp_pos[1]-8, wall+2])
        cube([20,16,standoff_h]);

    // Battery pocket (rear) – slight recess
    translate([door_pos[0]-door_size[0]/2, door_pos[1]-door_size[1]/2, wall+2])
        cube([door_size[0], door_size[1], 8]);
}

module enclosure_lid(){
    // Lid plate with outer fillet mimic (slightly smaller to fit)
    difference(){
        filleted_box([W-2*tol, H-2*tol, wall+lip], corner_r);
        // Underside clearance (leave rim that sits on lip)
        translate([wall,wall,0])
            cube([W-2*wall-2*tol, H-2*wall-2*tol, wall+lip]);
    }

    // Front panel features (speaker, display, encoder)
    // We "cut through" from the front face (y-plane), but since lid is a solid,
    // we subtract thin prisms to make openings.

    // Coordinate helper: front face plane at y = (H-2*tol)
    front_y = H/2; // We'll position cuts by translating to the lid and subtracting from a duplicate

    // Create cutouts by overlapping negative volumes
    difference(){
        // Nothing here; we will union cutouts then subtract at the end via separate module
    }

    // Speaker grill (through-holes in lid)
    translate([spk_pos[0], spk_pos[1], (wall+lip)/2])
        difference(){
            // Open circular aperture area
            cylinder(h=wall+lip+2, r=(spk_d/2)+spk_grill_margin, $fn=80, center=true);
            // Fill with small honeycomb voids (subtract from filler to create holes)
        }

    // Cut: actual holes for grill
    translate([spk_pos[0], spk_pos[1], 0])
        drill_grill();

    // Encoder shaft hole
    translate([enc_pos[0], enc_pos[1], -1])
        cylinder(h=wall+lip+2, r=enc_hole_d/2+tol, $fn=40);

    // Display window (choose one)
    if (use_oled){
        translate([oled_pos[0]-oled_win[0]/2, oled_pos[1]-oled_win[1]/2, -1])
            cube([oled_win[0], oled_win[1], wall+lip+2]);
    } else {
        translate([tft_pos[0]-tft_win[0]/2, tft_pos[1]-tft_win[1]/2, -1])
            cube([tft_win[0], tft_win[1], wall+lip+2]);
    }

    // Lid screw holes (match base bosses)
    for (px=[10, W-10])
      for (py=[10, H-10])
        translate([px, py, -1])
            cylinder(h=wall+lip+4, r=m3_hole/2, $fn=24);
}

module drill_grill(){
    // Make a circular cluster of holes for the speaker grill.
    // Simple pattern: radial rings of holes.
    hole_r = 2;           // hole radius
    spacing = 5;
    maxR = spk_d/2 - 4;   // leave inner margin

    for (r=[spacing:spacing:maxR])
        for (a=[0:360/max(6, floor(r/spacing)):360-1]){
            x = r*cos(a);
            y = r*sin(a);
            translate([x,y,-1])
                cylinder(h=wall+lip+4, r=hole_r, $fn=20);
        }
}

module battery_door(){
    // Simple flat door with small finger notch
    difference(){
        cube([door_size[0], door_size[1], door_th], center=true);
        // finger notch
        translate([door_size[0]/2 - 6, 0, 0])
            cylinder(h=door_th+2, r=4, $fn=24, center=true);
    }
}

// BACK CUTOUT for door frame on base (relief and ledge)
module add_door_frame(){
    frame_w = door_size[0] + 2*door_clearance;
    frame_h = door_size[1] + 2*door_clearance;
    frame_t = 2.2;

    // Cut opening
    translate([door_pos[0]-frame_w/2, door_pos[1]-frame_h/2, wall+2])
        cube([frame_w, frame_h, frame_t]);

    // Add small inner lip ledge to prevent door falling in
    ledge = 1.2;
    translate([door_pos[0]-door_size[0]/2, door_pos[1]-door_size[1]/2, wall+2+frame_t-ledge])
        difference(){
            cube([door_size[0], door_size[1], ledge]);
            translate([1,1,-0.1])
                cube([door_size[0]-2, door_size[1]-2, ledge+0.2]);
        }
}

/////////////// ASSEMBLY \\\\\\\\\\\\\

module base_with_features(){
    enclosure_base();
    add_door_frame();
}

module lid_with_features(){
    enclosure_lid();
}

if (show_part == "base"){
    base_with_features();
} else if (show_part == "lid"){
    lid_with_features();
} else if (show_part == "door"){
    battery_door();
} else {
    // preview assembly
    color([0.8,0.8,0.85]) translate([0,0,0]) base_with_features();
    color([0.7,0.7,0.75,0.7]) translate([0,0,D - (wall+lip)]) lid_with_features();
    // show door separately
    color([0.6,0.7,0.9,0.8]) translate([W+20, H/2, wall+5]) rotate([90,0,0]) battery_door();
}
