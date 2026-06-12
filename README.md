# CoC Auto Farming Bot

Fully automated Clash of Clans farming bot using Python, ADB, and OpenCV.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add template images to templates/ folder (see templates/PLACE_TEMPLATES_HERE.txt)

# 3. Make sure LDPlayer is running with Clash of Clans on the home screen

# 4. Run
python main.py
```

## How It Works

```
Home Screen
    ↓  tap attack_icon
Find a Match screen
    ↓  tap find_match_btn
Opponent found
    ↓  tap attack_btn
Battle prep screen
    ↓  read loot (OCR) → skip if below threshold
    ↓  deploy troops
Battle
    ↓  wait for Return Home button
    ↓  tap return_home_btn
Home Screen  ← repeat
```

## Setup

### 1. LDPlayer Settings
- Resolution: **1280 × 720**
- ADB port: **5555** (default)

### 2. ADB Connection
```bash
adb connect 127.0.0.1:5555
adb devices   # should show: 127.0.0.1:5555  device
```

### 3. Template Images
Crop these from a 1280×720 screenshot and place in `templates/`:
- `attack_icon.png`
- `find_match_btn.png`
- `attack_btn.png`
- `next_btn.png`
- `return_home_btn.png`
- `home_icon.png`

### 4. config.yaml
```yaml
adb:
  adb_path: "e:/coc auto bot/adb_tools/platform-tools/adb.exe"
  device_id: "127.0.0.1:5555"

loot:
  elixir_thresholds: [6000]
  elixir_priority: true
```

## GUI Tabs

| Tab | Description |
|-----|-------------|
| **Control** | Start/Stop bot + live activity log |
| **Loot** | Set Gold / Elixir / Dark Elixir thresholds |
| **Troops** | Add troop images and set deploy quantity |
| **Stats** | Attacks, loot collected, bases skipped |

## Project Structure

```
coc auto bot/
├── main.py              ← entry point
├── gui.py               ← GUI (4 tabs)
├── bot_engine.py        ← attack cycle logic
├── adb_controller.py    ← ADB / device control
├── vision.py            ← template matching + OCR
├── troop_detector.py    ← troop bar scan + deploy zones
├── config.py            ← config loader/saver
├── config.yaml          ← settings
├── requirements.txt
├── templates/           ← button PNG templates (6 required)
├── troop_images/        ← troop icon images
├── adb_tools/           ← place adb.exe here
└── logs/                ← auto-created log files
```

## Disclaimer
Using bots violates Supercell's Terms of Service. Use on alt/test accounts only.
"# Coc-Auto-Bot" 
"# coc-Server-Bot" 
"# coc-Server-Bot" 
"# coc-Server-Bot" 
"# coc-Server-Bot" 
