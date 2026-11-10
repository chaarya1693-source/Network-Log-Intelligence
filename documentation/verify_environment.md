# Environment Verification & Diagnostic Guide — Stage 1

This guide explains how to verify the host environment, audit available tools, and inspect forensic log channels.

---

## 1. Running the Diagnostic Script

Execute the automated environment diagnostic script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_environment.ps1
```

The script audits 8 specific environmental domains:
1. **Operating System**: Caption, build number, and AMD64/ARM architecture.
2. **Storage Drive Analysis**: Free and total space across available logical drives.
3. **Python Environment**: System Python path, version, and virtual environment status.
4. **Git Version**: Verification of Git binary.
5. **Node.js & Tooling**: Node.js and NPM versions.
6. **Network Capture (Wireshark/TShark)**: Detection of `tshark.exe` or confirmation of pure Python fallback (`dpkt` / `scapy`).
7. **Android Studio & ADB Diagnostics**: SDK, platform-tools, and `adb.exe` detection.
8. **Windows Event Log Channels**: Channel status (Enabled/Disabled) and record count for USB and PnP logs.

---

## 2. Windows USB / PnP Channel Reference

The USB Collector queries the following Windows Event Log channels:

| Event Log Channel | Default Status | Purpose |
| :--- | :--- | :--- |
| `Microsoft-Windows-Kernel-PnP/Device Management` | Enabled | Logs device arrivals (Event ID 400, 410, 420) and removals (Event ID 430, 440) with hardware IDs. |
| `Microsoft-Windows-Kernel-PnP/Configuration` | Enabled | Logs driver bindings and hardware configuration updates. |
| `Microsoft-Windows-UserPnp/DeviceInstall` | Enabled | Logs user-mode device installation procedures. |
| `Microsoft-Windows-Storage-ClassPnP/Operational` | Enabled | Captures USB Mass Storage class devices. |
| `Microsoft-Windows-DriverFrameworks-UserMode/Operational` | Disabled (Win 11) | High-detail user-mode driver logs (requires administrative enablement). |

### Fallback Mode
When user permissions prevent direct queries to `Microsoft-Windows-Kernel-PnP`, the system gracefully falls back to:
1. WMI / CIM queries (`Win32_PnPEntity`, `Win32_USBHub`) which require standard user privileges.
2. Controlled replay of historical export logs in `test_data/usb_samples/sample_usb_events.json`.

---

## 3. Storage Space Safety Guideline

Drive C: contains 240+ GB of free storage. To maintain workstation performance and protect user files:
- All generated evidence, PCAP captures, and database files reside inside the dedicated workspace folder:
  `C:\Users\Aman\Desktop\Digital forensic\Network-Log-Intelligence\evidence\`
- File system monitoring is strictly scoped to:
  `test_data/watched_downloads/`
- User personal folders (`C:\Users\Aman\Documents`, `Downloads`, `Desktop`) are **never** scanned or modified.

