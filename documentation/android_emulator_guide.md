# Android Emulator & Package Monitoring Guide — Stage 1

This document outlines Android Debug Bridge (ADB) interfacing, package snapshot comparison, and device safety guidelines.

---

## 1. Strict Device Safety Rules

1. **Personal Android Phone Protection**:
   - The user's personal Android phone is **never connected** to this project.
   - Rooting, bootloader unlocking, system tampering, and unknown APK installation on personal phones are **strictly prohibited**.
2. **Controlled Testing Environment**:
   - All mobile experiments are conducted strictly inside the **Android Studio Emulator** (AVD).
   - Only harmless, project-owned test packages are observed.

---

## 2. Distinction Between APK Concepts

Stage 1 maintains three distinct forensic concepts:

| Concept | Location | Event Type | Meaning |
| :--- | :--- | :--- | :--- |
| **APK File Observed** | Windows Host (`test_data/watched_downloads/`) | `apk_file_observed` | An APK file was downloaded or moved to the host computer. Does not indicate installation. |
| **Android Package Observed** | Android Emulator | `android_package_observed` | Existing third-party package detected during initial device snapshot. |
| **APK Installation Observed** | Android Emulator | `apk_installed` | A package appeared between consecutive ADB snapshots on the emulator. |

---

## 3. ADB Interface & Commands

The `AndroidCollector` communicates with the emulator using standard Android SDK tools:

### 3.1 Device Discovery
```bash
adb devices
```
*Discovers active emulator serial numbers (e.g. `emulator-5554`). The collector dynamically parses serial numbers and never assumes a hardcoded device.*

### 3.2 Third-Party Package Snapshot
```bash
adb -s emulator-5554 shell pm list packages -3
```
*Lists all user-installed (non-system) packages.*

### 3.3 Package Metadata Query
```bash
adb -s emulator-5554 shell dumpsys package <package_name>
```
*Extracts version name, version code, install time, and package signatures.*

---

## 4. Controlled Testing Procedure

### Step 1: Launch Android Emulator
Start your Android Studio Virtual Device from Android Studio Device Manager.
Verify ADB detects it:
```powershell
adb devices
```
Output:
```
List of devices attached
emulator-5554   device
```

### Step 2: Start Android Collector
```powershell
.\.venv\Scripts\python.exe main.py --collectors android
```
The collector establishes the baseline package snapshot for `emulator-5554`.

### Step 3: Install Harmless Test Package
With explicit approval, install the project-designated harmless test package:
```powershell
adb -s emulator-5554 install test_data\android_samples\sample_harmless_test.apk
```

### Step 4: Verify Detection
The collector executes its snapshot diff algorithm:
- Detects the new package `org.forensics.harmless.test`.
- Emits an `apk_installed` event with version metadata.
- Open `http://127.0.0.1:8000/android/` to inspect the record.

