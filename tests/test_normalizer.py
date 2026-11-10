"""
tests/test_normalizer.py — Unit tests for forensic normalization pipeline.
Verifies timezone normalization, timestamp integrity (no fabrication),
event type mapping, and string sanitization.
"""
from datetime import datetime, timezone
import pytest
from processing.normalizer import (
    normalize_timestamp,
    normalize_event_type,
    normalize_device_id,
    normalize_source,
    normalize_event,
)


def test_normalize_valid_iso_timestamp():
    """Test standard ISO-8601 UTC timestamp parses properly."""
    raw = "2026-11-10T12:00:00Z"
    dt = normalize_timestamp(raw)
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2026
    assert dt.month == 11
    assert dt.day == 10
    assert dt.hour == 12


def test_normalize_naive_datetime():
    """Test naive datetime object gets converted to UTC-aware datetime."""
    naive = datetime(2026, 11, 10, 10, 30, 0)
    aware = normalize_timestamp(naive)
    assert aware.tzinfo == timezone.utc
    assert aware.hour == 10


def test_normalize_timestamp_no_fabrication():
    """
    Test that invalid or missing timestamps return None and are NEVER
    silently fabricated into current time (Forensic Rule).
    """
    assert normalize_timestamp(None) is None
    assert normalize_timestamp("invalid-date-string-123") is None
    assert normalize_timestamp("") is None


def test_normalize_epoch_timestamp():
    """Test numeric unix epoch conversion."""
    epoch = 1700000000.0
    dt = normalize_timestamp(epoch)
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_normalize_event_type_mapping():
    """Test raw aliases map to canonical Common Event Model types."""
    assert normalize_event_type("usb_connect") == "usb_connected"
    assert normalize_event_type("usb_disconnect") == "usb_disconnected"
    assert normalize_event_type("file_create") == "file_created"
    assert normalize_event_type("file_modify") == "file_modified"
    assert normalize_event_type("download_observed") == "file_download_observed"
    assert normalize_event_type("apk_observed") == "apk_file_observed"
    assert normalize_event_type("network") == "network_packet"
    # Unmapped valid types remain as-is
    assert normalize_event_type("network_packet") == "network_packet"


def test_normalize_device_id():
    """Test device IDs are stripped, uppercased and length limited."""
    assert normalize_device_id("  usb_vid_0781_pid_5583  ") == "USB_VID_0781_PID_5583"
    assert normalize_device_id(None) == ""


def test_normalize_source():
    """Test source strings are sanitized and whitespace trimmed."""
    assert normalize_source("  pcap:sample_traffic.pcap  ") == "pcap:sample_traffic.pcap"
    assert normalize_source(None) == "unknown"


def test_normalize_event_dictionary():
    """Test normalizing a complete raw event dictionary."""
    raw = {
        "event_timestamp": "2026-11-10T08:00:00Z",
        "event_type": "usb_connect",
        "source": "Microsoft-Windows-Kernel-PnP",
        "description": "USB device connected",
        "source_record_id": "PnP#101",
        "collector_name": "USBCollector",
        "metadata": {"test": 1},
    }
    norm = normalize_event(raw)
    assert norm["event_type"] == "usb_connected"
    assert norm["source"] == "Microsoft-Windows-Kernel-PnP"
    assert norm["event_timestamp"].year == 2026
    assert norm["metadata"]["test"] == 1

