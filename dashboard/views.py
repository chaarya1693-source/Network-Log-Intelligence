"""
dashboard/views.py — Django web dashboard views for all 9 pages.
Real DB data only. Never fabricates events.
"""
import csv
import logging
from datetime import datetime

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('collectors')

EVENT_TYPES = [
    'usb_connected', 'usb_disconnected', 'file_created', 'file_modified',
    'file_moved', 'file_download_observed', 'apk_file_observed',
    'apk_installed', 'network_packet', 'android_package_observed',
]


def _get_event_counts():
    from database_app.models import Event
    from django.db.models import Count
    counts = dict(
        Event.objects.values('event_type').annotate(c=Count('id')).values_list('event_type', 'c')
    )
    return counts


def overview(request):
    """/ — Overview dashboard with summary statistics."""
    from database_app.models import Event, EvidenceFile, CollectorRun
    from django.db.models import Count
    from django.utils import timezone

    counts = _get_event_counts()
    recent_events = Event.objects.select_related('device').order_by('-event_timestamp')[:10]
    total_events = Event.objects.count()
    total_evidence = EvidenceFile.objects.count()
    collector_runs = CollectorRun.objects.order_by('-start_time')[:5]

    # Last 24h events by hour for chart
    chart_labels = []
    chart_data = []

    return render(request, 'dashboard/overview.html', {
        'counts': counts,
        'recent_events': recent_events,
        'total_events': total_events,
        'total_evidence': total_evidence,
        'collector_runs': collector_runs,
        'event_types': EVENT_TYPES,
        'page': 'overview',
    })


def network_activity(request):
    """/network/ — Network packet events, filterable table."""
    from database_app.models import Event
    page = max(1, int(request.GET.get('page', 1)))
    per_page = 25
    search = request.GET.get('search', '')
    qs = Event.objects.filter(event_type='network_packet').select_related('evidence').order_by('-event_timestamp')
    if search:
        qs = qs.filter(description__icontains=search)
    total = qs.count()
    offset = (page - 1) * per_page
    events = qs[offset:offset + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render(request, 'dashboard/network.html', {
        'events': events, 'total': total, 'page': page,
        'total_pages': total_pages, 'search': search, 'page_name': 'network',
    })


def usb_activity(request):
    """/usb/ — USB connection/disconnection events."""
    from database_app.models import Event
    page = max(1, int(request.GET.get('page', 1)))
    per_page = 25
    event_filter = request.GET.get('type', '')
    qs = Event.objects.filter(event_type__in=['usb_connected', 'usb_disconnected']).select_related('device').order_by('-event_timestamp')
    if event_filter:
        qs = qs.filter(event_type=event_filter)
    total = qs.count()
    offset = (page - 1) * per_page
    events = qs[offset:offset + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render(request, 'dashboard/usb.html', {
        'events': events, 'total': total, 'page': page,
        'total_pages': total_pages, 'event_filter': event_filter, 'page_name': 'usb',
    })


def file_activity(request):
    """/files/ — File monitoring events."""
    from database_app.models import Event
    page = max(1, int(request.GET.get('page', 1)))
    per_page = 25
    file_types = ['file_created', 'file_modified', 'file_moved', 'file_download_observed', 'apk_file_observed']
    event_filter = request.GET.get('type', '')
    search = request.GET.get('search', '')
    qs = Event.objects.filter(event_type__in=file_types).select_related('evidence').order_by('-event_timestamp')
    if event_filter:
        qs = qs.filter(event_type=event_filter)
    if search:
        qs = qs.filter(description__icontains=search)
    total = qs.count()
    offset = (page - 1) * per_page
    events = qs[offset:offset + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render(request, 'dashboard/files.html', {
        'events': events, 'total': total, 'page': page,
        'total_pages': total_pages, 'file_types': file_types,
        'event_filter': event_filter, 'search': search, 'page_name': 'files',
    })


def android_activity(request):
    """/android/ — Android package observation events."""
    from database_app.models import Event
    page = max(1, int(request.GET.get('page', 1)))
    per_page = 25
    android_types = ['android_package_observed', 'apk_installed']
    qs = Event.objects.filter(event_type__in=android_types).select_related('device').order_by('-event_timestamp')
    total = qs.count()
    offset = (page - 1) * per_page
    events = qs[offset:offset + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render(request, 'dashboard/android.html', {
        'events': events, 'total': total, 'page': page,
        'total_pages': total_pages, 'page_name': 'android',
    })


def timeline(request):
    """/timeline/ — Unified timeline with all event types, filters, pagination, CSV export."""
    from database_app.models import Event
    page = max(1, int(request.GET.get('page', 1)))
    per_page = 25
    event_type = request.GET.get('type', '')
    source = request.GET.get('source', '')
    start_dt_str = request.GET.get('start', '')
    end_dt_str = request.GET.get('end', '')
    search = request.GET.get('search', '')

    qs = Event.objects.select_related('device', 'evidence').order_by('-event_timestamp')
    if event_type:
        qs = qs.filter(event_type=event_type)
    if source:
        qs = qs.filter(source__icontains=source)
    if start_dt_str:
        try:
            qs = qs.filter(event_timestamp__gte=datetime.fromisoformat(start_dt_str))
        except ValueError:
            pass
    if end_dt_str:
        try:
            qs = qs.filter(event_timestamp__lte=datetime.fromisoformat(end_dt_str))
        except ValueError:
            pass
    if search:
        qs = qs.filter(description__icontains=search)

    total = qs.count()
    offset = (page - 1) * per_page
    events = qs[offset:offset + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render(request, 'dashboard/timeline.html', {
        'events': events, 'total': total, 'page': page,
        'total_pages': total_pages, 'event_types': EVENT_TYPES,
        'event_type': event_type, 'source': source,
        'start_dt': start_dt_str, 'end_dt': end_dt_str, 'search': search,
        'page_name': 'timeline',
    })


def evidence_management(request):
    """/evidence/ — Evidence chain of custody management."""
    from database_app.models import EvidenceFile
    page = max(1, int(request.GET.get('page', 1)))
    per_page = 25
    qs = EvidenceFile.objects.all().order_by('-acquisition_timestamp')
    total = qs.count()
    offset = (page - 1) * per_page
    evidence = qs[offset:offset + per_page]
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render(request, 'dashboard/evidence.html', {
        'evidence': evidence, 'total': total, 'page': page,
        'total_pages': total_pages, 'page_name': 'evidence',
    })


def verify_evidence(request, evidence_id: str):
    """/evidence/verify/<id>/ — Verify SHA-256 integrity of evidence file."""
    from database.repositories import EvidenceRepository
    result = EvidenceRepository.verify_integrity(evidence_id)
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(result)
    # For web: redirect back with flash message
    if result.get('verified'):
        messages.success(request, f"✓ Integrity verified: {evidence_id}")
    else:
        messages.error(request, f"✗ Integrity check failed: {result.get('error', 'Hash mismatch')}")
    return redirect('evidence')


def collectors_management(request):
    """/collectors/ — Collector status and run history."""
    from database_app.models import CollectorRun
    runs = CollectorRun.objects.order_by('-start_time')[:20]
    return render(request, 'dashboard/collectors.html', {
        'runs': runs, 'page_name': 'collectors',
    })


def reports(request):
    """/reports/ — Generate and export reports."""
    from database_app.models import Event
    from django.db.models import Count
    counts = _get_event_counts()
    total = Event.objects.count()
    return render(request, 'dashboard/reports.html', {
        'counts': counts, 'total': total, 'event_types': EVENT_TYPES, 'page_name': 'reports',
    })


def export_csv(request):
    """/reports/export/ — Download events as CSV."""
    from database_app.models import Event
    event_type = request.GET.get('type', '')
    qs = Event.objects.order_by('-event_timestamp')
    if event_type:
        qs = qs.filter(event_type=event_type)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="forensics_events.csv"'
    writer = csv.writer(response)
    writer.writerow(['event_id', 'event_timestamp', 'event_type', 'source',
                     'description', 'validation_status', 'collector_name', 'device_id'])
    for ev in qs[:10000]:
        writer.writerow([
            ev.event_id,
            ev.event_timestamp.isoformat(),
            ev.event_type,
            ev.source,
            ev.description,
            ev.validation_status,
            ev.collector_name,
            ev.device.device_id if ev.device else '',
        ])
    return response
