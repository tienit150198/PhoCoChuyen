@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 server.py --open
) else (
    python server.py --open
)
if errorlevel 1 (
    echo.
    echo Can Python 3.11 tro len. Cai Python va chon Add Python to PATH.
    pause
)
