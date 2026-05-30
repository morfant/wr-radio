#!/usr/bin/env python3
import html
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote_plus

AP_SSID     = "WR-Radio Setup"
AP_PASSWORD = "wrradio1"
AP_IP       = "10.42.0.1"
_HOTSPOT_CONN = "wr-radio-hotspot"

_credentials = None   # (ssid, password) set by HTTP handler


def is_wifi_connected() -> bool:
    try:
        r = subprocess.run(
            ["nmcli", "-t", "-f", "TYPE,STATE", "device"],
            capture_output=True, text=True, timeout=5
        )
        return any(
            line.startswith("wifi:") and line.endswith(":connected")
            for line in r.stdout.splitlines()
        )
    except Exception:
        return False


def scan_networks() -> list:
    try:
        r = subprocess.run(
            ["nmcli", "-t", "-f", "SSID", "device", "wifi", "list", "--rescan", "yes"],
            capture_output=True, text=True, timeout=20
        )
        seen, result = set(), []
        for line in r.stdout.splitlines():
            ssid = line.strip()
            if ssid and ssid not in seen:
                seen.add(ssid)
                result.append(ssid)
        return result
    except Exception:
        return []


def _nmcli(*args, timeout=15) -> subprocess.CompletedProcess:
    return subprocess.run(["sudo", "nmcli"] + list(args),
                          capture_output=True, text=True, timeout=timeout)


def _start_hotspot() -> bool:
    _nmcli("connection", "delete", _HOTSPOT_CONN, timeout=10)
    r = _nmcli("device", "wifi", "hotspot",
               "ifname", "wlan0",
               "ssid", AP_SSID,
               "password", AP_PASSWORD,
               timeout=20)
    if r.returncode != 0:
        print(f"핫스팟 실패: {r.stderr.strip()}")
        return False
    return True


def _stop_hotspot():
    _nmcli("connection", "down", _HOTSPOT_CONN, timeout=10)
    _nmcli("connection", "delete", _HOTSPOT_CONN, timeout=10)


def _connect_to_network(ssid: str, password: str) -> bool:
    if password:
        r = _nmcli("device", "wifi", "connect", ssid, "password", password, timeout=30)
    else:
        r = _nmcli("device", "wifi", "connect", ssid, timeout=30)
    return r.returncode == 0


_HTML_FORM = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WR-Radio WiFi 설정</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:sans-serif;max-width:400px;margin:40px auto;padding:0 20px;background:#111;color:#eee}}
h1{{font-size:1.4em;color:#7af}}
label{{display:block;font-size:.85em;color:#aaa;margin:14px 0 4px}}
select,input{{width:100%;padding:10px;background:#222;border:1px solid #444;color:#eee;border-radius:6px;font-size:1em}}
button{{width:100%;padding:13px;margin-top:22px;background:#27a;border:none;color:#fff;border-radius:6px;font-size:1.05em;cursor:pointer}}
button:hover{{background:#38b}}
#manual{{display:none;margin-top:8px}}
</style>
</head>
<body>
<h1>WR-Radio WiFi 설정</h1>
<form method="POST" action="/connect">
<label>WiFi 네트워크</label>
<select name="ssid_select"
  onchange="document.getElementById('manual').style.display=this.value==='__manual__'?'block':'none'">
{OPTIONS}
<option value="__manual__">직접 입력...</option>
</select>
<div id="manual">
<label>SSID 직접 입력</label>
<input type="text" name="ssid_manual" placeholder="WiFi 이름">
</div>
<label>비밀번호</label>
<input type="password" name="password" placeholder="비밀번호 없으면 빈칸">
<button type="submit">연결</button>
</form>
</body>
</html>
"""

_HTML_CONNECTING = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>연결 중</title>
<style>
body{{font-family:sans-serif;max-width:400px;margin:40px auto;padding:0 20px;background:#111;color:#eee}}
h1{{color:#7af}}
</style></head>
<body>
<h1>연결 중...</h1>
<p>기기 화면에서 결과를 확인하세요.<br>
연결 실패 시 <b>{ap_ssid}</b> 에 다시 접속하세요.</p>
</body>
</html>
"""


def _make_handler(networks):
    global _credentials

    options_html = "\n".join(
        f'<option value="{html.escape(s)}">{html.escape(s)}</option>'
        for s in networks
    )

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._respond(_HTML_FORM.format(OPTIONS=options_html))

        def do_POST(self):
            global _credentials
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace")
            params = parse_qs(body)

            ssid_sel = params.get("ssid_select", [""])[0]
            ssid_man = params.get("ssid_manual", [""])[0]
            password = unquote_plus(params.get("password", [""])[0])

            ssid = (unquote_plus(ssid_man) if ssid_sel == "__manual__"
                    else unquote_plus(ssid_sel)).strip()

            self._respond(_HTML_CONNECTING.format(ap_ssid=AP_SSID))

            if ssid:
                _credentials = (ssid, password)

        def _respond(self, body: str, code: int = 200):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return _Handler


def provision_wifi(GPIO, pins, state) -> bool:
    """
    AP 모드 + HTTP 설정 페이지로 WiFi 프로비저닝.
    성공 시 True, KeyboardInterrupt 시 False.
    port 80 권한 없으면 8080으로 fallback.
    """
    global _credentials
    from . import display as disp

    while True:
        _credentials = None

        print("WiFi 네트워크 스캔 중...")
        networks = scan_networks()
        print(f"스캔 완료: {len(networks)}개")

        if not _start_hotspot():
            disp.display_provisioning_error(GPIO, pins, state)
            time.sleep(10)
            continue

        try:
            server = HTTPServer(("0.0.0.0", 80), _make_handler(networks))
            ap_url = AP_IP
        except PermissionError:
            server = HTTPServer(("0.0.0.0", 8080), _make_handler(networks))
            ap_url = f"{AP_IP}:8080"

        disp.display_provisioning_screen(GPIO, pins, state,
                                         ap_ssid=AP_SSID, ap_pw=AP_PASSWORD,
                                         ap_url=ap_url)
        print(f"핫스팟 '{AP_SSID}' 시작, 접속 주소: {ap_url}")

        srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
        srv_thread.start()

        try:
            while _credentials is None:
                time.sleep(0.5)
        except KeyboardInterrupt:
            server.shutdown()
            _stop_hotspot()
            return False

        ssid, password = _credentials
        server.shutdown()

        print(f"핫스팟 종료 → '{ssid}' 연결 시도")
        disp.display_provisioning_connecting(GPIO, pins, state, ssid)

        _stop_hotspot()
        time.sleep(2.0)

        if _connect_to_network(ssid, password):
            print(f"WiFi 연결 성공: {ssid}")
            disp.display_provisioning_success(GPIO, pins, state)
            time.sleep(2.0)
            return True

        print(f"WiFi 연결 실패: {ssid}")
        disp.display_provisioning_failed(GPIO, pins, state)
        time.sleep(3.0)
