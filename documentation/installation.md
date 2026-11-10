# Installation & Deployment Guide — Stage 1

This guide covers system prerequisites, virtual environment creation, package installation, and configuration for Stage 1.

---

## 1. Prerequisites

- **Operating System**: Windows 10/11 64-bit (AMD64)
- **Python**: Python 3.12, 3.13, or 3.14 (Verified active on Python 3.14.8)
- **Git**: Git for Windows 2.40+ (Verified active on 2.54.0)
- **PowerShell**: Windows PowerShell 5.1+ or PowerShell 7+
- **Node.js (Optional)**: Node.js v18+ and NPM (for external Expo GUI if deployed)

---

## 2. Automated Installation

Run the PowerShell installer script from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_requirements.ps1
```

The script performs the following actions:
1. Detects system Python and checks compatibility.
2. Creates the isolated virtual environment `.venv\`.
3. Upgrades `pip` and installs dependencies pinned in `requirements.txt`.
4. Verifies critical imports (`django`, `watchdog`, `win32api`, `dotenv`, `yaml`, `dpkt`, `scapy`, `pytest`).
5. Checks optional Node.js / NPM availability.

---

## 3. Manual Installation (Alternative)

If preferred, setup can be performed step-by-step:

```powershell
# 1. Create Python virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 4. Install required packages
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 5. Verify core modules
.\.venv\Scripts\python.exe -c "import django, watchdog, win32api, dotenv, yaml, dpkt, scapy, pytest; print('All core modules verified!')"
```

---

## 4. Configuration Setup

Copy `.env.example` to `.env` if not already present:

```powershell
Copy-Item .env.example .env
```

Customize settings in `.env`:
```ini
DJANGO_SECRET_KEY=forensics-stage1-local-dev-key-92847aefbc012874bc
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,10.0.2.2

# Tool Paths (Optional: If left blank, tools auto-detect via PATH or standard directories)
TSHARK_PATH=
ANDROID_SDK_PATH=
ADB_PATH=
ANDROID_STUDIO_PATH=

PROJECT_TIMEZONE=Asia/Kolkata
```

---

## 5. Database Initialization

The SQLite database `forensics.db` is migrated automatically:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Verify system health:
```powershell
.\.venv\Scripts\python.exe manage.py check
```

---

## 6. Running the System

Start the orchestrator with all collectors and the web dashboard:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_project.ps1 -Port 8000
```

Access the dashboard at:
```
http://127.0.0.1:8000/
```

