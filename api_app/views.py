"""
api_app/views.py — JSON API views for Expo Go GUI client.
All endpoints return application/json. No DRF required.
"""
import json
import logging
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('collectors')

# Shared collector registry — populated by main.py
_collector_registry = {}


def set_collector_registry(registry: dict):
    """Called by main.py to inject running collectors."""
    global _collector_registry
    _collector_registry = registry


def _serialize_event(ev) -> dict:
    return {
        'id': ev.id,
        'event_id': ev.event_id,
        'event_timestamp': ev.event_timestamp.isoformat(),
        'event_type': ev.event_type,
        'source': ev.source,
        'description': ev.description,
        'validation_status': ev.validation_status,
        'collector_name': ev.collector_name,
        'device_id': ev.device.device_id if ev.device else None,
        'evidence_id': ev.evidence.evidence_id if ev.evidence else None,
        'metadata': ev.metadata,
    }


def _serialize_evidence(ev) -> dict:
    return {
        'id': ev.id,
        'evidence_id': ev.evidence_id,
        'original_filename': ev.original_filename,
        'evidence_type': ev.evidence_type,
        'sha256_hash': ev.sha256_hash,
        'file_size': ev.file_size,
        'acquisition_timestamp': ev.acquisition_timestamp.isoformat(),
        'is_verified': ev.is_verified,
        'collector_name': ev.collector_name,
        'source_description': ev.source_description,
    }


def stats_view(request):
    """GET /api/stats/ — overview counts for all event types."""
    from database_app.models import Event, EvidenceFile, CollectorRun
    from django.db.models import Count

    counts = dict(
        Event.objects.values('event_type').annotate(c=Count('id')).values_list('event_type', 'c')
    )
    return JsonResponse({
        'total_events': Event.objects.count(),
        'total_evidence': EvidenceFile.objects.count(),
        'total_runs': CollectorRun.objects.count(),
        'by_type': counts,
        'active_collectors': list(_collector_registry.keys()),
    })


def events_view(request):
    """GET /api/events/?type=&start=&end=&search=&page= — paginated event list."""
    from database_app.models import Event

    event_type = request.GET.get('type', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    search = request.GET.get('search', '')
    page = max(1, int(request.GET.get('page', 1)))
    per_page = 25

    qs = Event.objects.select_related('device', 'evidence').order_by('-event_timestamp')
    if event_type:
        qs = qs.filter(event_type=event_type)
    if start:
        try:
            qs = qs.filter(event_timestamp__gte=datetime.fromisoformat(start))
        except ValueError:
            pass
    if end:
        try:
            qs = qs.filter(event_timestamp__lte=datetime.fromisoformat(end))
        except ValueError:
            pass
    if search:
        qs = qs.filter(description__icontains=search)

    total = qs.count()
    offset = (page - 1) * per_page
    events = list(qs[offset:offset + per_page])

    return JsonResponse({
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, (total + per_page - 1) // per_page),
        'results': [_serialize_event(e) for e in events],
    })


def evidence_view(request):
    """GET /api/evidence/ — list all evidence files."""
    from database_app.models import EvidenceFile
    evidence = EvidenceFile.objects.all().order_by('-acquisition_timestamp')[:100]
    return JsonResponse({'results': [_serialize_evidence(e) for e in evidence]})


def collectors_view(request):
    """GET /api/collectors/ — collector statuses from registry + DB run history."""
    from database_app.models import CollectorRun
    statuses = {}
    for name, collector in _collector_registry.items():
        statuses[name] = collector.get_status()

    runs = CollectorRun.objects.order_by('-start_time')[:10]
    recent_runs = [
        {
            'id': r.id,
            'collector_name': r.collector_name,
            'status': r.status,
            'start_time': r.start_time.isoformat(),
            'end_time': r.end_time.isoformat() if r.end_time else None,
            'event_count': r.event_count,
            'error_count': r.error_count,
        }
        for r in runs
    ]
    return JsonResponse({'statuses': statuses, 'recent_runs': recent_runs})


@csrf_exempt
@require_http_methods(['POST'])
def collector_start_view(request):
    """POST /api/collectors/start/ {name: 'FileCollector'} — start a collector."""
    try:
        body = json.loads(request.body)
        name = body.get('name', '')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    collector = _collector_registry.get(name)
    if not collector:
        return JsonResponse({'error': f'Collector {name!r} not found'}, status=404)
    if collector.is_running:
        return JsonResponse({'message': f'{name} is already running'})
    collector.start()
    return JsonResponse({'message': f'{name} started'})


@csrf_exempt
@require_http_methods(['POST'])
def collector_stop_view(request):
    """POST /api/collectors/stop/ {name: 'FileCollector'} — stop a collector."""
    try:
        body = json.loads(request.body)
        name = body.get('name', '')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    collector = _collector_registry.get(name)
    if not collector:
        return JsonResponse({'error': f'Collector {name!r} not found'}, status=404)
    if not collector.is_running:
        return JsonResponse({'message': f'{name} is not running'})
    collector.stop()
    return JsonResponse({'message': f'{name} stopped'})


@csrf_exempt
@require_http_methods(['POST'])
def network_import_view(request):
    """POST /api/network/import/ {filepath: '...'} — import PCAP file."""
    try:
        body = json.loads(request.body)
        filepath = body.get('filepath', '')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not filepath:
        return JsonResponse({'error': 'filepath required'}, status=400)

    from collectors.network_collector import NetworkCollector
    config = {'project_root': 'D:/Aarya/Unnamed Project'}
    nc = NetworkCollector(config)
    count = nc.import_pcap(filepath)
    return JsonResponse({'message': f'Imported {count} events from {filepath}', 'count': count})
