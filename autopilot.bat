@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Autopilot running - refreshes news, fills calendar, posts due items every 10 min. Close window to stop.
python runner.py --loop
pause
