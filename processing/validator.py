"""
processing/validator.py — Validates normalized event dicts.
Returns validation_status: 'valid', 'invalid', 'warning', 'pending'.
"""
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger('collectors')

REQUIRED_FIELDS = ['event_timestamp', 'event_type', 'source', 'collector_name']
VALID_EVENT_TYPES = {
    'usb_connected', 'usb_disconnected', 'file_created', 'file_modified',
    'file_moved', 'file_download_observed', 'apk_file_observed',
    'apk_installed', 'network_packet', 'android_package_observed',
}

MAX_FUTURE_SECONDS = 300  # Allow 5 minutes future drift
MAX_PAST_DAYS = 365 * 5   # 5 years back is suspicious but not invalid


def validate_event(normalized: dict) -> str:
    """
    Validate a normalized event dict.
    Returns one of: 'valid', 'invalid', 'warning', 'pending'
    """
    warnings = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        value = normalized.get(field)
        if not value:
            logger.warning(f"validate_event: missing required field '{field}'")
            return 'invalid'

    # Validate event_type
    if normalized.get('event_type') not in VALID_EVENT_TYPES:
        logger.warning(f"validate_event: unrecognized event_type '{normalized.get('event_type')}'")
        warnings.append('unrecognized_event_type')

    # Validate timestamp
    ts = normalized.get('event_timestamp')
    if isinstance(ts, datetime):
        now = datetime.now(timezone.utc)
        diff_future = (ts - now).total_seconds()
        diff_past = (now - ts).total_seconds()
        if diff_future > MAX_FUTURE_SECONDS:
            warnings.append('timestamp_in_future')
        if diff_past > MAX_PAST_DAYS * 86400:
            warnings.append('timestamp_very_old')
    else:
        return 'invalid'

    # Optional field checks
    if not normalized.get('source_record_id'):
        warnings.append('no_source_record_id')
    if not normalized.get('description'):
        warnings.append('no_description')
    if not isinstance(normalized.get('metadata'), dict):
        warnings.append('metadata_not_dict')

    if warnings:
        return 'warning'
    return 'valid'
