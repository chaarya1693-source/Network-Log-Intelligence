# scripts/create_test_samples.py
# Generates harmless test fixtures for offline forensic testing

import json
import os
import zipfile

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Harmless test APK
apk_path = os.path.join(base_dir, 'test_data', 'android_samples', 'sample_harmless_test.apk')
with zipfile.ZipFile(apk_path, 'w') as z:
    z.writestr('AndroidManifest.xml', b'<manifest package="org.forensics.harmless.test"></manifest>')
    z.writestr('classes.dex', b'DEX_TEST_DUMMY_HARMLESS')
print(f'Created sample APK: {apk_path}')

# 2. Harmless files for watched_downloads
txt_path = os.path.join(base_dir, 'test_data', 'watched_downloads', 'sample_document.txt')
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write('This is a harmless forensic test document for file activity observation.\nTimestamp: 2026-11-10\n')

pdf_path = os.path.join(base_dir, 'test_data', 'watched_downloads', 'sample_report.pdf')
with open(pdf_path, 'wb') as f:
    f.write(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n162\n%%EOF')
print(f'Created sample files in watched_downloads: txt and pdf')

# 3. Controlled sample USB events JSON
usb_json_path = os.path.join(base_dir, 'test_data', 'usb_samples', 'sample_usb_events.json')
usb_events = [
    {
        'event_id': 400,
        'record_number': 1001,
        'time_generated': '2026-11-10T06:00:00Z',
        'source_name': 'Microsoft-Windows-Kernel-PnP',
        'computer': 'FORENSIC-WORKSTATION',
        'strings': ['USB\\VID_0781&PID_5583\\4C530001230411112233', 'SanDisk Ultra USB 3.0', 'DiskDrive']
    },
    {
        'event_id': 430,
        'record_number': 1002,
        'time_generated': '2026-11-10T06:15:00Z',
        'source_name': 'Microsoft-Windows-Kernel-PnP',
        'computer': 'FORENSIC-WORKSTATION',
        'strings': ['USB\\VID_0781&PID_5583\\4C530001230411112233', 'Device Removed']
    }
]
with open(usb_json_path, 'w', encoding='utf-8') as f:
    json.dump(usb_events, f, indent=2)
print(f'Created sample USB events JSON: {usb_json_path}')

