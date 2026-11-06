"""
database_app/models.py — Core ORM models for Stage 1
"""
import uuid
from django.db import models


def generate_event_id():
    return f"EVT-{uuid.uuid4().hex[:12].upper()}"


def generate_evidence_id():
    return f"EVD-{uuid.uuid4().hex[:12].upper()}"


class Device(models.Model):
    """Represents a physical or virtual device observed during monitoring."""
    device_id = models.CharField(max_length=512, unique=True, db_index=True)
    device_type = models.CharField(max_length=100, default='unknown')
    vendor_id = models.CharField(max_length=20, blank=True, default='')
    product_id = models.CharField(max_length=20, blank=True, default='')
    description = models.TextField(blank=True, default='')
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'devices'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['device_type']),
        ]

    def __str__(self):
        return f"{self.device_type}: {self.device_id[:40]}"


class EvidenceFile(models.Model):
    """Chain-of-custody record for every file or PCAP analyzed."""
    EVIDENCE_TYPES = [
        ('pcap', 'PCAP/PCAPNG Network Capture'),
        ('apk', 'Android APK File'),
        ('log', 'Log File'),
        ('event_log', 'Windows Event Log Export'),
        ('file', 'Observed File'),
        ('other', 'Other'),
    ]
    evidence_id = models.CharField(
        max_length=32, unique=True, default=generate_evidence_id, editable=False, db_index=True
    )
    original_filename = models.CharField(max_length=512)
    file_path = models.TextField()
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default='file')
    sha256_hash = models.CharField(max_length=64, db_index=True)
    file_size = models.BigIntegerField(default=0)
    acquisition_timestamp = models.DateTimeField()
    source_description = models.TextField(blank=True, default='')
    acquisition_method = models.CharField(max_length=100, default='automatic')
    collector_name = models.CharField(max_length=100, default='')
    timezone_info = models.CharField(max_length=50, default='Asia/Kolkata')
    is_verified = models.BooleanField(default=False)
    verification_timestamp = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evidence_files'
        ordering = ['-acquisition_timestamp']
        indexes = [
            models.Index(fields=['evidence_type']),
            models.Index(fields=['sha256_hash']),
        ]

    def __str__(self):
        return f"{self.evidence_id}: {self.original_filename}"


class Event(models.Model):
    """Central event record — every forensic observation stored here."""
    EVENT_TYPES = [
        ('usb_connected', 'USB Connected'),
        ('usb_disconnected', 'USB Disconnected'),
        ('file_created', 'File Created'),
        ('file_modified', 'File Modified'),
        ('file_moved', 'File Moved'),
        ('file_download_observed', 'File Download Observed'),
        ('apk_file_observed', 'APK File Observed'),
        ('apk_installed', 'APK Installed'),
        ('network_packet', 'Network Packet'),
        ('android_package_observed', 'Android Package Observed'),
    ]
    VALIDATION_STATUS = [
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('warning', 'Warning'),
        ('pending', 'Pending'),
    ]

    event_id = models.CharField(
        max_length=32, unique=True, default=generate_event_id, editable=False, db_index=True
    )
    event_timestamp = models.DateTimeField(db_index=True)
    collection_timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES, db_index=True)
    source = models.CharField(max_length=200, db_index=True)
    device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL, related_name='events')
    description = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    evidence = models.ForeignKey(EvidenceFile, null=True, blank=True, on_delete=models.SET_NULL, related_name='events')
    source_record_id = models.CharField(max_length=256, blank=True, default='', db_index=True)
    collector_name = models.CharField(max_length=100, default='')
    validation_status = models.CharField(max_length=20, choices=VALIDATION_STATUS, default='pending', db_index=True)

    class Meta:
        db_table = 'events'
        ordering = ['-event_timestamp']
        indexes = [
            models.Index(fields=['event_timestamp', 'event_type']),
            models.Index(fields=['source', 'collector_name']),
            models.Index(fields=['collector_name', 'source_record_id']),
        ]

    def __str__(self):
        return f"{self.event_id}: {self.event_type} @ {self.event_timestamp}"


class CollectorRun(models.Model):
    """Audit log for each collector execution session."""
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('stopped', 'Stopped'),
    ]
    collector_name = models.CharField(max_length=100, db_index=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    event_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    error_details = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'collector_runs'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.collector_name} [{self.status}] @ {self.start_time}"
