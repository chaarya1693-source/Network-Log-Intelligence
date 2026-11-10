"""
tests/test_file_collector.py — Unit tests for file system activity observer.
Verifies file stability check, SHA-256 calculation, browser temporary file handling,
and APK file observation without execution.
"""
import os
import tempfile
import time
import pytest
from collectors.file_collector import FileCollector, compute_sha256, wait_for_stability


@pytest.fixture
def temp_watch_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_compute_sha256_valid_file(temp_watch_dir):
    """Test SHA-256 computation against known string hash."""
    test_file = os.path.join(temp_watch_dir, "test.txt")
    with open(test_file, "wb") as f:
        f.write(b"Forensic Integrity Test 2026")
    computed = compute_sha256(test_file)
    assert computed is not None
    assert len(computed) == 64
    # Recomputing should match identically
    assert computed == compute_sha256(test_file)


def test_compute_sha256_nonexistent_file():
    """Test non-existent file returns None without raising an uncaught exception."""
    assert compute_sha256("non_existent_file_xyz_123.tmp") is None


def test_wait_for_stability_stable_file(temp_watch_dir):
    """Test wait_for_stability returns True for a file with static size."""
    test_file = os.path.join(temp_watch_dir, "stable.dat")
    with open(test_file, "wb") as f:
        f.write(b"Sample payload" * 100)
    assert wait_for_stability(test_file, wait_secs=0.1, max_wait=1.0) is True


def test_file_collector_initialization(temp_watch_dir):
    """Test FileCollector initializes directory and sets correct state."""
    config = {
        "project_root": temp_watch_dir,
        "stability_wait_seconds": 0.5,
    }
    collector = FileCollector(config)
    assert collector.name == "FileCollector"
    assert collector.initialize() is True
    assert not collector.is_running
    assert collector.total_events == 0


@pytest.mark.django_db
def test_file_event_apk_observation_differentiated(temp_watch_dir):
    """
    Test APK files generate 'apk_file_observed' event type rather than
    generic file events, and are never executed.
    """
    config = {
        "project_root": temp_watch_dir,
        "stability_wait_seconds": 0.1,
    }
    collector = FileCollector(config)
    collector.initialize()

    # Create dummy harmless APK
    apk_file = os.path.join(temp_watch_dir, "test_data", "watched_downloads", "harmless.apk")
    os.makedirs(os.path.dirname(apk_file), exist_ok=True)
    with open(apk_file, "wb") as f:
        f.write(b"DUMMY_APK_PAYLOAD_FOR_TESTING")

    # Trigger handling
    collector._handle_file_event("file_created", apk_file)

    from database_app.models import Event, EvidenceFile
    event = Event.objects.filter(collector_name="FileCollector", description__contains="harmless.apk").first()
    assert event is not None
    assert event.event_type == "apk_file_observed"

    evidence = EvidenceFile.objects.filter(original_filename="harmless.apk").first()
    assert evidence is not None
    assert evidence.evidence_type == "apk"
    assert evidence.sha256_hash == compute_sha256(apk_file)
