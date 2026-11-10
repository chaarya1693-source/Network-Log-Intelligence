"""
processing/normalizer.py — Normalize raw collector events into standard format.
Handles timezone conversion, event_type normalization, and device ID normalization.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo('Asia/Kolkata')
except ImportError:
    try:
        import pytz
        IST = pytz.timezone('Asia/Kolkata')
    except ImportError:
        IST = timezone.utc

logger = logging.getLogger('collectors')

EVENT_TYPE_MAP = {
    'usb_connect': 'usb_connected',
    'usb_disconnect': 'usb_disconnected',
    'file_create': 'file_created',
    'file_modify': 'file_modified',
    'file_move': 'file_moved',
    'download_observed': 'file_download_observed',
    'apk_observed': 'apk_file_observed',
    'apk_install': 'apk_installed',
    'network': 'network_packet',
    'android_package': 'android_package_observed',
}

VALID_EVENT_TYPES = {
    'usb_connected', 'usb_disconnected', 'file_created', 'file_modified',
    'file_moved', 'file_download_observed', 'apk_file_observed',
    'apk_installed', 'network_packet', 'android_package_observed',
}


def normalize_timestamp(ts: Any) -> Optional[datetime]:
    """
    Normalize any timestamp value to UTC-aware datetime.
    Preserves original; converts naïve datetimes assuming UTC.
    Never fabricates a timestamp if missing or unparseable.
    """
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            # Assume UTC for naïve datetimes
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(ts, str):
        for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f%z',
                    '%Y-%m-%d %H:%M:%S%z', '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ'):
            try:
                # Handle Z offset manually if needed
                ts_clean = ts.replace('Z', '+00:00') if ts.endswith('Z') else ts
                dt = datetime.fromisoformat(ts_clean) if hasattr(datetime, 'fromisoformat') else datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, TypeError):
                continue
    logger.warning(f"normalize_timestamp: cannot parse {ts!r} — preserving integrity, not fabricating")
    return None


def normalize_event_type(raw_type: str) -> str:
    """Map raw event type strings to canonical values."""
    if raw_type in VALID_EVENT_TYPES:
        return raw_type
    mapped = EVENT_TYPE_MAP.get(raw_type.lower().replace(' ', '_'), raw_type)
    if mapped not in VALID_EVENT_TYPES:
        logger.warning(f"normalize_event_type: unknown type '{raw_type}', keeping as-is")
    return mapped


def normalize_device_id(device_id: str) -> str:
    """Normalize device IDs — uppercase, strip excess whitespace."""
    if not device_id:
        return ''
    return device_id.strip().upper()[:512]


def normalize_source(source: str) -> str:
    """Normalize source string — strip whitespace, truncate."""
    return (source or 'unknown').strip()[:200]


def normalize_event(raw: dict) -> dict:
    """
    Normalize a raw event dict. Returns a normalized dict ready for validation.
    Input keys: event_timestamp, event_type, source, description, source_record_id,
                collector_name, metadata
    """
    return {
        'event_timestamp': normalize_timestamp(raw.get('event_timestamp')),
        'event_type': normalize_event_type(str(raw.get('event_type', 'unknown'))),
        'source': normalize_source(str(raw.get('source', ''))),
        'description': str(raw.get('description', ''))[:1000],
        'source_record_id': str(raw.get('source_record_id', ''))[:256],
        'collector_name': str(raw.get('collector_name', ''))[:100],
        'metadata': raw.get('metadata', {}),
    }
