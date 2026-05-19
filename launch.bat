@echo off
cd /d "%~dp0"
py -3 server.py 2>nul
if %errorlevel% neq 0 (
    py -3 server.py
)
pause
