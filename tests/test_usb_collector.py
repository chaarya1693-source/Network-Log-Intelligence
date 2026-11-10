"""
tests/test_usb_collector.py — Unit tests for Windows USB/PnP collector.
Verifies VID/PID extraction, connection/disconnection event classification,
and event model persistence.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from collectors.usb_collector import USBCollector, _extract_vid_pid, USB_CONNECT_IDS, USB_DISCONNECT_IDS


def test_extract_vid_pid():
    """Test regex extraction of Vendor ID and Product ID."""
    hw_id = "USB\\VID_0781&PID_5583\\4C530001230411112233"
    vid, pid = _extract_vid_pid(hw_id)
    assert vid == "0781"
    assert pid == "5583"

    hw_id_lower = "usb\\vid_05ac&pid_12a8\\123456"
    vid, pid = _extract_vid_pid(hw_id_lower)
    assert vid == "05AC"
    assert pid == "12A8"

    no_match = "ACPI\\VEN_PNP&DEV_0A08"
    vid, pid = _extract_vid_pid(no_match)
    assert vid == ""
    assert pid == ""


def test_usb_event_id_classification():
    """Test Windows Event IDs map properly to connect and disconnect."""
    assert 400 in USB_CONNECT_IDS
    assert 410 in USB_CONNECT_IDS
    assert 430 in USB_DISCONNECT_IDS
    assert 440 in USB_DISCONNECT_IDS


@pytest.mark.django_db
def test_usb_collector_store_event():
    """Test persisting USB connected and disconnected events creates Device and Event records."""
    collector = USBCollector({"usb_poll_interval_seconds": 1})
    collector.initialize()

    ts = datetime.now(timezone.utc)
    collector._store_event(
        event_timestamp=ts,
        event_type="usb_connected",
        source="FORENSIC-PC/Kernel-PnP",
        device_id="USB\\VID_0781&PID_5583\\TEST101",
        vendor_id="0781",
        product_id="5583",
        description="SanDisk Ultra USB 3.0",
        source_record_id="PnP#9991",
        metadata={"event_id": 400, "record_number": 9991},
    )

    from database_app.models import Event, Device
    device = Device.objects.filter(device_id="USB\\VID_0781&PID_5583\\TEST101").first()
    assert device is not None
    assert device.vendor_id == "0781"
    assert device.product_id == "5583"

    event = Event.objects.filter(source_record_id="PnP#9991").first()
    assert event is not None
    assert event.event_type == "usb_connected"
    assert event.device == device

    # Test disconnect event updates device and adds disconnect event
    collector._store_event(
        event_timestamp=ts,
        event_type="usb_disconnected",
        source="FORENSIC-PC/Kernel-PnP",
        device_id="USB\\VID_0781&PID_5583\\TEST101",
        vendor_id="0781",
        product_id="5583",
        description="Device Removed",
        source_record_id="PnP#9992",
        metadata={"event_id": 430, "record_number": 9992},
    )

    disconnect_ev = Event.objects.filter(source_record_id="PnP#9992").first()
    assert disconnect_ev is not None
    assert disconnect_ev.event_type == "usb_disconnected"

