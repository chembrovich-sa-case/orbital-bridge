@echo off
title Orbital Bridge Daemon
echo ===================================================
echo            ORBITAL BRIDGE DAEMON
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Creating .venv...
    python -m venv .venv
    echo [*] Installing dependencies...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist ".env" (
    echo [!] Warning: .env file not found!
    echo [*] Copying .env.example to .env...
    copy .env.example .env
    echo [!] Please fill in your BOT_TOKEN and ALLOWED_USER_IDS in .env before running.
    notepad .env
    pause
    exit /b
)

echo [*] Starting Orbital Bridge...
.venv\Scripts\python.exe -m src.bot
pause
