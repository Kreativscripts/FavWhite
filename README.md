# FavWhite

FavWhite is a small Windows desktop app that runs configurable timed key actions with:

- Main configuration window (GUI)
- Always-on-top draggable overlay showing next trigger + usage counts
- Start hides the main app and shows the overlay
- Stop closes overlay and returns to main app
- Global hotkey toggles Start/Stop (user-editable)
- Builds to a Windows EXE via PyInstaller (.spec)

---

## Features

### Macro items
Each macro item has:
- Enabled toggle
- Name
- Key (restricted to `2,3,4,5,6,7`)
- Interval (ms)
- Jitter min/max (ms)

### Global hotkey (Start/Stop)
- Configurable in the GUI
- Saved to `favwhite.cfg`

**Note:** if your target app is running as Administrator, you may need to run FavWhite as Administrator too for global hooks to behave correctly.

### Tool use (Left click spam)
Optional “tool use” mode:
- Enables continuous left-clicking
- Configurable delay in ms
- Saved to `favwhite.cfg`

### UI appearance
- Main window uses 15% transparency (opacity 0.85)
- Table resizing behavior improved

### Overlay spawn position
Overlay window spawns at a fixed location (currently set in `overlay.py`).

---

## Update system (version.json + remote checker)

FavWhite checks for updates on startup using a local `version.json`.

### `version.json` (local, shipped with the build)
This file defines:
- The version of THIS build
- The URL to check for the latest version

Example `version.json`:

```json
{
  "version": "xx.xx.2",
  "version_checker": "https://favnc.pages.dev/bss/whm.json",
  "update_url": "https://github.com/Kreativscripts/FavWhite"
}
````

### `whm.json` (remote, hosted on favnc.pages.dev)

The app loads the JSON from `version_checker` and expects a version field:

```json
{
  "version": "xx.xx.2"
}
```

### Behavior

* If `whm.json` version **matches** local `version.json` → app runs normally
* If `whm.json` version **does not match** → app shows a message and opens the GitHub repo

Message shown:

> “This is the older version of the app. Please go install the updated version on [https://github.com/Kreativscripts/FavWhite”](https://github.com/Kreativscripts/FavWhite”)

---

## Requirements

* Windows 10/11
* Python 3.11 recommended

---

## Setup (dev)

From your project root:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python .\bin\app.py
```

---

## Build EXE (PyInstaller spec)

FavWhite is built using the `.spec` file.

### Why datas matter

Because this is a onefile build, the app relies on PyInstaller `datas` to ship:

* `assets/icon.ico` (runtime + taskbar/window icon)
* `version.json` (startup update checker)
* `config_default.json` (defaults)

### Build

Run your build script which calls PyInstaller with the spec:

```bat
build.bat
```

Output typically ends up in:

`FavWhite\dist\FavWhite.v1.exe`

---

## Notes / Troubleshooting

### Hotkey doesn’t trigger

* If the target app/game is elevated (Admin), run FavWhite as Admin too.

### Icon doesn’t show

* Ensure the `.spec` includes both:

  * `EXE(... icon=...)`
  * `datas=[('...\\assets\\icon.ico', 'assets'), ...]`
* Ensure runtime asset loading uses `sys._MEIPASS` in onefile mode.