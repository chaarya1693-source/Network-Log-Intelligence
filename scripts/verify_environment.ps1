# scripts/verify_environment.ps1
# Environment Verification & Diagnostic Report Script

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Stage 1: System Environment & Diagnostic Report" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# OS Information
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "[1] Operating System:" -ForegroundColor Yellow
Write-Host "    Caption:        $($os.Caption)"
Write-Host "    Version:        $($os.Version) (Build $($os.BuildNumber))"
Write-Host "    Architecture:   $($os.OSArchitecture)"

# Disk Space
Write-Host "`n[2] Storage Drive Analysis:" -ForegroundColor Yellow
Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    $free = [math]::round($_.Free/1GB, 2)
    $used = [math]::round($_.Used/1GB, 2)
    $color = if ($free -lt 5) { "Red" } else { "Green" }
    Write-Host "    Drive $($_.Name): Free = $free GB | Used = $used GB" -ForegroundColor $color
}

# Python
Write-Host "`n[3] Python Environment:" -ForegroundColor Yellow
$pyPath = (Get-Command python -ErrorAction SilentlyContinue).Source
Write-Host "    System Python:  $pyPath"
$pyVer = python --version 2>&1
Write-Host "    Version:        $pyVer"
$venvPy = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    Write-Host "    Virtual Env:    $venvPy (Detected)" -ForegroundColor Green
    & $venvPy -c "import django, watchdog, win32api, scapy, dpkt; print('    Venv Modules:   Django, Watchdog, PyWin32, Scapy, DPKT all imported OK')"
} else {
    Write-Host "    Virtual Env:    Not found (Run install_requirements.ps1)" -ForegroundColor Red
}

# Git
Write-Host "`n[4] Git Environment:" -ForegroundColor Yellow
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    Write-Host "    Git Version:    $(git --version)" -ForegroundColor Green
} else {
    Write-Host "    Git:            Missing" -ForegroundColor Red
}

# Node & Expo GUI
Write-Host "`n[5] Node.js & React Native Tooling:" -ForegroundColor Yellow
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    Write-Host "    Node Version:   $(node --version)" -ForegroundColor Green
    Write-Host "    NPM Version:    $(npm --version)" -ForegroundColor Green
} else {
    Write-Host "    Node.js:        Missing" -ForegroundColor Red
}

# Wireshark / TShark
Write-Host "`n[6] Network Capture (Wireshark/TShark):" -ForegroundColor Yellow
$tsharkCandidatePaths = @(
    "D:\Aarya\Softwares\WireShark\tshark.exe",
    "C:\Program Files\Wireshark\tshark.exe"
)
$tsharkPath = $tsharkCandidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $tsharkPath) {
    $tsharkCmd = Get-Command tshark -ErrorAction SilentlyContinue
    if ($tsharkCmd) { $tsharkPath = $tsharkCmd.Source }
}
if ($tsharkPath) {
    Write-Host "    TShark Path:    $tsharkPath" -ForegroundColor Green
    $tsharkVer = & $tsharkPath --version | Select-Object -First 1
    Write-Host "    TShark Version: $tsharkVer" -ForegroundColor Green
} else {
    Write-Host "    TShark:         Not found (Offline PCAP parsing enabled via Scapy/DPKT)" -ForegroundColor Yellow
}

# Android Studio & ADB
Write-Host "`n[7] Android Studio, SDK & ADB Diagnostics:" -ForegroundColor Yellow
$studioPath = "D:\Aarya\Softwares\Android Studio\bin\studio64.exe"
if (Test-Path $studioPath) {
    Write-Host "    Android Studio: $studioPath (Installed)" -ForegroundColor Green
} else {
    Write-Host "    Android Studio: Check custom install path" -ForegroundColor Yellow
}

$adbCandidatePaths = @(
    "C:\Users\AASTHA\AppData\Local\Android\Sdk\platform-tools\adb.exe",
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
)
$adbPath = $adbCandidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $adbPath) {
    $adbCmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($adbCmd) { $adbPath = $adbCmd.Source }
}
if ($adbPath) {
    Write-Host "    ADB Path:       $adbPath" -ForegroundColor Green
    $adbVer = & $adbPath version | Select-Object -First 1
    Write-Host "    ADB Version:    $adbVer" -ForegroundColor Green
} else {
    Write-Host "    ADB:            Configured at C:\Users\AASTHA\AppData\Local\Android\Sdk\platform-tools\adb.exe" -ForegroundColor Yellow
}

# Windows USB Event Channels
Write-Host "`n[8] Windows USB / PnP Channels:" -ForegroundColor Yellow
$channels = @(
    "Microsoft-Windows-Kernel-PnP/Device Management",
    "Microsoft-Windows-Kernel-PnP/Configuration",
    "Microsoft-Windows-UserPnp/DeviceInstall",
    "Microsoft-Windows-Storage-ClassPnP/Operational",
    "Microsoft-Windows-DriverFrameworks-UserMode/Operational"
)
foreach ($ch in $channels) {
    $log = Get-WinEvent -ListLog $ch -ErrorAction SilentlyContinue
    if ($log) {
        $status = if ($log.IsEnabled) { "Enabled ($($log.RecordCount) records)" } else { "Disabled" }
        Write-Host "    ${ch}: $status" -ForegroundColor $(if ($log.IsEnabled) { "Green" } else { "DarkYellow" })
    } else {
        Write-Host "    ${ch}: Unavailable" -ForegroundColor Red
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  Diagnostic Check Complete!" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
