"""
processing/parser.py — Raw event dict parser into standardized internal format.
"""
import logging
from typing import Any

logger = logging.getLogger('collectors')


def parse_raw_event(raw: dict) -> dict:
    """
    Parse a raw event dict (from any collector) into a standardized format.
    Does NOT validate — call validator.validate_event() after normalization.
    """
    return {
        'event_timestamp': raw.get('event_timestamp'),
        'event_type': raw.get('event_type', 'unknown'),
        'source': raw.get('source', ''),
        'description': raw.get('description', ''),
        'source_record_id': raw.get('source_record_id', ''),
        'collector_name': raw.get('collector_name', ''),
        'device_id': raw.get('device_id', ''),
        'vendor_id': raw.get('vendor_id', ''),
        'product_id': raw.get('product_id', ''),
        'metadata': raw.get('metadata', {}),
    }
