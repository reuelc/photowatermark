@echo off
setlocal EnableDelayedExpansion
title PhotoWatermark Pro — Installer

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║         PhotoWatermark Pro  —  Installer             ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

REM ── Step 1: Check Python ────────────────────────────────────────────────────
echo  [1/5] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not on PATH.
    echo.
    echo  Please install Python 3.10 or later from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  Found: !PYVER!

REM ── Step 2: Create virtual environment ──────────────────────────────────────
echo.
echo  [2/5] Creating virtual environment in .\venv ...
cd /d "%~dp0"
if exist venv (
    echo  Virtual environment already exists, skipping creation.
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  Virtual environment created successfully.
)

REM ── Step 3: Install dependencies ────────────────────────────────────────────
echo.
echo  [3/5] Installing dependencies (PyQt5 + Pillow)...
echo  This may take a minute on the first install...
call venv\Scripts\activate.bat
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo  ERROR: pip install failed. Check your internet connection.
    pause
    exit /b 1
)
echo  Dependencies installed successfully.

REM ── Step 4: Create desktop shortcut ─────────────────────────────────────────
echo.
echo  [4/5] Creating desktop shortcut...

set SHORTCUT_PATH=%USERPROFILE%\Desktop\PhotoWatermark Pro.lnk
set APP_DIR=%~dp0
set PYTHON_EXE=%APP_DIR%venv\Scripts\pythonw.exe
set APP_SCRIPT=%APP_DIR%src\main.py

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = New-Object -ComObject WScript.Shell; ^
   $lnk = $s.CreateShortcut('%SHORTCUT_PATH%'); ^
   $lnk.TargetPath = '%PYTHON_EXE%'; ^
   $lnk.Arguments = '"%APP_SCRIPT%"'; ^
   $lnk.WorkingDirectory = '%APP_DIR%'; ^
   $lnk.Description = 'PhotoWatermark Pro - Batch Image Watermarking'; ^
   $lnk.IconLocation = '%SystemRoot%\System32\SHELL32.dll,13'; ^
   $lnk.Save()" >nul 2>&1

if exist "%SHORTCUT_PATH%" (
    echo  Desktop shortcut created: "PhotoWatermark Pro"
) else (
    echo  Note: Could not create desktop shortcut automatically.
    echo  You can launch the app manually with:  run.bat
)

REM ── Step 5: Create Start Menu shortcut ───────────────────────────────────────
echo.
echo  [5/5] Creating Start Menu entry...
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\PhotoWatermark Pro.lnk

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = New-Object -ComObject WScript.Shell; ^
   $lnk = $s.CreateShortcut('%STARTMENU%'); ^
   $lnk.TargetPath = '%PYTHON_EXE%'; ^
   $lnk.Arguments = '"%APP_SCRIPT%"'; ^
   $lnk.WorkingDirectory = '%APP_DIR%'; ^
   $lnk.Description = 'PhotoWatermark Pro - Batch Image Watermarking'; ^
   $lnk.IconLocation = '%SystemRoot%\System32\SHELL32.dll,13'; ^
   $lnk.Save()" >nul 2>&1

echo  Start Menu entry created.

REM ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   Installation Complete!                             ║
echo  ║                                                      ║
echo  ║   Launch options:                                    ║
echo  ║   • Double-click "PhotoWatermark Pro" on Desktop     ║
echo  ║   • Start Menu → PhotoWatermark Pro                  ║
echo  ║   • Double-click run.bat in this folder              ║
echo  ║   • python src\main.py  (from this folder)           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

set /p LAUNCH="  Launch the app now? (Y/N): "
if /i "!LAUNCH!"=="Y" (
    start "" "%PYTHON_EXE%" "%APP_SCRIPT%"
)

pause
endlocal
