@echo off
cd /d "%~dp0"
echo Starting EvidenceMatch...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" on the first screen. Then double-click this file again.
  pause
  exit /b 1
)
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installing the requirements failed. Check your internet connection and try again.
  pause
  exit /b 1
)
start "" http://127.0.0.1:8000
echo.
echo EvidenceMatch is running at http://127.0.0.1:8000
echo Keep this window open. Close it to stop.
python app.py
pause
