# scripts/install_requirements.ps1
# Repeatable installation script for Stage 1 Digital Forensics System

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Stage 1: Digital Forensics System - Installation Script" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.12+ from python.org"
}
$pyVersion = python --version
Write-Host "[+] Detected Python: $pyVersion" -ForegroundColor Green

# 2. Check Virtual Environment
$venvPath = Join-Path $PSScriptRoot "..\.venv"
if (-not (Test-Path "$venvPath\Scripts\python.exe")) {
    Write-Host "[*] Creating virtual environment at .venv..." -ForegroundColor Yellow
    python -m venv "$venvPath"
    Write-Host "[+] Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "[+] Existing virtual environment detected at $venvPath" -ForegroundColor Green
}

# 3. Upgrade Pip & Install Dependencies
$venvPython = "$venvPath\Scripts\python.exe"
Write-Host "[*] Installing/Verifying Python packages from requirements.txt..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $PSScriptRoot "..\requirements.txt")

# 4. Verify Imports
Write-Host "[*] Verifying critical package imports..." -ForegroundColor Yellow
& $venvPython -c "import django, watchdog, win32api, dotenv, yaml, dpkt, scapy, pytest; print('All core modules verified successfully!')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[+] All Python packages verified successfully!" -ForegroundColor Green
} else {
    Write-Error "Verification failed for one or more Python packages."
}

# 5. Check Node.js and NPM for React Native / Expo GUI
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($nodeCmd -and $npmCmd) {
    $nodeVer = node --version
    Write-Host "[+] Node.js detected: $nodeVer" -ForegroundColor Green
} else {
    Write-Host "[!] Node.js or NPM is not found in PATH. Install Node.js v18+ for Expo GUI." -ForegroundColor Yellow
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Installation and Verification Completed Successfully!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
