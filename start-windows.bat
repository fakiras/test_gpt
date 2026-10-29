@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Open http://YOUR-PC-IP:8765 on your iPad.
ipconfig
.venv\Scripts\python.exe server.py
if errorlevel 1 goto error
exit /b 0
:error
echo Startup failed. Install Python 3.10 or newer and check the error above.
pause
exit /b 1
