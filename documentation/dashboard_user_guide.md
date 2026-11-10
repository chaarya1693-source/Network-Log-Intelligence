# Dashboard User Guide — Stage 1

The Stage 1 Forensic Dashboard is a responsive web application built with Django, HTML5, CSS, and Bootstrap 5.3, supporting both Dark and Light theme modes.

---

## 1. Accessing the Dashboard

1. Launch the server:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\run_project.ps1 -Port 8000
   ```
2. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000/
   ```

---

## 2. Navigating the 9 Interfaces

### 2.1 Overview Dashboard (`/`)
- **Metric Cards**: Total Events, USB Events, Network Packets, Evidence Files, File Events, Android Events, APKs Observed, Active Collectors.
- **Recent Telemetry Table**: Real-time list of the 10 most recent observations across all collectors.
- **Collector Session Status**: Current status of active and recent collector runs.

### 2.2 Network Activity (`/network/`)
- Filterable table of captured network packets.
- Displays: Frame #, Timestamp, Source IP:Port, Destination IP:Port, Protocol badge (TCP, UDP, ICMP), Packet Length, TCP Flags, DNS queries, and Evidence Link.
- Real-time search by IP or port.

### 2.3 USB Activity (`/usb/`)
- Dedicated log of USB hardware arrival and removal events.
- Filter by `usb_connected` or `usb_disconnected`.
- Displays: Hardware ID, Vendor ID (VID), Product ID (PID), Source Channel, Device Class, and Timestamp.

### 2.4 File Activity (`/files/`)
- Records file creation, modification, move, and download completion inside `test_data/watched_downloads/`.
- Displays: Filename, Extension, File Size, SHA-256 Hash, Observed Filesystem Timestamps, and Associated Evidence ID.

### 2.5 Android Activity (`/android/`)
- Displays mobile telemetry from connected Android emulators.
- Clearly differentiates between:
  - `apk_file_observed` (Host observation of downloaded APK).
  - `apk_installed` (Newly detected package on emulator).
  - `android_package_observed` (Baseline snapshot packages).
- Package details include Version Name, Version Code, and Target Device Serial.

### 2.6 Unified Chronological Timeline (`/timeline/`)
The primary investigative page of Stage 1:
- **Chronological Sorting**: Default newest-first display across all 4 collector sources.
- **Filters**:
  - Event Type dropdown.
  - Source filter.
  - Date / Time range selector.
  - Text search across descriptions and metadata.
- **Pagination**: Configured to 25 events per page.
- **Evidence Reference**: Every entry links directly back to its source evidence file.
- **Export to CSV**: Download filtered results immediately.

### 2.7 Evidence Management (`/evidence/`)
- Master chain-of-custody inventory.
- Lists Evidence ID (`EVD-...`), Original Filename, Evidence Type badge, File Size, SHA-256 Hash, Acquisition Timestamp, and Verification Status.
- One-click **Verify Hash** button executes live recalculation of the cryptographic SHA-256 checksum on disk.

### 2.8 Collector Management (`/collectors/`)
- Collector health cards for `USBCollector`, `FileCollector`, `NetworkCollector`, and `AndroidCollector`.
- Displays session status (`running`, `idle`, `failed`), total events harvested, and total error count.
- Collector audit log table displaying historical sessions from the `collector_runs` table.

### 2.9 Forensic Reports (`/reports/`)
- High-level event distribution across all categories.
- Interactive Chart.js visualization of event types.
- One-click **Export All CSV** button for full timeline data extraction.

