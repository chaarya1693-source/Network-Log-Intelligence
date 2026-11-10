# scripts/run_project.ps1
# Runner script for HPC-Accelerated AI-Enhanced Digital Forensics System (Stage 1)

param(
    [string]$Collectors = "file,network,usb,android",
    [int]$Port = 8000,
    [switch]$NoServer = $false
)

$PSScriptRoot_Resolved = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot_Resolved "..")
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment python not found at $VenvPython. Run install_requirements.ps1 first."
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Stage 1: Digital Forensics System - Project Launcher" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] Project Root: $ProjectRoot"
Write-Host "[*] Active Python: $VenvPython"
Write-Host "[*] Selected Collectors: $Collectors"
Write-Host "[*] Web Dashboard: http://127.0.0.1:$Port/"
Write-Host "==========================================================" -ForegroundColor Cyan

Set-Location $ProjectRoot
$env:PYTHONPATH = "$ProjectRoot"

if ($NoServer) {
    & $VenvPython main.py --collectors $Collectors --no-server
} else {
    & $VenvPython main.py --collectors $Collectors --port $Port
}

