# Orbital Bridge PowerShell Launcher
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "            ORBITAL BRIDGE DAEMON" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[!] Virtual environment not found. Creating .venv..." -ForegroundColor Yellow
    python -m venv (Join-Path $PSScriptRoot ".venv")
    Write-Host "[*] Installing dependencies..." -ForegroundColor Green
    & $venvPython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
}

$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[!] Warning: .env file not found!" -ForegroundColor Red
    Copy-Item (Join-Path $PSScriptRoot ".env.example") $envFile
    Write-Host "[!] Please fill in your BOT_TOKEN and ALLOWED_USER_IDS in .env." -ForegroundColor Yellow
    Start-Process notepad $envFile
    exit
}

Write-Host "[*] Starting Orbital Bridge..." -ForegroundColor Green
& $venvPython -m src.bot
