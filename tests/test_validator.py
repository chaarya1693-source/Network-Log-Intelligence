"""
tests/test_validator.py — Unit tests for event validation rules.
Verifies valid, invalid, and warning validation outcomes.
"""
from datetime import datetime, timezone, timedelta
import pytest
from processing.validator import validate_event


def test_validate_complete_valid_event():
    """Test fully populated, valid event receives 'valid' status."""
    event = {
        "event_timestamp": datetime.now(timezone.utc),
        "event_type": "network_packet",
        "source": "pcap:sample.pcap",
        "collector_name": "NetworkCollector",
        "source_record_id": "frame#1",
        "description": "TCP 192.168.1.1:80 -> 192.168.1.2:5000",
        "metadata": {"frame": 1},
    }
    assert validate_event(event) == "valid"


def test_validate_missing_required_timestamp():
    """Test missing event_timestamp produces 'invalid' status."""
    event = {
        "event_timestamp": None,
        "event_type": "file_created",
        "source": "watchdog",
        "collector_name": "FileCollector",
    }
    assert validate_event(event) == "invalid"


def test_validate_missing_collector_name():
    """Test missing collector_name produces 'invalid' status."""
    event = {
        "event_timestamp": datetime.now(timezone.utc),
        "event_type": "file_created",
        "source": "watchdog",
        "collector_name": "",
    }
    assert validate_event(event) == "invalid"


def test_validate_future_timestamp_warning():
    """Test event with timestamp far in the future (>5 minutes) generates 'warning'."""
    far_future = datetime.now(timezone.utc) + timedelta(minutes=10)
    event = {
        "event_timestamp": far_future,
        "event_type": "usb_connected",
        "source": "System",
        "collector_name": "USBCollector",
        "source_record_id": "PnP#1",
        "description": "USB device",
        "metadata": {},
    }
    assert validate_event(event) == "warning"


def test_validate_missing_optional_fields_warning():
    """Test missing description or source_record_id generates 'warning' instead of hard invalid."""
    event = {
        "event_timestamp": datetime.now(timezone.utc),
        "event_type": "apk_file_observed",
        "source": "watchdog",
        "collector_name": "FileCollector",
        "source_record_id": "",
        "description": "",
        "metadata": {},
    }
    assert validate_event(event) == "warning"

