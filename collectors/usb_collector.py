"""
collectors/usb_collector.py — Windows USB/PnP event collector using win32evtlog.
Monitors Microsoft-Windows-Kernel-PnP/Device Management channel.
"""
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

from collectors.base_collector import BaseCollector

logger = logging.getLogger('collectors')

# Windows Event IDs for USB device events
USB_CONNECT_IDS = {400, 410, 420}      # Device enumerated / started
USB_DISCONNECT_IDS = {430, 440}         # Device removed / disabled
USB_INSTALL_IDS = {20001, 20003}        # Driver installed


def _extract_vid_pid(hardware_id_str: str):
    """Extract VID/PID from hardware ID string like VID_05AC&PID_12A0."""
    vid, pid = '', ''
    if not hardware_id_str:
        return vid, pid
    m = re.search(r'VID_([0-9A-Fa-f]{4})', hardware_id_str, re.IGNORECASE)
    if m:
        vid = m.group(1).upper()
    m = re.search(r'PID_([0-9A-Fa-f]{4})', hardware_id_str, re.IGNORECASE)
    if m:
        pid = m.group(1).upper()
    return vid, pid


class USBCollector(BaseCollector):
    """
    Monitors Windows Event Log channel for USB connection/disconnection events.
    Uses pywin32 (win32evtlog) to read event records.
    """

    CHANNEL = 'Microsoft-Windows-Kernel-PnP/Device Management'

    def __init__(self, config: dict):
        super().__init__(config)
        self._poll_interval = config.get('usb_poll_interval_seconds', 3)
        self._seen_record_ids: set = set()
        self._last_record_number = 0

    @property
    def name(self) -> str:
        return 'USBCollector'

    def initialize(self) -> bool:
        try:
            import win32evtlog  # noqa: F401
            logger.info(f"{self.name}: win32evtlog available")
            return True
        except ImportError:
            self.report_error("win32evtlog not available — install pywin32")
            return False

    def _collect_loop(self):
        """Poll the PnP event channel every N seconds for new USB events."""
        import win32evtlog
        import win32con

        while self._running:
            try:
                self._read_new_events(win32evtlog, win32con)
            except Exception as exc:
                self.report_error(f"Error reading event log: {exc}", exc)
            time.sleep(self._poll_interval)

    def _read_new_events(self, win32evtlog, win32con):
        """Read new events from PnP channel since last check."""
        try:
            handle = win32evtlog.OpenEventLog(None, self.CHANNEL)
        except Exception as e:
            # Try alternative channel name
            try:
                handle = win32evtlog.OpenEventLog(None, 'System')
                logger.info(f"{self.name}: using System channel (PnP channel unavailable: {e})")
            except Exception as e2:
                self.report_error(f"Cannot open event log: {e2}", e2)
                return

        try:
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            new_count = 0
            for event in (events or []):
                record_id = getattr(event, 'RecordNumber', 0)
                if record_id in self._seen_record_ids:
                    continue
                self._seen_record_ids.add(record_id)
                event_id = event.EventID & 0xFFFF
                # Filter to USB-relevant event IDs from System channel
                # From PnP channel: check source name
                source = getattr(event, 'SourceName', '')
                if 'PnP' not in source and 'PnPDevice' not in source and 'DriverFrameworks' not in source:
                    # In System channel, filter more loosely
                    if event_id not in {7036, 7045, 10400, 10401}:
                        continue
                self._process_event(event, event_id)
                new_count += 1
                if new_count >= 100:  # Batch limit
                    break
            if new_count:
                logger.debug(f"{self.name}: processed {new_count} new USB events")
        finally:
            win32evtlog.CloseEventLog(handle)

    def _process_event(self, event, event_id: int):
        """Convert win32 event record to forensic Event model entry."""
        try:
            # Extract timestamp
            time_gen = event.TimeGenerated
            if hasattr(time_gen, 'timestamp'):
                ts = datetime.fromtimestamp(time_gen.timestamp(), tz=timezone.utc)
            else:
                ts = datetime.now(timezone.utc)

            # Extract strings/data
            strings = list(event.StringInserts or [])
            raw_description = ' | '.join(str(s) for s in strings if s)
            source_name = getattr(event, 'SourceName', 'Unknown')
            computer = getattr(event, 'ComputerName', 'localhost')
            record_number = getattr(event, 'RecordNumber', 0)
            source_record_id = f"{source_name}#{record_number}"

            # Determine USB event type
            if event_id in USB_DISCONNECT_IDS:
                evt_type = 'usb_disconnected'
            else:
                evt_type = 'usb_connected'

            # Extract hardware ID if present
            hardware_ids = [s for s in strings if isinstance(s, str) and 'VID_' in s.upper()]
            vid, pid = '', ''
            device_id_str = f"USB_{source_name}_{record_number}"
            if hardware_ids:
                vid, pid = _extract_vid_pid(hardware_ids[0])
                device_id_str = hardware_ids[0][:256]

            self._store_event(
                event_timestamp=ts,
                event_type=evt_type,
                source=f"{computer}/{source_name}",
                device_id=device_id_str,
                vendor_id=vid,
                product_id=pid,
                description=raw_description[:500],
                source_record_id=source_record_id,
                metadata={
                    'event_id': event_id,
                    'record_number': record_number,
                    'source_name': source_name,
                    'computer': computer,
                    'raw_strings': strings[:10],
                }
            )
        except Exception as exc:
            self.report_error(f"Failed to process event record: {exc}", exc)

    def _store_event(self, event_timestamp, event_type, source, device_id,
                     vendor_id, product_id, description, source_record_id, metadata):
        """Persist event to database with deduplication."""
        import django
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
        try:
            django.setup()
        except Exception:
            pass

        from database_app.models import Device, Event
        from processing.deduplicator import is_duplicate

        if is_duplicate(source_record_id, self.name):
            return

        try:
            device, _ = Device.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'device_type': 'usb',
                    'vendor_id': vendor_id,
                    'product_id': product_id,
                    'description': description,
                }
            )
            # Update last_seen
            device.last_seen = event_timestamp
            device.save(update_fields=['last_seen'])
        except Exception:
            device = None

        try:
            from processing.normalizer import normalize_event
            from processing.validator import validate_event
            raw = {
                'event_timestamp': event_timestamp,
                'event_type': event_type,
                'source': source,
                'description': description,
                'source_record_id': source_record_id,
                'collector_name': self.name,
                'metadata': metadata,
            }
            normalized = normalize_event(raw)
            validation_status = validate_event(normalized)
            Event.objects.create(
                event_timestamp=normalized['event_timestamp'],
                event_type=normalized['event_type'],
                source=normalized['source'],
                device=device,
                description=normalized['description'],
                source_record_id=source_record_id,
                collector_name=self.name,
                validation_status=validation_status,
                metadata=normalized['metadata'],
            )
            self._increment_events()
        except Exception as exc:
            self.report_error(f"Failed to store event: {exc}", exc)
