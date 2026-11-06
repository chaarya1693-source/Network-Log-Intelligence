"""
database/repositories.py — Repository pattern for DB access.
"""
import csv
import hashlib
import io
import logging
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger('collectors')


class EvidenceRepository:
    @staticmethod
    def create_evidence(original_filename, file_path, evidence_type, sha256_hash,
                        file_size, acquisition_timestamp, source_description='',
                        acquisition_method='automatic', collector_name='', metadata=None):
        from database_app.models import EvidenceFile
        from django.utils import timezone as dj_tz
        return EvidenceFile.objects.create(
            original_filename=original_filename,
            file_path=file_path,
            evidence_type=evidence_type,
            sha256_hash=sha256_hash,
            file_size=file_size,
            acquisition_timestamp=acquisition_timestamp or dj_tz.now(),
            source_description=source_description,
            acquisition_method=acquisition_method,
            collector_name=collector_name,
            metadata=metadata or {},
        )

    @staticmethod
    def verify_integrity(evidence_id: str) -> dict:
        """Recompute SHA-256 and compare with stored hash."""
        from database_app.models import EvidenceFile
        from django.utils import timezone as dj_tz
        try:
            ev = EvidenceFile.objects.get(evidence_id=evidence_id)
        except EvidenceFile.DoesNotExist:
            return {'verified': False, 'error': 'Evidence record not found'}
        try:
            h = hashlib.sha256()
            with open(ev.file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
            computed = h.hexdigest()
            match = computed == ev.sha256_hash
            ev.is_verified = match
            ev.verification_timestamp = dj_tz.now()
            ev.save(update_fields=['is_verified', 'verification_timestamp'])
            return {
                'verified': match,
                'stored_hash': ev.sha256_hash,
                'computed_hash': computed,
                'file_path': ev.file_path,
            }
        except FileNotFoundError:
            return {'verified': False, 'error': f'File not found: {ev.file_path}'}
        except Exception as e:
            return {'verified': False, 'error': str(e)}

    @staticmethod
    def get_all():
        from database_app.models import EvidenceFile
        return EvidenceFile.objects.all().order_by('-acquisition_timestamp')

    @staticmethod
    def get_by_id(evidence_id: str):
        from database_app.models import EvidenceFile
        try:
            return EvidenceFile.objects.get(evidence_id=evidence_id)
        except EvidenceFile.DoesNotExist:
            return None


class EventRepository:
    @staticmethod
    def get_timeline(event_type=None, source=None, device_id=None,
                     start_dt=None, end_dt=None, search=None,
                     page=1, per_page=25):
        from database_app.models import Event
        qs = Event.objects.select_related('device', 'evidence').order_by('-event_timestamp')
        if event_type:
            qs = qs.filter(event_type=event_type)
        if source:
            qs = qs.filter(source__icontains=source)
        if device_id:
            qs = qs.filter(device__device_id__icontains=device_id)
        if start_dt:
            qs = qs.filter(event_timestamp__gte=start_dt)
        if end_dt:
            qs = qs.filter(event_timestamp__lte=end_dt)
        if search:
            qs = qs.filter(description__icontains=search)
        total = qs.count()
        offset = (page - 1) * per_page
        events = qs[offset:offset + per_page]
        return {'events': events, 'total': total, 'page': page, 'per_page': per_page,
                'total_pages': max(1, (total + per_page - 1) // per_page)}

    @staticmethod
    def get_counts_by_type():
        from database_app.models import Event
        from django.db.models import Count
        return dict(Event.objects.values('event_type').annotate(count=Count('id'))
                    .values_list('event_type', 'count'))

    @staticmethod
    def export_to_csv(queryset) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['event_id', 'event_timestamp', 'event_type', 'source',
                         'description', 'validation_status', 'collector_name'])
        for ev in queryset:
            writer.writerow([
                ev.event_id, ev.event_timestamp.isoformat(), ev.event_type,
                ev.source, ev.description, ev.validation_status, ev.collector_name,
            ])
        return output.getvalue()


class CollectorRunRepository:
    @staticmethod
    def get_all_runs():
        from database_app.models import CollectorRun
        return CollectorRun.objects.all().order_by('-start_time')[:50]
