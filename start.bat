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
    echo Can Python 3.10+, psycopg va DATABASE_URL PostgreSQL trong .env.
    echo Chay: python -m pip install -r requirements.txt
    pause
)
