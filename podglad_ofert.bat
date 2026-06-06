@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================
echo   JOB HUNTER - PODGLAD (bez wysylki na WhatsApp)
echo ==================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" main.py --dry

echo.
pause
