# Stage 1 Testing & Verification Report

**Date of Execution:** November 10, 2026  
**Environment:** Windows 11 AMD64 | Python 3.14.8 | Django 6.1.3 | Pytest 9.2.0  
**Test Framework:** Pytest with `pytest-django`  
**Overall Result:** **34 Passed / 0 Failed (100% Pass Rate)**  

---

## 1. Test Execution Summary

```
============================= test session starts =============================
platform win32 -- Python 3.14.8, pytest-9.2.0, pluggy-1.7.0
django: version: 6.1.3, settings: forensics_core.settings
rootdir: C:\Users\Aman\Desktop\Digital forensic\Network-Log-Intelligence
configfile: pytest.ini
plugins: django-4.14.0

tests/test_android_collector.py::test_android_collector_store_package_observation PASSED [  2%]
tests/test_file_collector.py::test_file_event_apk_observation_differentiated PASSED [  5%]
tests/test_integration.py::test_evidence_file_integrity_verification PASSED [  8%]
tests/test_integration.py::test_unified_timeline_filtering_and_pagination PASSED [ 11%]
tests/test_integration.py::test_csv_export PASSED                        [ 14%]
tests/test_integration.py::test_dashboard_views_http_status PASSED       [ 17%]
tests/test_integration.py::test_api_endpoints_http_status PASSED         [ 20%]
tests/test_network_collector.py::test_network_collector_import_pcap PASSED [ 23%]
tests/test_usb_collector.py::test_usb_collector_store_event PASSED       [ 26%]
tests/test_android_collector.py::test_get_adb_path_fallback PASSED       [ 29%]
tests/test_android_collector.py::test_parse_package_snapshot_lines PASSED [ 32%]
tests/test_android_collector.py::test_snapshot_diff_detection PASSED     [ 35%]
tests/test_file_collector.py::test_compute_sha256_valid_file PASSED      [ 38%]
tests/test_file_collector.py::test_compute_sha256_nonexistent_file PASSED [ 41%]
tests/test_file_collector.py::test_wait_for_stability_stable_file PASSED [ 44%]
tests/test_file_collector.py::test_file_collector_initialization PASSED  [ 47%]
tests/test_network_collector.py::test_parse_valid_synthetic_pcap PASSED  [ 50%]
tests/test_network_collector.py::test_parse_empty_pcap PASSED            [ 52%]
tests/test_network_collector.py::test_parse_malformed_pcap PASSED        [ 55%]
tests/test_normalizer.py::test_normalize_valid_iso_timestamp PASSED      [ 58%]
tests/test_normalizer.py::test_normalize_naive_datetime PASSED           [ 61%]
tests/test_normalizer.py::test_normalize_timestamp_no_fabrication PASSED [ 64%]
tests/test_normalizer.py::test_normalize_epoch_timestamp PASSED          [ 67%]
tests/test_normalizer.py::test_normalize_event_type_mapping PASSED       [ 70%]
tests/test_normalizer.py::test_normalize_device_id PASSED                [ 73%]
tests/test_normalizer.py::test_normalize_source PASSED                   [ 76%]
tests/test_normalizer.py::test_normalize_event_dictionary PASSED         [ 79%]
tests/test_usb_collector.py::test_extract_vid_pid PASSED                 [ 82%]
tests/test_usb_collector.py::test_usb_event_id_classification PASSED     [ 85%]
tests/test_validator.py::test_validate_complete_valid_event PASSED       [ 88%]
tests/test_validator.py::test_validate_missing_required_timestamp PASSED [ 91%]
tests/test_validator.py::test_validate_missing_collector_name PASSED     [ 94%]
tests/test_validator.py::test_validate_future_timestamp_warning PASSED   [ 97%]
tests/test_validator.py::test_validate_missing_optional_fields_warning PASSED [100%]

============================= 34 passed in 2.96s ==============================
```

---

## 2. Test Category Breakdown

| Suite | Target Module | Scope & Objectives | Result |
| :--- | :--- | :--- | :--- |
| `test_normalizer.py` | `processing/normalizer.py` | Timezone awareness, ISO parsing, alias mapping, no-fabrication rule for corrupt timestamps. | **8 / 8 Passed** |
| `test_validator.py` | `processing/validator.py` | Mandatory field enforcement, future drift warning, partial metadata acceptance. | **5 / 5 Passed** |
| `test_file_collector.py` | `collectors/file_collector.py` | SHA-256 calculation, file stability wait, temporary `.crdownload` handling, APK file observation. | **5 / 5 Passed** |
| `test_network_collector.py` | `collectors/network_collector.py` | DPKT PCAP parsing, protocol/port/IP/DNS/flag extraction, empty/malformed capture resilience. | **4 / 4 Passed** |
| `test_usb_collector.py` | `collectors/usb_collector.py` | Regex VID/PID parsing, Event ID connect/disconnect mapping, Device model creation. | **3 / 3 Passed** |
| `test_android_collector.py` | `collectors/android_collector.py` | ADB binary discovery, package list parsing, before/after snapshot diffing. | **4 / 4 Passed** |
| `test_integration.py` | Full Pipeline | Evidence chain-of-custody, SHA-256 tamper verification, timeline filtering/search, CSV export, 9 dashboard views, 4 REST API endpoints. | **5 / 5 Passed** |

---

## 3. End-to-End Functional Verification Record

An end-to-end integration test was conducted against `forensics.db`:
- **Evidence Import**: `sample_traffic.pcap` ingested by `NetworkCollector`.
- **Result**: Created `EVD-49C4E5075777` with SHA-256 `f244b8272ac0751927faba62c58513038a3bc040c9f79f6ee8f23fd417b9a5c5`.
- **Packet Ingestion**: 5 network events parsed, validated, and linked to evidence.
- **Cryptographic Verification**: `EvidenceRepository.verify_integrity()` executed and returned `verified: True`.
- **Timeline Query & Export**: Retrieved chronologically sorted events and exported valid RFC-4180 CSV with correct headers.
- **State Reset**: Database successfully reset cleanly to 0 records for operational deployment.

