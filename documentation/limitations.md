# Forensic & Technical Limitations — Stage 1

In accordance with strict forensic engineering standards, all known technical boundaries and non-claims of Stage 1 are disclosed below.

---

## 1. Scope & Functional Boundaries

1. **Stage 1 Implementation Only**:
   - Stage 1 is restricted strictly to metadata collection, normalization, cryptographic evidence vaulting, and unified timeline reconstruction.
   - Stage 1 **does NOT** implement AI anomaly detection, machine learning malware classifiers, risk scores, or DoS defense mechanisms (these belong strictly to Stages 2, 3, and 4).
2. **No Claim of Legal Certification**:
   - This software is a research and digital forensic analysis framework. It is not an ISO/IEC 17025 accredited legal acquisition tool.

---

## 2. Collector-Specific Limitations

### 2.1 USB Collector
- **No File Transfer Detection**: A `usb_connected` event proves only that a physical or logical USB device was enumerated by the Windows operating system. It **does NOT prove** that files were read, written, copied, or exfiltrated.
- **Kernel Log Accessibility**: On standard Windows 11 Home installations, detailed user-mode driver logs (`DriverFrameworks-UserMode/Operational`) are disabled by default and require administrative privileges to enable.

### 2.2 File Activity Collector
- **Dedicated Scope**: Monitors only `test_data/watched_downloads/`. It does not monitor system-wide file modifications.
- **Origin URL Unknown**: Filesystem observers (such as Python `watchdog`) cannot inherently know the remote origin URL of a downloaded file unless separate browser history or alternate data streams (`Zone.Identifier`) corroborate it. Remote URLs are explicitly marked `unknown` when unavailable.
- **No APK Execution**: APK files observed in the monitored directory are hashed and recorded. They are **never executed** on the host operating system.

### 2.3 Android Emulator Collector
- **Snapshot Diffing vs Continuous Auditing**: ADB package monitoring relies on polling snapshot diffs. High-speed transient install/uninstall cycles that occur within a single polling interval may not be captured.
- **No Personal Phone Access**: The collector strictly refuses to interact with, root, unlock, or inspect personal Android phones. It operates exclusively against the Android Studio Emulator.

### 2.4 Network Collector
- **No TLS/HTTPS Decryption**: Encrypted traffic (HTTPS, TLS 1.3, SSH) is inspected strictly at the transport and network layer (IPs, ports, packet sizes, TCP flags). Plaintext payloads and credentials are never decrypted or extracted.
- **Switched Network Invisibility**: In modern switched Ethernet and Wi-Fi networks, a computer's network interface cannot observe unicast traffic traversing between other workstations and the access point.

