@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================
echo   JOB HUNTER - pobieram nowe oferty i wysylam...
echo ==================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" main.py

echo.
echo ==================================================
echo   Gotowe. Sprawdz WhatsApp.
echo ==================================================
pause
