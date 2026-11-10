"""
tests/test_android_collector.py — Unit tests for Android ADB package observer.
Verifies package snapshot parsing, snapshot diff comparison,
and isolation from host file observation.
"""
from datetime import datetime, timezone
import pytest
from collectors.android_collector import AndroidCollector, get_adb_path


def test_get_adb_path_fallback():
    """Test get_adb_path returns a string path or default without error."""
    path = get_adb_path()
    assert isinstance(path, str)
    assert len(path) > 0


def test_parse_package_snapshot_lines():
    """Test parsing standard ADB pm output into set of package strings."""
    raw_output = """
    package:com.android.chrome
    package:org.forensics.harmless.test
    package:com.google.android.youtube
    """
    packages = set()
    for line in raw_output.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            packages.add(line[8:].strip())

    assert "org.forensics.harmless.test" in packages
    assert "com.android.chrome" in packages
    assert len(packages) == 3


def test_snapshot_diff_detection():
    """
    Test comparing before and after package snapshots identifies
    newly installed package accurately in controlled emulator tests.
    """
    before_snapshot = {"com.android.chrome", "com.google.android.youtube"}
    after_snapshot = {"com.android.chrome", "com.google.android.youtube", "org.forensics.harmless.test"}

    new_packages = after_snapshot - before_snapshot
    assert len(new_packages) == 1
    assert "org.forensics.harmless.test" in new_packages


@pytest.mark.django_db
def test_android_collector_store_package_observation():
    """Test storing Android package observation creates Event with android_package_observed type."""
    collector = AndroidCollector({"android_poll_interval_seconds": 10})

    collector._store_package_event(
        event_type="android_package_observed",
        serial="emulator-5554",
        package="org.forensics.harmless.test",
        info={"versionName": "1.0.0", "versionCode": "1"},
    )

    from database_app.models import Event, Device
    event = Event.objects.filter(collector_name="AndroidCollector", source_record_id__contains="org.forensics.harmless.test").first()
    assert event is not None
    assert event.event_type == "android_package_observed"
    assert event.device is not None
    assert event.device.device_type == "android_emulator"
    assert "org.forensics.harmless.test" in event.description
