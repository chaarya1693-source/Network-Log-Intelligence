"""
tests/test_integration.py — End-to-end integration tests for Stage 1.
Tests database relationships, evidence integrity verification,
unified timeline filtering, CSV export, and Django dashboard views.
"""
from datetime import datetime, timezone, timedelta
import io
import os
import pytest
from django.test import Client
from django.utils import timezone as dj_tz
from database_app.models import Device, EvidenceFile, Event, CollectorRun
from database.repositories import EvidenceRepository, EventRepository, CollectorRunRepository


@pytest.mark.django_db
def test_evidence_file_integrity_verification(tmp_path):
    """
    Test EvidenceFile chain-of-custody and SHA-256 integrity verification:
    1. Create evidence file on disk
    2. Register in EvidenceRepository
    3. Verify integrity returns match=True
    4. Mutate file content
    5. Verify integrity returns match=False (tamper detection)
    """
    evidence_path = tmp_path / "packet_capture.pcap"
    content = b"ORIGINAL_FORENSIC_CAPTURE_DATA_V1"
    evidence_path.write_bytes(content)

    import hashlib
    original_hash = hashlib.sha256(content).hexdigest()

    evidence = EvidenceRepository.create_evidence(
        original_filename="packet_capture.pcap",
        file_path=str(evidence_path),
        evidence_type="pcap",
        sha256_hash=original_hash,
        file_size=len(content),
        acquisition_timestamp=dj_tz.now(),
        collector_name="NetworkCollector",
    )

    # 1. Verification of untampered evidence
    result1 = EvidenceRepository.verify_integrity(evidence.evidence_id)
    assert result1["verified"] is True
    assert result1["computed_hash"] == original_hash

    # Refresh from DB
    evidence.refresh_from_db()
    assert evidence.is_verified is True
    assert evidence.verification_timestamp is not None

    # 2. Tampering test: modify the file on disk
    evidence_path.write_bytes(b"TAMPERED_FORENSIC_CAPTURE_DATA_V2")
    result2 = EvidenceRepository.verify_integrity(evidence.evidence_id)
    assert result2["verified"] is False
    assert result2["computed_hash"] != original_hash

    evidence.refresh_from_db()
    assert evidence.is_verified is False


@pytest.mark.django_db
def test_unified_timeline_filtering_and_pagination():
    """
    Test EventRepository timeline query with multi-source events,
    filtering by event_type, date range, search query, and pagination.
    """
    now = dj_tz.now()
    # Create device
    dev = Device.objects.create(device_id="USB\\VID_0781&PID_5583", device_type="usb")

    # Create events of various types and timestamps
    e1 = Event.objects.create(
        event_timestamp=now - timedelta(hours=3),
        event_type="usb_connected",
        source="Kernel-PnP",
        device=dev,
        description="USB drive connected",
        collector_name="USBCollector",
        validation_status="valid",
    )
    e2 = Event.objects.create(
        event_timestamp=now - timedelta(hours=2),
        event_type="file_created",
        source="watchdog",
        description="Report.pdf downloaded",
        collector_name="FileCollector",
        validation_status="valid",
    )
    e3 = Event.objects.create(
        event_timestamp=now - timedelta(hours=1),
        event_type="network_packet",
        source="pcap:capture.pcap",
        description="TCP 192.168.1.50:443 -> 1.1.1.1:443",
        collector_name="NetworkCollector",
        validation_status="valid",
    )

    # 1. Unfiltered timeline: all 3 events ordered descending
    res_all = EventRepository.get_timeline(page=1, per_page=10)
    assert res_all["total"] == 3
    event_list = list(res_all["events"])
    assert event_list[0].id == e3.id
    assert event_list[1].id == e2.id
    assert event_list[2].id == e1.id

    # 2. Filter by event_type
    res_usb = EventRepository.get_timeline(event_type="usb_connected")
    assert res_usb["total"] == 1
    assert res_usb["events"][0].id == e1.id

    # 3. Filter by search text
    res_search = EventRepository.get_timeline(search="Report.pdf")
    assert res_search["total"] == 1
    assert res_search["events"][0].id == e2.id

    # 4. Filter by date range
    res_time = EventRepository.get_timeline(
        start_dt=now - timedelta(hours=2, minutes=30),
        end_dt=now - timedelta(minutes=30),
    )
    assert res_time["total"] == 2


@pytest.mark.django_db
def test_csv_export():
    """Test exporting event timeline to CSV format contains correct headers and records."""
    now = dj_tz.now()
    Event.objects.create(
        event_timestamp=now,
        event_type="usb_connected",
        source="System",
        description="USB test export",
        collector_name="USBCollector",
        validation_status="valid",
    )
    qs = Event.objects.all()
    csv_str = EventRepository.export_to_csv(qs)
    assert "event_id,event_timestamp,event_type,source,description" in csv_str
    assert "usb_connected" in csv_str
    assert "USB test export" in csv_str


@pytest.mark.django_db
def test_dashboard_views_http_status():
    """Test all 9 dashboard pages return HTTP 200 OK and render without crashing."""
    client = Client()
    urls = [
        "/",
        "/network/",
        "/usb/",
        "/files/",
        "/android/",
        "/timeline/",
        "/evidence/",
        "/collectors/",
        "/reports/",
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, f"URL {url} failed with status {response.status_code}"


@pytest.mark.django_db
def test_api_endpoints_http_status():
    """Test REST API endpoints return HTTP 200 and application/json."""
    client = Client()
    endpoints = [
        "/api/stats/",
        "/api/events/",
        "/api/evidence/",
        "/api/collectors/",
    ]
    for ep in endpoints:
        response = client.get(ep)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)

