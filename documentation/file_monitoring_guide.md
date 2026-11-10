# File Activity Monitoring Guide — Stage 1

This document explains the watchdog-based filesystem monitoring module, temporary file handling, and APK observation.

---

## 1. Monitored Directory Isolation

To protect personal files and maintain strict forensic boundaries, file monitoring is confined **exclusively** to:
```
test_data/watched_downloads/
```
The collector **never** scans or hooks user directories such as `C:\Users\Aman\Downloads` or `Desktop`.

---

## 2. Event Types & Classification

The `FileCollector` maps observed filesystem actions into canonical event types:

| Event Type | Condition | Evidence Generated |
| :--- | :--- | :--- |
| `file_created` | File initially created on disk. | `EvidenceFile` (file) |
| `file_modified` | Existing file content changed. | Updated metadata |
| `file_moved` | File renamed or moved. | Rename audit trail |
| `file_download_observed` | Non-temp file stabilizes in watched folder. | `EvidenceFile` (file) |
| `apk_file_observed` | File with `.apk` extension arrives. | `EvidenceFile` (apk) |

---

## 3. Temporary Download Handling & Stability

Browsers frequently create temporary staging files during download operations:
- Google Chrome / Edge: `.crdownload`
- Mozilla Firefox: `.part`
- Generic downloaders: `.tmp`, `.partial`, `.download`

### How the Collector Handles Temp Files:
1. When a `.crdownload` file is created, the collector suppresses full evidence creation.
2. When the browser finishes writing and renames `payload.pdf.crdownload` to `payload.pdf`, watchdog fires `on_moved`.
3. The collector invokes `wait_for_stability()`:
   - Polls file size every 1 second until the file size remains identical across consecutive samples.
   - Computes the cryptographic `SHA-256` hash of the completed file.
   - Stores the event as `file_download_observed` (or `apk_file_observed` if `.apk`).

---

## 4. Controlled Testing Procedure

### Step 1: Start File Collector
```powershell
.\.venv\Scripts\python.exe main.py --collectors file
```

### Step 2: Simulate File Download
Copy or create a harmless document in `test_data/watched_downloads/`:
```powershell
# 1. Create a simulated download
Copy-Item test_data\watched_downloads\sample_document.txt test_data\watched_downloads\test_download.txt
```

### Step 3: Simulate Temporary File Rename
```powershell
# Create temp file
Set-Content -Path test_data\watched_downloads\report.pdf.crdownload -Value "Staging payload"
Start-Sleep -Seconds 2
# Rename to final
Rename-Item -Path test_data\watched_downloads\report.pdf.crdownload -NewName report.pdf
```

### Step 4: Verify in Dashboard
Navigate to `http://127.0.0.1:8000/files/`:
- `report.pdf` is recorded with `file_download_observed`.
- Full SHA-256 hash is visible.
- File size is recorded accurately.

---

## 5. APK Observation Safety Rule

When an `.apk` file arrives in `test_data/watched_downloads/`:
- The collector extracts file size and computes SHA-256.
- The collector creates an `apk_file_observed` event.
- **Strict Rule**: The system **NEVER opens, launches, or executes** the APK on the host computer.

