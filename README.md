# FavWhite

A small Windows desktop app that runs configurable timed key actions with:

- Main configuration window
- Always-on-top draggable overlay showing next trigger + usage counts
- Start hides the main app and shows the overlay
- Stop closes overlay and returns to main app
- Global hotkey: **Ctrl + Q** toggles Start/Stop
- Builds to a Windows EXE via PyInstaller

## Requirements
- Windows 10/11
- Python 3.10+ (3.11 recommended)

## Setup (dev)

From `dev_workspace/`:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python ..\bin\app.py
```

## Build EXE

From `dev_workspace/`:

### PowerShell
```powershell
.\build.ps1
```

### CMD
```bat
build.bat
```

The EXE will be created in:
`dev_workspace\dist\favwhite\favwhite.exe`

Copy it to the repo root and rename it to `favwhite.exe` if desired.

## Notes
- Uses OS-level keyboard injection via `pynput`.
- If you want to send keys to elevated windows, you may need to run as Administrator.
