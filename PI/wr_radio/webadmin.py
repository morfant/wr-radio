#!/usr/bin/env python3
"""상시 동작하는 스테이션 목록 관리 웹서버 (홈 WiFi, 포트 8080).

설계: 웹 스레드는 state.radio_stations를 직접 수정하지 않는다.
config.json만 (config._config_lock + 원자적 저장으로) 갱신하고
state.stations_dirty = True 만 세운다. 메인 루프가 안전한 시점에 reload한다.
wifi.py의 stdlib http.server 패턴을 차용."""

import html
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config

PORT = 8080
DEFAULT_COLOR = (100, 200, 255)


# ── HTML ────────────────────────────────────────────────────────────
_STYLE = """\
*{box-sizing:border-box}
body{font-family:sans-serif;max-width:560px;margin:24px auto;padding:0 16px;background:#111;color:#eee}
h1{font-size:1.4em;color:#7af}
h2{font-size:1.05em;color:#9bf;margin-top:28px}
.msg{padding:10px 12px;border-radius:6px;margin:12px 0;font-size:.9em}
.msg.err{background:#511;border:1px solid #944;color:#fbb}
.msg.ok{background:#151;border:1px solid #494;color:#bfb}
.st{display:flex;align-items:center;gap:10px;padding:10px;border:1px solid #333;border-radius:8px;margin:8px 0;background:#1a1a1a}
.sw{width:18px;height:18px;border-radius:4px;flex:0 0 auto;border:1px solid #555}
.info{flex:1;min-width:0}
.info .nm{font-weight:600}
.info .lc{font-size:.8em;color:#9aa}
.info .url{font-size:.72em;color:#678;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.acts{display:flex;gap:4px;flex:0 0 auto}
.acts form{margin:0}
.acts button,.acts a{display:inline-block;padding:6px 9px;font-size:.8em;border-radius:5px;border:1px solid #444;background:#222;color:#cde;text-decoration:none;cursor:pointer}
.acts .del{color:#f99;border-color:#633}
label{display:block;font-size:.82em;color:#aaa;margin:12px 0 4px}
input{width:100%;padding:9px;background:#222;border:1px solid #444;color:#eee;border-radius:6px;font-size:1em}
.row{display:flex;gap:8px}
.row>div{flex:1}
button.primary{width:100%;padding:12px;margin-top:18px;background:#27a;border:none;color:#fff;border-radius:6px;font-size:1.02em;cursor:pointer}
button.primary:hover{background:#38b}
a.back{color:#7af;font-size:.9em}
"""

_PAGE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WR-Radio Stations</title>
<style>{style}</style>
</head>
<body>
{body}
</body>
</html>
"""


def _page(body: str) -> str:
    return _PAGE.format(style=_STYLE, body=body)


def _esc(v) -> str:
    return html.escape(str(v), quote=True)


def _color_of(st) -> tuple:
    c = st.get("color")
    if isinstance(c, (list, tuple)) and len(c) == 3:
        try:
            return tuple(int(x) for x in c)
        except (TypeError, ValueError):
            pass
    return DEFAULT_COLOR


def _station_form(action: str, st=None, index=None, error="") -> str:
    """추가(action=/add)와 편집(action=/edit) 폼 공용 렌더러."""
    st = st or {}
    r, g, b = _color_of(st) if st else DEFAULT_COLOR
    name = _esc(st.get("name", ""))
    url = _esc(st.get("url", ""))
    loc = _esc(st.get("location", ""))
    lat = _esc(st.get("lat", ""))
    lon = _esc(st.get("lon", ""))
    title = "Edit station" if index is not None else "Add station"
    idx_field = (f'<input type="hidden" name="index" value="{index}">'
                 if index is not None else "")
    err_html = f'<div class="msg err">{_esc(error)}</div>' if error else ""
    return f"""
<h1>{title}</h1>
{err_html}
<form method="POST" action="{action}">
{idx_field}
<label>Name</label>
<input name="name" value="{name}" placeholder="Station name" required>
<label>Stream URL</label>
<input name="url" value="{url}" placeholder="https://..." required>
<label>Location</label>
<input name="location" value="{loc}" placeholder="City, Country">
<div class="row">
<div><label>Latitude</label><input name="lat" value="{lat}" placeholder="-90 ~ 90" required></div>
<div><label>Longitude</label><input name="lon" value="{lon}" placeholder="-180 ~ 180" required></div>
</div>
<label>Color (R / G / B, 0-255)</label>
<div class="row">
<div><input name="cr" value="{r}" placeholder="R"></div>
<div><input name="cg" value="{g}" placeholder="G"></div>
<div><input name="cb" value="{b}" placeholder="B"></div>
</div>
<button class="primary" type="submit">Save</button>
</form>
<p><a class="back" href="/">&larr; Back to list</a></p>
"""


def _list_page(stations, msg="", err="") -> str:
    rows = []
    n = len(stations)
    for i, st in enumerate(stations):
        r, g, b = _color_of(st)
        up = "" if i == 0 else (
            f'<form method="POST" action="/move">'
            f'<input type="hidden" name="index" value="{i}">'
            f'<input type="hidden" name="dir" value="up">'
            f'<button title="Move up">&#9650;</button></form>')
        down = "" if i == n - 1 else (
            f'<form method="POST" action="/move">'
            f'<input type="hidden" name="index" value="{i}">'
            f'<input type="hidden" name="dir" value="down">'
            f'<button title="Move down">&#9660;</button></form>')
        delete = (
            f'<form method="POST" action="/delete" '
            f'onsubmit="return confirm(\'Delete this station?\')">'
            f'<input type="hidden" name="index" value="{i}">'
            f'<button class="del" title="Delete">&#10005;</button></form>')
        rows.append(f"""
<div class="st">
<span class="sw" style="background:rgb({r},{g},{b})"></span>
<div class="info">
<div class="nm">{_esc(st.get('name',''))}</div>
<div class="lc">{_esc(st.get('location',''))}</div>
<div class="url">{_esc(st.get('url',''))}</div>
</div>
<div class="acts">
<a href="/edit?i={i}">Edit</a>
{up}{down}{delete}
</div>
</div>""")

    banner = ""
    if err:
        banner = f'<div class="msg err">{_esc(err)}</div>'
    elif msg:
        banner = f'<div class="msg ok">{_esc(msg)}</div>'

    return f"""
<h1>WR-Radio Stations</h1>
{banner}
{''.join(rows)}
<h2>Add a new station</h2>
<form method="POST" action="/add">
<label>Name</label>
<input name="name" placeholder="Station name" required>
<label>Stream URL</label>
<input name="url" placeholder="https://..." required>
<label>Location</label>
<input name="location" placeholder="City, Country">
<div class="row">
<div><label>Latitude</label><input name="lat" placeholder="-90 ~ 90" required></div>
<div><label>Longitude</label><input name="lon" placeholder="-180 ~ 180" required></div>
</div>
<label>Color (R / G / B, 0-255)</label>
<div class="row">
<div><input name="cr" placeholder="R"></div>
<div><input name="cg" placeholder="G"></div>
<div><input name="cb" placeholder="B"></div>
</div>
<button class="primary" type="submit">Add station</button>
</form>
"""


# ── 폼 파싱 / 스테이션 빌드 ──────────────────────────────────────────
def _field(params, key, default=""):
    return params.get(key, [default])[0].strip()


def _build_station(params):
    """폼 파라미터 → 스테이션 dict. color는 빈칸이면 None(검증 후 기본색)."""
    cr, cg, cb = (_field(params, "cr"), _field(params, "cg"), _field(params, "cb"))
    color = None if (cr == "" and cg == "" and cb == "") else [cr, cg, cb]
    return {
        "name": _field(params, "name"),
        "url": _field(params, "url"),
        "location": _field(params, "location"),
        "lat": _field(params, "lat"),
        "lon": _field(params, "lon"),
        "color": color,
    }


def _finalize_station(st):
    """검증 통과한 폼 dict를 저장용 정규 형태로. timezone 자동 채움."""
    color = st.get("color")
    rgb = list(DEFAULT_COLOR) if color is None else [int(c) for c in color]
    lat, lon = float(st["lat"]), float(st["lon"])
    return {
        "name": st["name"].strip(),
        "url": st["url"].strip(),
        "location": st.get("location", "").strip(),
        "lat": lat,
        "lon": lon,
        "color": rgb,
        "timezone": config.find_timezone(lat, lon),
    }


# ── 핸들러 ──────────────────────────────────────────────────────────
def _make_handler(state):

    class _Handler(BaseHTTPRequestHandler):

        # ---- 응답 헬퍼 ----
        def _html(self, body, code=200):
            data = _page(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _redirect(self, location="/"):
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _read_params(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            return parse_qs(body)

        @staticmethod
        def _stations():
            cfg = config.load_config()
            return list(cfg.get("stations", [])) if cfg else []

        def _commit(self, stations):
            ok = config.update_stations(stations)
            if ok:
                state.stations_dirty = True
            return ok

        # ---- GET ----
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                qs = parse_qs(parsed.query)
                self._html(_list_page(self._stations(),
                                      msg=qs.get("msg", [""])[0],
                                      err=qs.get("err", [""])[0]))
            elif parsed.path == "/edit":
                qs = parse_qs(parsed.query)
                try:
                    i = int(qs.get("i", ["-1"])[0])
                except ValueError:
                    i = -1
                stations = self._stations()
                if 0 <= i < len(stations):
                    self._html(_station_form("/edit", st=stations[i], index=i))
                else:
                    self._redirect("/?err=Station+not+found")
            else:
                self._redirect("/")

        # ---- POST ----
        def do_POST(self):
            path = urlparse(self.path).path
            params = self._read_params()
            if path == "/add":
                self._handle_add(params)
            elif path == "/edit":
                self._handle_edit(params)
            elif path == "/delete":
                self._handle_delete(params)
            elif path == "/move":
                self._handle_move(params)
            else:
                self._redirect("/")

        def _handle_add(self, params):
            raw = _build_station(params)
            ok, err = config.validate_station(raw)
            if not ok:
                self._html(_station_form("/add", st=raw, error=err))
                return
            stations = self._stations()
            stations.append(_finalize_station(raw))
            self._commit(stations)
            self._redirect("/?msg=Station+added")

        def _handle_edit(self, params):
            try:
                i = int(_field(params, "index", "-1"))
            except ValueError:
                i = -1
            raw = _build_station(params)
            stations = self._stations()
            if not (0 <= i < len(stations)):
                self._redirect("/?err=Station+not+found")
                return
            ok, err = config.validate_station(raw)
            if not ok:
                self._html(_station_form("/edit", st=raw, index=i, error=err))
                return
            stations[i] = _finalize_station(raw)
            self._commit(stations)
            self._redirect("/?msg=Station+updated")

        def _handle_delete(self, params):
            try:
                i = int(_field(params, "index", "-1"))
            except ValueError:
                i = -1
            stations = self._stations()
            if len(stations) <= 1:
                self._redirect("/?err=Cannot+delete+the+last+station")
                return
            if 0 <= i < len(stations):
                del stations[i]
                self._commit(stations)
                self._redirect("/?msg=Station+deleted")
            else:
                self._redirect("/?err=Station+not+found")

        def _handle_move(self, params):
            try:
                i = int(_field(params, "index", "-1"))
            except ValueError:
                i = -1
            direction = _field(params, "dir")
            stations = self._stations()
            j = i - 1 if direction == "up" else i + 1
            if 0 <= i < len(stations) and 0 <= j < len(stations):
                stations[i], stations[j] = stations[j], stations[i]
                self._commit(stations)
            self._redirect("/")

        def log_message(self, *args):
            pass

    return _Handler


def start_server(state):
    """관리 웹서버를 데몬 스레드로 기동. 실패 시 None 반환 (라디오 동작에는 영향 없음)."""
    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), _make_handler(state))
        server.daemon_threads = True
    except Exception as e:
        print(f"⚠️  스테이션 관리 웹서버 시작 실패 (포트 {PORT}): {e}")
        return None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"🌐 스테이션 관리 웹서버 시작: 포트 {PORT}")
    return server
