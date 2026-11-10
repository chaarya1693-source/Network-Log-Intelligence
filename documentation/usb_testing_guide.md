# USB Collector Testing Guide — Stage 1

This document provides testing procedures, Windows Event Log references, and verification steps for the USB Collector.

---

## 1. Technical Background

The USB Collector monitors the Windows Plug and Play subsystem using `win32evtlog`.

### Event IDs and Meaning
- **400, 410, 420**: Device arrived / started / enumerated by kernel. Classified as `usb_connected`.
- **430, 440**: Device removed or disabled. Classified as `usb_disconnected`.

### VID / PID Extraction
Device strings typically follow the format:
```
USB\VID_0781&PID_5583\4C530001230411112233
```
The regex extractor in `collectors/usb_collector.py` parses:
- `VID`: `0781` (SanDisk Corporation)
- `PID`: `5583` (Ultra USB 3.0 Flash Drive)

---

## 2. Controlled Manual Testing Procedure

### Step 1: Start USB Collector
Run the orchestrator with the USB collector enabled:
```powershell
.\.venv\Scripts\python.exe main.py --collectors usb
```

### Step 2: Insert a Harmless USB Drive
1. Insert a harmless, project-designated USB flash drive into any USB port on your Windows host.
2. Observe terminal logs:
   ```
   [INFO] USBCollector: processed 1 new USB events
   [DEBUG] USBCollector: recorded usb_connected for USB\VID_...
   ```

### Step 3: Remove the USB Drive
1. Safely remove or unplug the USB flash drive.
2. Observe terminal logs:
   ```
   [INFO] USBCollector: processed 1 new USB events
   [DEBUG] USBCollector: recorded usb_disconnected for USB\VID_...
   ```

### Step 4: Verify in Dashboard
1. Open `http://127.0.0.1:8000/usb/`.
2. Verify:
   - Event Timestamp matches insertion time.
   - Event Type displays `usb_connected` (badge green) and `usb_disconnected` (badge red).
   - Vendor ID and Product ID are populated.
   - Device description shows hardware class.

---

## 3. Offline Testing via Sample Fixture

For automated CI/CD or offline workstations where live USB insertion is unavailable, use the controlled sample fixture:
`test_data/usb_samples/sample_usb_events.json`

Run the automated test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_usb_collector.py
```

---

## 4. Important Forensic Caveat

> [!WARNING]
> A `usb_connected` event proves **only** that a USB physical or logical device was enumerated by the Windows operating system. It **does NOT prove** that files were copied, modified, exfiltrated, or read from or to the USB device. The system never claims file transfer without separate, corroborated filesystem evidence.

