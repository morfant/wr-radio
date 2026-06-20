# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WR-Radio is a portable internet radio (Raspberry Pi Zero 2W) that streams ambient sounds from locations worldwide. The repository has three parts: `PI/` (Python application), `PCB/` (Eagle CAD schematic/layout), and `Case/` (OpenSCAD parametric case).

All active software development happens in `PI/`.

## Running the Application

On the Raspberry Pi:
```bash
cd PI
python3 run.py
```

Via systemd service (production):
```bash
sudo systemctl start wr-radio
sudo journalctl -u wr-radio -f   # view logs
```

Hardware component tests (run individually on Pi to verify hardware):
```bash
cd PI
python3 test/ads1115/bat_test.py       # battery ADC
python3 test/encoder/test_rotary.py    # rotary encoder
python3 test/oled/oled_test.py         # display
python3 test/bt/bt_test.py             # Bluetooth
```

LCD 표시 테스트 스크립트 (`sudo` 필요, 실행 전 서비스 중지):
```bash
sudo systemctl stop wr-radio
sudo python3 test/lcd/weather_icon_test.py     # 3×3 그리드로 전체 날씨 아이콘
sudo python3 test/lcd/weather_layout_test.py   # 실제 레이아웃으로 5초 간격 순환
```

`sudo`로 실행 시 패키지 누락 오류가 나면: `sudo pip3 install <패키지> --break-system-packages`

There is no test suite or linter configured — tests are hardware integration tests that require physical hardware.

## Configuration

Config file is hardcoded to `/home/wr-radio/wr-radio/config.json`. On first run it is created automatically with default stations. Stations can be managed from a browser (see "Station Management Web UI") or by editing that file directly. Each station needs `name`, `url`, `location`, `lat`, `lon`, `color` fields (`timezone` is derived from lat/lon at load by `normalize_stations()`, so it need not be stored). See `PI/config.json.example` for the schema.

Weather requires an OpenWeatherMap API key set in `openweather_api_key`.

## Software Architecture

`PI/wr_radio/` is a Python package where all modules share a single `AppState` dataclass instance passed by reference:

- **`state.py`** — `AppState` dataclass: single source of truth for all runtime state (mode, volume, brightness, BT connection, weather cache, hardware handles)
- **`main.py`** — Application entry point and main loop. Owns GPIO/SPI setup, UI mode state machine (normal → volume → system_menu → brightness), and coordinates all subsystems
- **`config.py`** — Config file load/save. Hardcoded path. Also owns the timezone lookup table and `DEFAULT_STATIONS`
- **`player.py`** — Manages an `mpv` subprocess controlled via Unix IPC socket (`/tmp/wr_mpv.sock`). Also handles headphone jack detection (GPIO 23) and PAM8403 amp power (GPIO 24). Spawns a background thread (`_audio_monitor_thread`) that monitors `core-idle` property and BT sink liveness
- **`display.py`** — Raw ST7789 SPI driver (RGB565, no library). Uses PIL for rendering. Prefers `display_image_region()` over full `display_image()` to reduce SPI traffic. PIL weather icons are drawn programmatically (emoji font incompatibility workaround). `display_time_only()` 함수로 시간 영역(y=68 strip)만 1분마다 부분 갱신
- **`bluetooth.py`** — Wraps `bluetoothctl` and `pactl` subprocesses. `Scanner` class runs scan in a background thread; name lookups via `bluetoothctl info` run in their own threads to avoid blocking the scan loop
- **`battery.py`** — Reads ADS1115 over I2C (A0 = battery voltage ×2 divider, A1 = VBUS ×2 divider). Sampling is paused 20s after station changes to let the voltage stabilize
- **`weather.py`** — OpenWeatherMap API, 10-minute cache in `AppState.weather_cache`, fetches in daemon threads
- **`input.py`** — Pure logic for rotary encoder (S1/S2 edge detection with debounce) and button (short press / long press distinction)
- **`wifi.py`** — WiFi provisioning via `nmcli`. When WiFi is unavailable, starts a WPA2 hotspot ("WR-Radio Setup") and serves a stdlib `http.server` config page so the user enters home WiFi credentials from a browser. See "WiFi Provisioning" section below
- **`webadmin.py`** — Always-on stdlib `http.server` (port 8080) for managing the station list from a phone/PC browser. Started once at boot, runs for the app lifetime in a daemon thread. See "Station Management Web UI" section below

### GPIO Pin Assignments (BCM)

| Signal | Pin | Notes |
|--------|-----|-------|
| Rotary S1/S2 | 17/27 | Pull-up, falling edge = rotation |
| Button KEY | 22 | Pull-up |
| LCD CS/DC/RST/BL | 26/13/6/12 | BL via PWM 1kHz |
| Headphone detect | 23 | Pull-up, HIGH = inserted |
| Amp STBY | 24 | LOW = standby |
| I2S BCLK/LRCLK/DIN | **18/19/21** | **Hardware-fixed — cannot change** |

### Key Design Constraints

- **SPI at 16MHz** (not 64MHz): higher speeds couple noise into the audio path via power rails
- **mpv IPC**: all player control goes through the Unix socket, never by killing/spawning new processes except for output-device switches (BT ↔ speaker)
- **BT scan pauses audio**: `bluetoothctl scan on` causes RF interference; playback is stopped before scanning and resumed after
- **Lock file**: `/tmp/wr_radio.lock` prevents multiple instances
- **overlayfs**: root FS is read-only in production images; persistent data lives on a separate `/data` partition. Disabled during development

### UI Mode State Machine

```
normal ──(short press)──▶ volume ──(press/timeout)──▶ normal
normal ──(long press)───▶ system_menu ──(select Brightness)──▶ brightness ──▶ system_menu
                          system_menu ──(select Back/timeout)──▶ normal
```

All modes time out after 3 seconds of inactivity (`InputConfig.mode_timeout_sec`).

System menu items (`SYSTEM_MENU_ITEMS` in `main.py`): Brightness, Bluetooth, **Manage Stations**, **WiFi Setup**, Power Off, Back. WiFi Setup calls the blocking `wifi.provision_wifi()` (re-provisioning after relocating to a new network). Manage Stations shows the web UI URL on the LCD (`show_station_admin()`, blocks until knob press); the web server itself runs continuously regardless of this menu.

## Station Management Web UI (webadmin.py)

Lets users add/edit/delete/reorder radio stations from a phone/PC browser, instead of SSHing in to edit `config.json`. The server runs **always-on** (started once at boot in `main()` via `webadmin.start_server(state)`), bound to `0.0.0.0:8080` on the home WiFi (STA mode). Access URL: `http://<hostname>.local:8080` (mDNS/avahi; stable across IP changes). The "Manage Stations" menu item just displays this URL on the LCD. Idle cost is negligible (server thread blocks on `accept()`).

**Thread-safety design — the critical part (do not regress):** `state.radio_stations` / `state.current_index` are indexed without bounds checks all over (`player.py`, `display.py`, the main loop). So the web thread **never mutates `state` directly**. Instead:
1. The web handler writes the new list to `config.json` via `config.update_stations()` (atomic temp-file + `os.replace`, under the shared `config._config_lock` that also guards `save_settings()` — prevents read-modify-write races), then sets `state.stations_dirty = True` (a plain bool; safe under the GIL).
2. The main loop checks `stations_dirty` at the top of each iteration and calls `reload_stations()` — the **only** place `radio_stations`/`current_index` are reassigned from web edits. It clears the flag first (so edits arriving mid-reload are caught next loop), reloads + `normalize_stations()`, and **tracks the playing station by URL**: if the playing station's URL still exists in the new list, `current_index` follows it (so reorder / deleting an earlier station never interrupts playback); if it's gone (deleted or its URL edited), it clamps the index and sets `pending_play` to switch.

**Routes** (`BaseHTTPRequestHandler`, `ThreadingHTTPServer` with `daemon_threads`): `GET /` (list + add form), `GET /edit?i=N` (prefilled edit form), `POST /add|/edit|/delete|/move` → validate with `config.validate_station()` → `update_stations()` + dirty flag → `303` redirect. Invalid input re-renders the form with an error. **Deleting the last remaining station is refused** (empty list would crash the bounds-free indexing). No auth (home-LAN device, explicit assumption).

**Coordinate entry** (three ways): manual decimal; **place-name geocoding** — a "Look up" button hits `GET /geocode?q=` which calls the OpenWeatherMap Geocoding API (reusing `state.openweather_api_key`) and fills lat/lon; and **DMS** — `_parse_coord()` converts `35°18'31"N` style input to decimal server-side in `_build_station()`. The `location` input is capped at `LOCATION_MAXLEN` (30) so it can't overflow the LCD line.

**Locusonus browser** (`GET /browse`, `POST /add_locusonus`): lists the live streams from the Locustream Icecast server (`LOCUS_STATUS_URL` = `…/status-json.xsl`, 5-min cache in `_locus_cache`) with listener counts. `_normalize_locus_url()` keeps only `.mp3`/`.ogg` mounts and rewrites each to the public `https://locus.creacast.com:9443/<mount>` form (verified reachable/playable). Adding maps `server_name` → name and **geocodes the place-name part** (text before " - ") for coordinates; on geocode failure it falls back to the manual add form prefilled with name/url. Already-added streams (URL match) show "Added" instead of a button. Note: Locusonus mics are intermittent, so the list only shows currently-live streams.

## WiFi Provisioning (wifi.py)

`provision_wifi()` is a **blocking** function (not a main-loop mode) called from two places in `main.py`:
1. **At boot** — after the splash, if `is_wifi_connected()` is false. If a saved WiFi profile exists, waits up to 20s for NetworkManager to connect (reboot race) showing `display_wifi_waiting()`; a new device (`has_saved_wifi()` false) skips the wait and provisions immediately.
2. **From the system menu** — "WiFi Setup" item, to reconfigure WiFi.

Flow: scan networks → start hotspot → serve HTTP form → user submits SSID+password → connect → on success return to normal radio; on failure show error and retry loop.

Key details and the bugs they fix (all hard-won — do not regress):
- **Hotspot**: `nmcli device wifi hotspot` (WPA2, SSID "WR-Radio Setup", password `wrradio1`). Open networks are blocked by modern macOS, so WPA2 is required. Pi IP = `10.42.0.1`.
- **HTTP server runs as `wr-radio` (non-root)** so port 80 fails → falls back to `8080`. URL shown on LCD is `10.42.0.1:8080`.
- **`server.server_close()` after `shutdown()`** — without it the socket stays bound and the retry loop crashes with "Address already in use", which systemd restarts into an infinite provisioning loop.
- **Connect via explicit profile** (`nmcli connection add` with `wifi-sec.key-mgmt wpa-psk`), not `nmcli device wifi connect`. The latter needs the SSID in the scan cache, which is empty right after tearing down the hotspot → fails with "key-mgmt: property is missing".
- **`_cleanup_hotspots()` deletes by AP mode, not name** — `nmcli device wifi hotspot` auto-names the connection "Hotspot", so name-based cleanup left profiles accumulating.
- **Cancel**: holding the button 1.5s during provisioning cancels → tears down hotspot (NM auto-reconnects a saved profile) → returns to normal radio (the menu is the re-entry point, so a wrong password never bricks the device).

**Debugging tip**: while provisioning, the Pi is in AP mode and unreachable from the home network. Provision from a **phone** (on the hotspot) so the dev machine stays on home WiFi. `journalctl -u wr-radio` persists across reboots — analyze failures after the Pi rejoins the network.

## Display Layout (display.py)

### 날씨 아이콘 + 온도
- 위치: `icon_x=86`, `icon_y=location_y+43`, 온도 텍스트 `icon_x+30`
- 아이콘 코드: `01` 맑음, `02` 구름조금, `03`/`04` 구름, `09` 이슬비(파란 점 3개), `10` 비(사선 4줄), `11` 천둥, `13` 눈, `50` 안개(파란 점 10개 산포)
- 아이콘은 PIL로 직접 드로잉 (emoji 폰트 미지원으로 인한 대안)

### 배터리 아이콘
- 본체 20px + 팁 2px, 충전 중 번개 볼트는 외곽선 안(y+3~y+11)에 맞춤
- 충전 상태 감지: VBUS(ADS1115 A1) ≥ 4.0V

### 부분 갱신 영역
- `y=0~18`: 배터리 + BT 인디케이터
- `y=0~115`: 스테이션 정보 전체 (채널 변경 시)
- `y=68~86`: 시간 텍스트만 (1분마다 `display_time_only()`)
- `y=125~165`: 애니메이션 (재생 중 사인파, 로딩 중 점)
- `y=168~239`: 스테이션 번호 + 버튼 힌트

## Pi 연결 및 배포

```bash
ssh wr-radio@192.168.0.56
cd ~/wr-radio && git pull
sudo systemctl restart wr-radio
```

서비스 파일: `/etc/systemd/system/wr-radio.service`, `WorkingDirectory=/home/wr-radio/wr-radio/PI`

### 신규 기기 셋업 필수 단계: nmcli sudoers 규칙

WiFi 프로비저닝(`wifi.py`)은 `sudo nmcli`로 핫스팟을 만든다. 서비스는 `wr-radio` 사용자(비-root)로 실행되므로, 비밀번호 없이 `nmcli`를 쓸 수 있도록 sudoers 규칙이 **각 기기마다** 필요하다. 없으면 프로비저닝이 "Insufficient privileges"로 실패한다.

```bash
echo 'wr-radio ALL=(root) NOPASSWD: /usr/bin/nmcli' | sudo tee /etc/sudoers.d/wr-radio-nmcli
sudo chmod 440 /etc/sudoers.d/wr-radio-nmcli
```

`nmcli` 하나만 허용해 권한 범위를 좁게 유지한다.
