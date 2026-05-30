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

There is no test suite or linter configured — tests are hardware integration tests that require physical hardware.

## Configuration

Config file is hardcoded to `/home/wr-radio/wr-radio/config.json`. On first run it is created automatically with default stations. To add stations, edit that file directly. Each station needs `name`, `url`, `location`, `lat`, `lon`, `color` fields. See `PI/config.json.example` for the schema.

Weather requires an OpenWeatherMap API key set in `openweather_api_key`.

## Software Architecture

`PI/wr_radio/` is a Python package where all modules share a single `AppState` dataclass instance passed by reference:

- **`state.py`** — `AppState` dataclass: single source of truth for all runtime state (mode, volume, brightness, BT connection, weather cache, hardware handles)
- **`main.py`** — Application entry point and main loop. Owns GPIO/SPI setup, UI mode state machine (normal → volume → system_menu → brightness), and coordinates all subsystems
- **`config.py`** — Config file load/save. Hardcoded path. Also owns the timezone lookup table and `DEFAULT_STATIONS`
- **`player.py`** — Manages an `mpv` subprocess controlled via Unix IPC socket (`/tmp/wr_mpv.sock`). Also handles headphone jack detection (GPIO 23) and PAM8403 amp power (GPIO 24). Spawns a background thread (`_audio_monitor_thread`) that monitors `core-idle` property and BT sink liveness
- **`display.py`** — Raw ST7789 SPI driver (RGB565, no library). Uses PIL for rendering. Prefers `display_image_region()` over full `display_image()` to reduce SPI traffic. PIL weather icons are drawn programmatically (emoji font incompatibility workaround)
- **`bluetooth.py`** — Wraps `bluetoothctl` and `pactl` subprocesses. `Scanner` class runs scan in a background thread; name lookups via `bluetoothctl info` run in their own threads to avoid blocking the scan loop
- **`battery.py`** — Reads ADS1115 over I2C (A0 = battery voltage ×2 divider, A1 = VBUS ×2 divider). Sampling is paused 20s after station changes to let the voltage stabilize
- **`weather.py`** — OpenWeatherMap API, 10-minute cache in `AppState.weather_cache`, fetches in daemon threads
- **`input.py`** — Pure logic for rotary encoder (S1/S2 edge detection with debounce) and button (short press / long press distinction)

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
