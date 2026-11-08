#!/usr/bin/env python3
"""Generate concepts_3d.html (three.js viewer) and concept_{A,A2,A3,B,C1,C2}.step from concepts.py.
Inner frame (mm): x left->right, y front->rear, z bottom->top; case outer = inner +/- T.
Run: python3 concepts_3d.py"""
import json, os
import concepts as C

OUT = os.path.dirname(os.path.abspath(__file__))
T = C.T


def O(name, kind, box, axis=None, label=True):
    """Opening: kind 'rect' (box) or 'disc' (cylinder through the wall along axis, radius from box)."""
    return dict(name=name, kind=kind, box=tuple(box), axis=axis, label=label)


# Openings as full 3D boxes (inner frame), merged from the F/T/R marks in concepts.py.
# Where the 2D marks give only two axes, the third is inferred; see ASSUMED notes.
def openings(key, c):
    Wi, Di, Hi = c["inner"]
    if key == "A":
        return [
            O("USB-C 충전", "rect", (93.5, 102.5, Di, Di + T, 17.5, 21.5)),            # rear wall (F/T marks y71-74, R mark z17.5-21.5)
            O("이어폰 잭", "rect", (Wi, Wi + T, 32.5, 38.5, 16.5, 22.5)),              # right wall; z ASSUMED around HAT mid-height
            O("전원 스위치", "rect", (66.5 - 3.07, 66.5 + 3.07, Di, Di + T, 31.5 - 3.07, 31.5 + 3.07)),  # rear wall at bushing
            O("LCD 창", "rect", (94 - 17.8, 94 + 17.8, -T, 0, 63 - 16.15, 63 + 16.15)),
            O("스피커 그릴", "disc", (33 - 22.4, 33 + 22.4, -T, 0, 63 - 22.4, 63 + 22.4), "y"),
            O("엔코더", "rect", (94 - 13.5, 94 + 13.5, 24 - 13.5, 24 + 13.5, Hi, Hi + T)),  # top wall around knob axis
        ]
    if key == "A2":
        return [
            O("LCD 창", "rect", (94 - 17.8, 94 + 17.8, -T, 0, 48 - 16.15, 48 + 16.15)),
            O("스피커 그릴", "disc", (33 - 22.4, 33 + 22.4, -T, 0, 48 - 22.4, 48 + 22.4), "y"),
            O("엔코더(상단)", "disc", (94 - 13.5, 94 + 13.5, 24 - 13.5, 24 + 13.5, Hi, Hi + T), "z"),
            O("USB-C 충전", "rect", (Wi, Wi + T, 50, 57, 45.5, 50.5)),
            O("이어폰 잭", "rect", (86, 94, 49.5, 57.5, Hi, Hi + T)),
            O("전원 스위치", "rect", (Wi, Wi + T, 34.5 - 3.07, 34.5 + 3.07, 23.5 - 3.07, 23.5 + 3.07)),
        ]
    if key == "A3":
        pc1, uy, uz = 47.6, 49.2, 67.9
        ly, jx, jy = pc1 + 0.6, 48.1, pc1 + 3.0
        sw_y, sw_z = 55.6, 69.5
        ops = [
            O("LCD 창", "rect", (94 - 17.8, 94 + 17.8, -T, 0, 48 - 16.15, 48 + 16.15)),
            O("스피커 그릴", "disc", (33 - 22.4, 33 + 22.4, -T, 0, 48 - 22.4, 48 + 22.4), "y"),
            O("엔코더(상단)", "disc", (94 - 13.5, 94 + 13.5, 24 - 13.5, 24 + 13.5, Hi, Hi + T), "z"),
            O("USB-C 충전 (포켓 13.5×7.5×2.2)", "rect", (-T, -0.8, uy - 3.75, uy + 3.75, uz - 6.75, uz + 6.75)),
            O("USB-C 개구 9.6×3.8", "rect", (-0.8, 0, uy - 1.9, uy + 1.9, uz - 4.8, uz + 4.8), None, False),
            O("충전 LED", "disc", (-T, 0, ly - 1, ly + 1, 56.0, 58.0), "x"),
            O("충전 LED", "disc", (-T, 0, ly - 1, ly + 1, 52.0, 54.0), "x", False),
            O("이어폰 잭 Ø7", "disc", (jx - 3.5, jx + 3.5, jy - 3.5, jy + 3.5, Hi, Hi + T), "z"),
            O("SD 카드 슬롯", "rect", (79.5, 93.5, 47.8, 50.8, Hi, Hi + T)),
            O("전원 스위치", "rect", (Wi, Wi + T, sw_y - 3.07, sw_y + 3.07, sw_z - 3.07, sw_z + 3.07)),
        ]
        for i in range(5):
            x = 16 + 8 * i
            ops.append(O("환기", "rect", (x - 1, x + 1, Di, Di + T, 17, 37), None, i == 0))
            ops.append(O("환기", "rect", (x - 1, x + 1, Di, Di + T, 64, 84), None, i == 0))
        return ops
    if key == "B":
        return [
            O("LCD 창", "rect", (35.5 - 17.8, 35.5 + 17.8, -T, 0, 116.75 - 16.15, 116.75 + 16.15)),
            O("엔코더", "disc", (35.5 - 13.5, 35.5 + 13.5, -T, 0, 82.5 - 13.5, 82.5 + 13.5), "y"),
            O("스피커 그릴", "disc", (35.5 - 26.4, 35.5 + 26.4, -T, 0, 33 - 26.4, 33 + 26.4), "y"),
            O("이어폰 잭", "rect", (32.5, 38.5, 65, 72, Hi, Hi + T)),                  # top wall; x ASSUMED centered
            O("USB-C 충전", "rect", (Wi, Wi + T, 64, 72, 92.5, 112.5)),                   # right wall
            O("전원 스위치", "rect", (Wi, Wi + T, 52.5 - 3.07, 52.5 + 3.07, 115.5 - 3.07, 115.5 + 3.07)),
        ]
    if key == "C1":
        return [
            O("LCD 창", "rect", (94 - 17.8, 94 + 17.8, -T, 0, 35.5 - 16.15, 35.5 + 16.15)),
            O("스피커 그릴", "disc", (33 - 22.4, 33 + 22.4, -T, 0, 35.5 - 22.4, 35.5 + 22.4), "y"),
            O("엔코더", "disc", (137.5 - 13.5, 137.5 + 13.5, -T, 0, 35.5 - 13.5, 35.5 + 13.5), "y"),
            O("USB-C 충전", "rect", (Wi, Wi + T, 37, 44, 31, 36)),
            O("이어폰 잭", "rect", (134.5, 142.5, 36.5, 44.5, Hi, Hi + T)),
            O("전원 스위치", "rect", (Wi, Wi + T, 18.5 - 3.07, 18.5 + 3.07, 15.5 - 3.07, 15.5 + 3.07)),
        ]
    return [  # C2
        O("LCD 창", "rect", (94 - 17.8, 94 + 17.8, -T, 0, 20.25 - 16.15, 20.25 + 16.15)),
        O("스피커 그릴", "disc", (33 - 22.4, 33 + 22.4, -T, 0, 35.5 - 22.4, 35.5 + 22.4), "y"),
        O("엔코더(상단)", "disc", (94 - 13.5, 94 + 13.5, 14 - 13.5, 14 + 13.5, Hi, Hi + T), "z"),
        O("USB-C 충전", "rect", (Wi, Wi + T, 34, 41, 31, 36)),
        O("이어폰 잭", "rect", (134.5, 142.5, 33.5, 41.5, Hi, Hi + T)),
        O("전원 스위치", "rect", (Wi, Wi + T, 18.5 - 3.07, 18.5 + 3.07, 15.5 - 3.07, 15.5 + 3.07)),
    ]


def concept_data():
    out = []
    for fn in (C.concept_A, C.concept_A2, C.concept_A3, C.concept_B, C.concept_C1, C.concept_C2):
        c = fn()
        Wi, Di, Hi = c["inner"]
        parts = [dict(name=" ".join(p["name"].split()), col=p["col"], shape=p["shape"], axis=p["axis"],
                      box=list(p["box"]), dashed=p["dashed"], alpha=p.get("alpha")) for p in c["parts"]]
        out.append(dict(key=c["key"], title=c["title"], inner=[Wi, Di, Hi], outer=list(C.outer(c)),
                        parts=parts, openings=[dict(o) for o in openings(c["key"], c)],
                        note=f"{c['flex_note']} / {c['extra']}", notes=c.get("notes", []), labels=c.get("labels3d", [])))
    return out


# ---------------- STEP ----------------
def build_step(c):
    import cadquery as cq
    Wi, Di, Hi = c["inner"]

    def box(b):
        x0, x1, y0, y1, z0, z1 = b
        return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

    def cylinder(b, axis):
        x0, x1, y0, y1, z0, z1 = b
        d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
        r = {"x": min(y1 - y0, z1 - z0), "y": min(x1 - x0, z1 - z0), "z": min(x1 - x0, y1 - y0)}[axis] / 2
        ln = {"x": x1 - x0, "y": y1 - y0, "z": z1 - z0}[axis]
        p = {"x": (x0, (y0 + y1) / 2, (z0 + z1) / 2), "y": ((x0 + x1) / 2, y0, (z0 + z1) / 2),
             "z": ((x0 + x1) / 2, (y0 + y1) / 2, z0)}[axis]
        return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, ln, cq.Vector(*p), cq.Vector(*d)))

    shell = box((-T, Wi + T, -T, Di + T, -T, Hi + T)).cut(box((0, Wi, 0, Di, 0, Hi)))
    for o in c["openings"]:
        shell = shell.cut(cylinder(o["box"], o["axis"]) if o["kind"] == "disc" else box(o["box"]))
    asm = cq.Assembly(name=f"concept_{c['key']}")
    asm.add(shell, name="case_shell", color=cq.Color(0.6, 0.6, 0.6, 0.3))
    for i, p in enumerate(c["parts"]):
        solid = cylinder(p["box"], p["axis"]) if p["shape"] == "cyl" else box(p["box"])
        h = p["col"].lstrip("#")
        rgb = [int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]
        asm.add(solid, name=f"{i + 1:02d}_{p['name'].replace(' ', '_')}", color=cq.Color(*rgb, 1))
    path = os.path.join(OUT, f"concept_{c['key']}.step")
    asm.save(path)
    return path


# ---------------- HTML ----------------
def main():
    data = concept_data()
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__T__", str(T))
    with open(os.path.join(OUT, "concepts_3d.html"), "w", encoding="utf-8") as f:
        f.write(html)
    for c in data:
        print(build_step(c))


TEMPLATE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WR-Radio 케이스 3D</title>
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#eef0f3;font-family:system-ui,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;color:#222}
#bar{position:fixed;top:0;left:0;right:0;padding:8px 12px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;background:rgba(255,255,255,.88);z-index:5;border-bottom:1px solid #ccd}
button{font:inherit;padding:5px 11px;border:1px solid #889;border-radius:6px;background:#fff;cursor:pointer}
button.on{background:#2d4a7a;color:#fff;border-color:#2d4a7a}
label.t{margin-left:8px;font-size:14px;user-select:none}
#info{position:fixed;left:12px;bottom:12px;background:rgba(255,255,255,.9);border:1px solid #ccd;border-radius:8px;padding:8px 12px;font-size:13px;max-width:300px;z-index:5;line-height:1.5}
#legend div{display:flex;align-items:center;gap:6px}
#legend i{width:12px;height:12px;border:1px solid #333;display:inline-block}
#tip{position:fixed;pointer-events:none;background:#222;color:#fff;font-size:12px;padding:3px 7px;border-radius:4px;display:none;z-index:9}
.lab{font-size:12px;font-weight:600;color:#c00;background:rgba(255,255,255,.85);padding:1px 5px;border-radius:3px;border:1px solid #e99;white-space:nowrap}
.dim{font-size:13px;font-weight:700;color:#124;background:rgba(255,255,255,.85);padding:2px 7px;border-radius:4px;white-space:nowrap}
.front{font-size:13px;font-weight:700;color:#fff;background:#2d4a7a;padding:2px 8px;border-radius:4px;white-space:nowrap}
</style>
<script type="importmap">
{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}
</script></head>
<body>
<div id="bar"></div>
<div id="info"><div id="dims"></div><div id="legend"></div><div style="color:#666;margin-top:4px">드래그: 회전 · 스크롤: 확대 · 우클릭 드래그: 이동</div></div>
<div id="tip"></div>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {CSS2DRenderer, CSS2DObject} from 'three/addons/renderers/CSS2DRenderer.js';
const DATA = __DATA__;
const T = __T__;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeef0f3);
const camera = new THREE.PerspectiveCamera(40, innerWidth/innerHeight, 1, 5000);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(devicePixelRatio); renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const lr = new CSS2DRenderer();
lr.setSize(innerWidth, innerHeight);
Object.assign(lr.domElement.style,{position:'fixed',top:'0',left:'0',pointerEvents:'none'});
document.body.appendChild(lr.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.AmbientLight(0xffffff, 0.75));
const dl = new THREE.DirectionalLight(0xffffff, 1.0); dl.position.set(200,400,300); scene.add(dl);
const grid = new THREE.GridHelper(1000, 100, 0x888899, 0xc4c8d0); grid.position.y = -0.01; scene.add(grid);

// inner (x,y,z) -> three (x, z, -y); group origin = inner origin, lifted by T so the case bottom sits on the grid.
const M = (b) => ({cx:(b[0]+b[1])/2, cy:(b[4]+b[5])/2, cz:-(b[2]+b[3])/2, sx:b[1]-b[0], sy:b[5]-b[4], sz:b[3]-b[2]});
function solid(b, geomFn) {
  const m = M(b); const g = geomFn(m); return [g, m];
}
function cylGeom(b, axis) {
  const m = M(b);
  let r, len;
  if (axis==='z'){ r=Math.min(m.sx,m.sz)/2; len=m.sy; }
  else if (axis==='y'){ r=Math.min(m.sx,m.sy)/2; len=m.sz; }
  else { r=Math.min(m.sz,m.sy)/2; len=m.sx; }
  const g = new THREE.CylinderGeometry(r, r, len, 40);
  if (axis==='y') g.rotateX(Math.PI/2); else if (axis==='x') g.rotateZ(Math.PI/2);
  return g;
}
function boxGeom(b){ const m=M(b); return new THREE.BoxGeometry(m.sx,m.sy,m.sz); }
function lab(text, cls, pos, parent){ const d=document.createElement('div'); d.className=cls; d.textContent=text;
  const o=new CSS2DObject(d); o.position.copy(pos); parent.add(o); return o; }

const groups = [], partMeshes = [], labelObjs = [], shellObjs = [];
DATA.forEach((c) => {
  const g = new THREE.Group(); g.position.y = T; scene.add(g);
  const [Wi,Di,Hi] = c.inner;
  // shell
  const sb = [-T, Wi+T, -T, Di+T, -T, Hi+T];
  const sg = boxGeom(sb), sm = M(sb);
  const shell = new THREE.Group();
  const mesh = new THREE.Mesh(sg, new THREE.MeshStandardMaterial({color:0x8899aa, transparent:true, opacity:0.15, depthWrite:false}));
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(sg), new THREE.LineBasicMaterial({color:0x222222}));
  shell.add(mesh, edges); shell.position.set(sm.cx, sm.cy, sm.cz); g.add(shell); shellObjs.push(shell);
  // parts
  c.parts.forEach((p) => {
    const geo = p.shape==='cyl' ? cylGeom(p.box, p.axis) : boxGeom(p.box);
    const mat = new THREE.MeshStandardMaterial({color:p.col, transparent:p.dashed||!!p.alpha, opacity:p.alpha||(p.dashed?0.8:1), depthWrite:!p.alpha, roughness:0.6});
    const me = new THREE.Mesh(geo, mat); const m = M(p.box); me.position.set(m.cx,m.cy,m.cz);
    me.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), new THREE.LineBasicMaterial({color:0x333333, transparent:true, opacity:0.5})));
    me.userData.name = p.name; g.add(me); partMeshes.push(me);
  });
  // openings (slightly oversized so they show over the shell faces)
  c.openings.forEach((o) => {
    const e = 0.4, b = o.box;
    const bb = [b[0]-e,b[1]+e,b[2]-e,b[3]+e,b[4]-e,b[5]+e];
    const geo = o.kind==='disc' ? cylGeom(bb, o.axis) : boxGeom(bb);
    const me = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({color:0xff2020}));
    const m = M(b); me.position.set(m.cx,m.cy,m.cz); me.userData.name = o.name+' (개구부)'; g.add(me); partMeshes.push(me);
    // label pushed outward from the wall
    const out = new THREE.Vector3(0,0,0);
    if (b[2] < 0 && b[3] <= 0.01) out.z = 18; else if (b[2] >= Di-0.01) out.z = -18;
    else if (b[0] >= Wi-0.01) out.x = 18; else if (b[1] <= 0.01 && b[0] < 0) out.x = -18; else if (b[5] > Hi) out.y = 18;
    if (o.label !== false) labelObjs.push(lab(o.name,'lab',new THREE.Vector3(m.cx,m.cy,m.cz).add(out), g));
  });
  (c.labels||[]).forEach(l => labelObjs.push(lab(l.txt,'lab',new THREE.Vector3(l.pos[0], l.pos[2], -l.pos[1]), g)));
  (c.notes||[]).forEach(n => { if (n.to) return;
    const yy = n.v==='F' ? Di*0.0 : 0;
    const pp = c.parts.find(p => n.txt.startsWith('Pi') ? p.name.startsWith('Pi') : p.name.startsWith('HAT'));
    if (!pp) return; const mm = M(pp.box);
    labelObjs.push(lab(n.txt.replace('\n',' '),'lab',new THREE.Vector3(mm.cx, mm.cy, mm.cz + mm.sz/2 + 4), g)); });
  // dims + front marker
  labelObjs.push(lab(`${c.title}  ${c.outer.map(v=>+v.toFixed(1)).join('×')} mm (W×H×D)`,'dim',
    new THREE.Vector3(Wi/2, Math.max(Hi+T, ...c.parts.map(p=>p.box[5]))+16, -Di/2), g));
  lab('▼ 정면','front',new THREE.Vector3(Wi/2, -T+1, T+32), g);
  const arrow = new THREE.ArrowHelper(new THREE.Vector3(0,0,1), new THREE.Vector3(Wi/2,-T,T+2), 22, 0x2d4a7a, 7, 5);
  g.add(arrow);
  g.userData.c = c;
  groups.push(g);
});

const gap = 40;
function layout(mode) {
  const ids = mode==='all' ? DATA.map((_,i)=>i) : [mode];
  let x = 0; const total = ids.reduce((s,i)=>s+DATA[i].outer[0],0) + gap*(ids.length-1);
  x = -total/2; let maxH=0, maxD=0;
  groups.forEach((g,i) => {
    g.visible = ids.includes(i);
    if (g.visible) { g.position.x = x + T; g.position.z = DATA[i].inner[1]/2; x += DATA[i].outer[0]+gap;
      maxH=Math.max(maxH,DATA[i].outer[1]); maxD=Math.max(maxD,DATA[i].outer[2]); }
  });
  const target = new THREE.Vector3(0, maxH/2, 0);
  const dist = Math.max(total, maxH, maxD) * 1.9 + 60;
  controls.target.copy(target);
  camera.position.set(target.x + dist*0.55, target.y + dist*0.5, target.z + dist*0.85);
  controls.update();
  // legend
  const seen = new Map();
  ids.forEach(i => DATA[i].parts.forEach(p => { if(!seen.has(p.name)) seen.set(p.name,p.col); }));
  document.getElementById('legend').innerHTML = [...seen].map(([n,c])=>`<div><i style="background:${c}"></i>${n}</div>`).join('') +
    '<div><i style="background:#ff2020"></i>개구부</div>';
  document.getElementById('dims').innerHTML = ids.map(i=>`<b>${DATA[i].title}</b> 외곽 ${DATA[i].outer.map(v=>+v.toFixed(1)).join('×')} mm<br><span style="color:#666">${DATA[i].note}</span>`).join('<br>');
}
// UI
const bar = document.getElementById('bar');
const NM = {A:'A. 가로 탁상형',A2:'A2. 가로형 (보드 세움)',A3:'A3. 추천안',B:'B. 세로형',C1:'C1. 엔코더 정면 옆',C2:'C2. 엔코더 상단'};
const names = [...DATA.map((d,i)=>[String(i),NM[d.key]||d.title]),['all','여섯 나란히 (전체)']];
const btns = names.map(([k,t]) => { const b=document.createElement('button'); b.textContent=t;
  b.onclick=()=>{ btns.forEach(x=>x.classList.remove('on')); b.classList.add('on'); layout(k==='all'?'all':+k); }; bar.appendChild(b); return b; });
function toggle(text, fn){ const l=document.createElement('label'); l.className='t'; const c=document.createElement('input'); c.type='checkbox'; c.onchange=()=>fn(c.checked); l.append(c,' '+text); bar.appendChild(l); return c; }
toggle('케이스 숨기기', v => shellObjs.forEach(s => s.visible = !v));
const lc = toggle('라벨', v => labelObjs.forEach(o => o.visible = v)); lc.checked = true;
btns[0].click();

// hover tooltip
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tip = document.getElementById('tip');
renderer.domElement.addEventListener('pointermove', (e) => {
  mouse.set(e.clientX/innerWidth*2-1, -(e.clientY/innerHeight)*2+1); ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(partMeshes.filter(m => m.parent.visible), false)[0];
  if (hit) { tip.style.display='block'; tip.style.left=(e.clientX+12)+'px'; tip.style.top=(e.clientY+12)+'px'; tip.textContent=hit.object.userData.name; }
  else tip.style.display='none';
});
addEventListener('resize', () => { camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth,innerHeight); lr.setSize(innerWidth,innerHeight); });
(function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); lr.render(scene,camera); })();
</script></body></html>
'''

if __name__ == "__main__":
    main()
