"""
processing/deduplicator.py — Prevents duplicate events from being stored.
Two strategies:
 1. source_record_id + collector_name uniqueness (within a 5-second window and globally)
 2. SHA-256 hash deduplication for file events
"""
import logging
from datetime import timedelta

logger = logging.getLogger('collectors')

DEDUP_WINDOW_SECONDS = 5


def is_duplicate(source_record_id: str, collector_name: str) -> bool:
    """
    Check if an event with this source_record_id from this collector already exists in DB.
    Returns True if duplicate (should be skipped).
    """
    if not source_record_id:
        return False
    try:
        import django
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
        try:
            django.setup()
        except Exception:
            pass
        from database_app.models import Event
        return Event.objects.filter(
            source_record_id=source_record_id,
            collector_name=collector_name
        ).exists()
    except Exception as e:
        logger.debug(f"deduplicator: DB check failed: {e}")
        return False


def is_duplicate_hash(sha256_hash: str) -> bool:
    """
    Check if a file with this SHA-256 has already been recorded as an EvidenceFile.
    Returns True if duplicate.
    """
    if not sha256_hash:
        return False
    try:
        import django
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
        try:
            django.setup()
        except Exception:
            pass
        from database_app.models import EvidenceFile
        return EvidenceFile.objects.filter(sha256_hash=sha256_hash).exists()
    except Exception as e:
        logger.debug(f"deduplicator: hash DB check failed: {e}")
        return False
