@echo off
rem Double-click, or run in PowerShell:  .\run.bat --name exp-002 --max-actions 40
rem Always updates to the latest code first, then starts the driver. Extra arguments go to driver.py.
setlocal
cd /d "%~dp0"
echo Updating to the latest version...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update.ps1"
if errorlevel 1 echo Update failed. Continuing with the local version.
python -m pip install -q -r bot\requirements.txt
python bot\driver.py %*
echo.
pause
