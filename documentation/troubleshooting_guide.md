# Troubleshooting & Diagnostic Guide — Stage 1

This guide covers common issues, error messages, and remediation steps.

---

## 1. Virtual Environment & Python Issues

### Issue: `python.exe: No module named pytest` or `ModuleNotFoundError`
- **Cause**: Command was run against the global system Python instead of the isolated virtual environment `.venv`.
- **Solution**: Always run commands via the project's virtual environment binary:
  ```powershell
  .\.venv\Scripts\python.exe -m <command>
  ```

### Issue: PowerShell execution policy blocks `.venv\Scripts\Activate.ps1`
- **Cause**: Windows client execution policy restricts script execution for non-signed scripts.
- **Solution**: Do not alter global execution policies. Either bypass per process or invoke the executable directly:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\.venv\Scripts\Activate.ps1
  # OR directly invoke:
  .\.venv\Scripts\python.exe manage.py runserver
  ```

---

## 2. Windows USB & Event Log Issues

### Issue: `Get-WinEvent: Attempted to perform an unauthorized operation`
- **Cause**: Windows 11 limits read access to specific kernel operational event logs for non-elevated user accounts.
- **Remediation**:
  1. The `USBCollector` automatically falls back to WMI queries (`Win32_PnPEntity`, `Win32_USBHub`) which do not require elevated privileges.
  2. For offline testing without administrator access, run tests using the sample fixture:
     ```powershell
     .\.venv\Scripts\python.exe -m pytest tests/test_usb_collector.py
     ```

---

## 3. Network Collection & PCAP Parsing Issues

### Issue: `tshark: command not found`
- **Status**: Expected when Wireshark is not installed or not in system `PATH`.
- **Remediation**: Stage 1 features a pure Python PCAP/PCAPNG parser powered by `dpkt` and `scapy`. Offline PCAP ingestion functions completely without TShark installed.
- **If Live Capture is Needed**: Install official Wireshark from `https://www.wireshark.org/` and specify the path in `.env`:
  ```ini
  TSHARK_PATH=C:\Program Files\Wireshark\tshark.exe
  ```

---

## 4. Android & ADB Issues

### Issue: `ADB not found` or `detect_devices returned empty`
- **Cause**: Android SDK platform-tools are either not in standard paths or no Android emulator is currently running.
- **Remediation**:
  1. If Android Studio is installed, set the exact path in `.env`:
     ```ini
     ADB_PATH=C:\Users\Aman\AppData\Local\Android\Sdk\platform-tools\adb.exe
     ```
  2. Start an Android Virtual Device (AVD) from Android Studio.
  3. Verify ADB sees the emulator:
     ```powershell
     adb devices
     ```
  4. Unit tests in `tests/test_android_collector.py` run independently using mock package snapshots and do not require a live emulator.

---

## 5. Web Dashboard Port Conflicts

### Issue: `Error: That port is already in use.`
- **Cause**: Another service or a previous instance of Django is bound to port 8000.
- **Solution**: Specify an alternative port using the `-Port` argument:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\run_project.ps1 -Port 8080
  ```

