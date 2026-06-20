#!/usr/bin/env python3
"""상시 동작하는 스테이션 목록 관리 웹서버 (홈 WiFi, 포트 8080).

설계: 웹 스레드는 state.radio_stations를 직접 수정하지 않는다.
config.json만 (config._config_lock + 원자적 저장으로) 갱신하고
state.stations_dirty = True 만 세운다. 메인 루프가 안전한 시점에 reload한다.
wifi.py의 stdlib http.server 패턴을 차용."""

import html
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config

PORT = 8080
LOCATION_MAXLEN = 30   # LCD location 줄(14px)이 240px 화면에서 잘리지 않는 안전선

# Locusonus(Locustream) Icecast 서버 — 라이브 스트림 목록을 JSON으로 제공
LOCUS_STATUS_URL = "https://locus.creacast.com:9443/status-json.xsl"
LOCUS_BASE = "https://locus.creacast.com:9443"
LOCUS_TTL = 300.0   # 목록 캐시 수명(초)
_locus_cache = {"t": 0.0, "data": []}
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
.added{color:#7c7;font-size:.8em;padding:6px 9px;white-space:nowrap}
a.browse{display:inline-block;margin:4px 0 8px;color:#7af;font-size:.92em}
label{display:block;font-size:.82em;color:#aaa;margin:12px 0 4px}
input{width:100%;padding:9px;background:#222;border:1px solid #444;color:#eee;border-radius:6px;font-size:1em}
.row{display:flex;gap:8px}
.row>div{flex:1}
button.primary{width:100%;padding:12px;margin-top:18px;background:#27a;border:none;color:#fff;border-radius:6px;font-size:1.02em;cursor:pointer}
button.primary:hover{background:#38b}
button.lookup{width:100%;padding:9px;background:#444;border:1px solid #555;color:#cde;border-radius:6px;font-size:.95em;cursor:pointer}
button.lookup:hover{background:#555}
.geo{font-size:.78em;color:#9bf;min-height:1.1em;margin-top:4px}
.hint{font-size:.75em;color:#888;margin-top:4px}
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
<input name="location" value="{loc}" placeholder="City, Country" maxlength="{LOCATION_MAXLEN}">
{_PLACE_BLOCK}
<div class="row">
<div><label>Latitude</label><input name="lat" value="{lat}" placeholder="-90 ~ 90" required></div>
<div><label>Longitude</label><input name="lon" value="{lon}" placeholder="-180 ~ 180" required></div>
</div>
<div class="hint">Decimal (35.31, 135.72) or DMS (35 18 31 N) accepted.</div>
<label>Color (R / G / B, 0-255)</label>
<div class="row">
<div><input name="cr" value="{r}" placeholder="R"></div>
<div><input name="cg" value="{g}" placeholder="G"></div>
<div><input name="cb" value="{b}" placeholder="B"></div>
</div>
<button class="primary" type="submit">Save</button>
</form>
<p><a class="back" href="/">&larr; Back to list</a></p>
""" + _GEO_SCRIPT


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
<a class="browse" href="/browse">&#127758; Browse Locusonus live streams &rarr;</a>
{''.join(rows)}
<h2>Add a new station</h2>
<form method="POST" action="/add">
<label>Name</label>
<input name="name" placeholder="Station name" required>
<label>Stream URL</label>
<input name="url" placeholder="https://..." required>
<label>Location</label>
<input name="location" placeholder="City, Country" maxlength="{LOCATION_MAXLEN}">
{_PLACE_BLOCK}
<div class="row">
<div><label>Latitude</label><input name="lat" placeholder="-90 ~ 90" required></div>
<div><label>Longitude</label><input name="lon" placeholder="-180 ~ 180" required></div>
</div>
<div class="hint">Decimal (35.31, 135.72) or DMS (35 18 31 N) accepted.</div>
<label>Color (R / G / B, 0-255)</label>
<div class="row">
<div><input name="cr" placeholder="R"></div>
<div><input name="cg" placeholder="G"></div>
<div><input name="cb" placeholder="B"></div>
</div>
<button class="primary" type="submit">Add station</button>
</form>
""" + _GEO_SCRIPT


def _browse_page(streams, existing_urls, msg="", err="") -> str:
    rows = []
    for s in streams:
        added = s["url"] in existing_urls
        listeners = s.get("listeners", 0)
        if added:
            action = '<span class="added">&#10003; Added</span>'
        else:
            action = (
                '<form method="POST" action="/add_locusonus">'
                f'<input type="hidden" name="url" value="{_esc(s["url"])}">'
                f'<input type="hidden" name="name" value="{_esc(s["name"])}">'
                '<button>Add</button></form>')
        rows.append(f"""
<div class="st">
<div class="info">
<div class="nm">{_esc(s['name'])}</div>
<div class="lc">{listeners} listening</div>
<div class="url">{_esc(s['url'])}</div>
</div>
<div class="acts">{action}</div>
</div>""")

    banner = ""
    if err:
        banner = f'<div class="msg err">{_esc(err)}</div>'
    elif msg:
        banner = f'<div class="msg ok">{_esc(msg)}</div>'

    body = "".join(rows) if rows else '<p class="hint">No live streams right now.</p>'
    return f"""
<h1>Browse Locusonus</h1>
<p><a class="back" href="/">&larr; Back to stations</a>&nbsp;&nbsp;<a class="back" href="/browse?refresh=1">Refresh</a></p>
{banner}
<p class="hint">{len(streams)} live streams. Coordinates are auto-filled from the place name; adjust them after adding if needed.</p>
{body}
"""


# ── 폼 파싱 / 스테이션 빌드 ──────────────────────────────────────────
def _field(params, key, default=""):
    return params.get(key, [default])[0].strip()


def _parse_coord(s: str) -> str:
    """좌표 입력을 소수(decimal degrees) 문자열로 정규화.
    소수('35.31', '-0.04')는 그대로, 도-분-초(DMS, '35°18'31\"N')는 변환.
    파싱 불가 시 원문 반환 → validate_station이 '숫자여야 한다'로 거른다."""
    s = s.strip()
    if not s:
        return s
    try:
        return str(float(s))            # 이미 소수
    except ValueError:
        pass
    hemi_m = re.search(r"[NSEWnsew]", s)
    hemi = hemi_m.group(0).upper() if hemi_m else ""
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if not nums:
        return s
    deg = float(nums[0])
    minutes = float(nums[1]) if len(nums) > 1 else 0.0
    seconds = float(nums[2]) if len(nums) > 2 else 0.0
    val = deg + minutes / 60.0 + seconds / 3600.0
    if s.startswith("-") or hemi in ("S", "W"):
        val = -val
    return str(round(val, 6))


def _build_station(params):
    """폼 파라미터 → 스테이션 dict. color는 빈칸이면 None(검증 후 기본색)."""
    cr, cg, cb = (_field(params, "cr"), _field(params, "cg"), _field(params, "cb"))
    color = None if (cr == "" and cg == "" and cb == "") else [cr, cg, cb]
    return {
        "name": _field(params, "name"),
        "url": _field(params, "url"),
        "location": _field(params, "location"),
        "lat": _parse_coord(_field(params, "lat")),
        "lon": _parse_coord(_field(params, "lon")),
        "color": color,
    }


def _geocode(query: str, api_key: str):
    """OpenWeatherMap Geocoding API로 지명 → (lat, lon, label). 없으면 None."""
    import requests  # weather.py와 동일 의존성; import 실패 회피 위해 지연 로드
    r = requests.get(
        "https://api.openweathermap.org/geo/1.0/direct",
        params={"q": query, "limit": 1, "appid": api_key},
        timeout=8,
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    top = data[0]
    parts = [top.get("name", ""), top.get("state", ""), top.get("country", "")]
    label = ", ".join(p for p in parts if p)
    return round(float(top["lat"]), 6), round(float(top["lon"]), 6), label


def _normalize_locus_url(listenurl: str) -> str:
    """Icecast listenurl에서 mount(basename)만 떼어 공개 https(9443) 형식으로 통일.
    기본 스테이션들이 쓰는, Pi에서 검증된 형식과 동일하게 맞춘다."""
    try:
        mount = urlparse(listenurl).path.strip("/")
    except Exception:
        return ""
    if not mount or not mount.lower().endswith((".mp3", ".ogg")):
        return ""
    return f"{LOCUS_BASE}/{mount}"


def _fetch_locusonus(force: bool = False):
    """라이브 스트림 목록 [{name, url, listeners}] + error. 5분 캐시.
    실패 시 직전 캐시를 유지하고 에러 메시지를 함께 반환."""
    now = time.time()
    if not force and _locus_cache["data"] and (now - _locus_cache["t"]) < LOCUS_TTL:
        return _locus_cache["data"], None
    try:
        import requests
        r = requests.get(LOCUS_STATUS_URL, timeout=10)
        r.raise_for_status()
        sources = r.json().get("icestats", {}).get("source", [])
        if isinstance(sources, dict):    # 소스가 1개면 Icecast가 dict로 반환
            sources = [sources]
        out, seen = [], set()
        for s in sources:
            url = _normalize_locus_url(s.get("listenurl") or s.get("server_url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            name = (s.get("server_name") or "").strip() or url.rsplit("/", 1)[-1]
            out.append({"name": name, "url": url, "listeners": s.get("listeners", 0)})
        out.sort(key=lambda x: x["name"].lower())
        _locus_cache["data"] = out
        _locus_cache["t"] = now
        return out, None
    except Exception as e:
        print(f"⚠️  Locusonus 목록 가져오기 실패: {e}")
        return _locus_cache["data"], "Could not reach the Locusonus server."


# 지명 입력 + 좌표 자동조회 버튼 (추가/편집 폼 공용). 수동 lat/lon 입력은 그대로 둔다.
_PLACE_BLOCK = """
<label>Place name (optional &mdash; fills coordinates below)</label>
<div class="row">
<div style="flex:2"><input id="place" placeholder="e.g. London, GB"></div>
<div style="flex:1"><button type="button" class="lookup" onclick="geocode()">Look up</button></div>
</div>
<div id="geo_status" class="geo"></div>
"""

_GEO_SCRIPT = """
<script>
function geocode(){
  var q=document.getElementById('place').value.trim();
  var s=document.getElementById('geo_status');
  if(!q){s.textContent='Enter a place name first.';return;}
  s.textContent='Looking up...';
  fetch('/geocode?q='+encodeURIComponent(q)).then(function(r){return r.json();}).then(function(d){
    if(d.ok){
      document.getElementsByName('lat')[0].value=d.lat;
      document.getElementsByName('lon')[0].value=d.lon;
      var loc=document.getElementsByName('location')[0];
      if(loc&&!loc.value){loc.value=d.label;}
      s.textContent='Found: '+d.label+' ('+d.lat+', '+d.lon+')';
    }else{s.textContent=d.error||'Not found.';}
  }).catch(function(){s.textContent='Lookup failed.';});
}
</script>
"""


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

        def _json(self, obj, code=200):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

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
            elif parsed.path == "/geocode":
                qs = parse_qs(parsed.query)
                self._handle_geocode(qs.get("q", [""])[0].strip())
            elif parsed.path == "/browse":
                qs = parse_qs(parsed.query)
                streams, err = _fetch_locusonus(force=bool(qs.get("refresh")))
                existing = {s.get("url") for s in self._stations()}
                self._html(_browse_page(streams, existing,
                                        msg=qs.get("msg", [""])[0], err=err))
            else:
                self._redirect("/")

        def _handle_geocode(self, query):
            api_key = getattr(state, "openweather_api_key", "") or ""
            if not api_key:
                self._json({"ok": False,
                            "error": "Weather API key not set; enter coordinates manually."})
                return
            if not query:
                self._json({"ok": False, "error": "Enter a place name."})
                return
            try:
                res = _geocode(query, api_key)
            except Exception:
                self._json({"ok": False, "error": "Lookup failed."})
                return
            if not res:
                self._json({"ok": False, "error": "Place not found."})
                return
            lat, lon, label = res
            self._json({"ok": True, "lat": lat, "lon": lon, "label": label})

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
            elif path == "/add_locusonus":
                self._handle_add_locusonus(params)
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

        def _handle_add_locusonus(self, params):
            url = _field(params, "url")
            name = _field(params, "name")
            if not url:
                self._redirect("/browse?err=Missing+stream")
                return
            stations = self._stations()
            if any(s.get("url") == url for s in stations):
                self._redirect("/browse?msg=Already+added")
                return
            # server_name의 장소명 부분("London - Stave Hill" → "London")을 지오코딩
            city = re.split(r"\s+[-–]\s+", name, maxsplit=1)[0].strip() or name
            geo = None
            api_key = getattr(state, "openweather_api_key", "") or ""
            if api_key:
                try:
                    geo = _geocode(city, api_key)
                except Exception:
                    geo = None
            if geo:
                lat, lon, label = geo
                st = {"name": name, "url": url, "location": label,
                      "lat": str(lat), "lon": str(lon), "color": None}
                ok, _err = config.validate_station(st)
                if ok:
                    stations.append(_finalize_station(st))
                    self._commit(stations)
                    self._redirect("/browse?msg=Added")
                    return
            # 좌표 자동조회 실패 → 수동 입력 폼으로 (name/url/location 채워서)
            prefill = {"name": name, "url": url, "location": city}
            self._html(_station_form(
                "/add", st=prefill,
                error=f"Couldn't find coordinates for '{city}'. "
                      "Enter them manually or use Look up."))

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
