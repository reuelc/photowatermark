@echo off
setlocal EnableDelayedExpansion
title PhotoWatermark Pro — Uninstaller

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║         PhotoWatermark Pro  —  Uninstaller           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  This will remove:
echo    • The virtual environment (venv folder)
echo    • Desktop shortcut
echo    • Start Menu entry
echo.
echo  This will NOT remove:
echo    • The watermark_app folder itself
echo    • Your watermarked output images in ~/watermarked_output/
echo    • Your saved profiles in the profiles/ folder
echo.

set /p CONFIRM="  Are you sure you want to uninstall? (Y/N): "
if /i not "!CONFIRM!"=="Y" (
    echo  Uninstall cancelled.
    pause
    exit /b 0
)

cd /d "%~dp0"

REM ── Remove desktop shortcut ──────────────────────────────────────────────────
echo.
echo  Removing desktop shortcut...
set SHORTCUT=%USERPROFILE%\Desktop\PhotoWatermark Pro.lnk
if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo  Desktop shortcut removed.
) else (
    echo  Desktop shortcut not found (already removed).
)

REM ── Remove Start Menu entry ──────────────────────────────────────────────────
echo  Removing Start Menu entry...
set STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\PhotoWatermark Pro.lnk
if exist "%STARTMENU%" (
    del "%STARTMENU%"
    echo  Start Menu entry removed.
) else (
    echo  Start Menu entry not found (already removed).
)

REM ── Remove virtual environment ───────────────────────────────────────────────
echo  Removing virtual environment (venv)...
if exist venv (
    rmdir /s /q venv
    echo  Virtual environment removed.
) else (
    echo  Virtual environment not found (already removed).
)

REM ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   Uninstall Complete.                                ║
echo  ║                                                      ║
echo  ║   Your output images and profiles were kept.         ║
echo  ║   You can safely delete the watermark_app folder     ║
echo  ║   to fully remove all application files.             ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause
endlocal
