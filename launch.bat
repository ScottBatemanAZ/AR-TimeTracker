@echo off
cd /d "%~dp0"
title Azazel's Razer — Time Tracker

echo.
echo  ============================================
echo   Azazel's Razer  --  AR Time Tracker
echo  ============================================
echo.

:: ── Check for Python ──────────────────────────────────────────────────
py -3 --version >nul 2>&1
if %errorlevel% neq 0 (
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo  ERROR: Python is not installed or not found on PATH.
        echo.
        echo  Please download and install Python 3 from:
        echo.
        echo    https://www.python.org/downloads/
        echo.
        echo  IMPORTANT: During installation, check the box that says
        echo  "Add Python to PATH" before clicking Install.
        echo.
        echo  After installing Python, close this window and try again.
        echo.
        pause
        exit /b 1
    )
    set PYCMD=python
) else (
    set PYCMD=py -3
)

echo  Starting server...
echo  Open your browser to:  http://localhost:5757
echo  Press Ctrl+C to stop.
echo.

%PYCMD% server.py
echo.
echo  Server stopped.
pause
