@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  run.bat — Quick launcher for development / testing
REM ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"
python src\main.py
pause
