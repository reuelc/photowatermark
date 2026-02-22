@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  build.bat — Package PhotoWatermark Pro as a standalone Windows .exe
REM
REM  Requirements: pip install pyinstaller
REM  Output:       dist\PhotoWatermark Pro\PhotoWatermark Pro.exe
REM ─────────────────────────────────────────────────────────────────────────────

echo.
echo  Building PhotoWatermark Pro...
echo.

REM Change to the project root (same folder as this .bat file)
cd /d "%~dp0"

REM Install / upgrade dependencies
pip install -r requirements.txt

REM Run PyInstaller
pyinstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name "PhotoWatermark Pro" ^
    --add-data "profiles;profiles" ^
    src\main.py

echo.
echo  ─────────────────────────────────────────────────────────────────────
echo   Build complete!
echo   Executable: dist\PhotoWatermark Pro\PhotoWatermark Pro.exe
echo  ─────────────────────────────────────────────────────────────────────
echo.
pause
