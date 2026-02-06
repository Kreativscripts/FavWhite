@echo off
setlocal enabledelayedexpansion

echo ===============================
echo FavWhite Onefile Builder
echo ===============================

cd /d "%~dp0"

REM Repo root is parent of dev_workspace
set ROOT=%cd%\..

set BIN=%ROOT%\bin
set ASSETS=%ROOT%\assets
set ICON=%ASSETS%\icon.ico

if not exist "%ICON%" (
    echo [ERROR] Missing icon file:
    echo         %ICON%
    echo Convert your PNG to ICO and place it there.
    pause
    exit /b 1
)

echo [INFO] Cleaning build/dist...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [INFO] Running PyInstaller...

pyinstaller --clean --onefile --noconsole ^
  --name favwhite ^
  --paths "%BIN%" ^
  --icon "%ICON%" ^
  --hidden-import pynput.keyboard._win32 ^
  --hidden-import pynput.mouse._win32 ^
  "%BIN%\app.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Build finished!
echo Output:
echo %cd%\dist\favwhite.exe
echo.

pause
endlocal
