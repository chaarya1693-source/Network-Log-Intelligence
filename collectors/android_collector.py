r"""
collectors/android_collector.py — ADB-based Android emulator/device monitoring.
Performs package snapshot comparisons. NEVER installs APKs without explicit approval.
"""
import logging
import subprocess
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set

from collectors.base_collector import BaseCollector

import os
import shutil

logger = logging.getLogger('collectors')


def get_adb_path(configured_path: Optional[str] = None) -> str:
    """Discover ADB binary dynamically via configuration, environment, PATH, or SDK defaults."""
    if configured_path and os.path.exists(configured_path):
        return configured_path
    env_path = os.environ.get('ADB_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    which_path = shutil.which('adb')
    if which_path:
        return which_path
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if local_app_data:
        default_sdk_adb = os.path.join(local_app_data, 'Android', 'Sdk', 'platform-tools', 'adb.exe')
        if os.path.exists(default_sdk_adb):
            return default_sdk_adb
    return configured_path or 'adb'


class AndroidCollector(BaseCollector):
    """
    Monitors Android devices/emulators via ADB for package changes.
    Records package observations and detects new installs via before/after snapshots.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self._adb = get_adb_path(config.get('adb_path'))
        self._poll_interval = config.get('android_poll_interval_seconds', 10)
        self._last_snapshots: Dict[str, Set[str]] = {}  # serial → package set

    @property
    def name(self) -> str:
        return 'AndroidCollector'

    def initialize(self) -> bool:
        try:
            result = subprocess.run([self._adb, 'version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"{self.name}: ADB available — {result.stdout.splitlines()[0]}")
                return True
            else:
                self.report_error(f"ADB returned non-zero: {result.stderr}")
                return False
        except FileNotFoundError:
            self.report_error(f"ADB not found at {self._adb}")
            return False
        except Exception as e:
            self.report_error(f"ADB init error: {e}", e)
            return False

    def _collect_loop(self):
        """Poll connected devices for package changes."""
        while self._running:
            try:
                devices = self.detect_devices()
                for serial in devices:
                    self._check_device(serial)
            except Exception as exc:
                self.report_error(f"Polling error: {exc}", exc)
            time.sleep(self._poll_interval)

    def detect_devices(self) -> List[str]:
        """Return list of connected device serials."""
        try:
            result = subprocess.run([self._adb, 'devices'], capture_output=True, text=True, timeout=10)
            serials = []
            for line in result.stdout.splitlines()[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == 'device':
                    serials.append(parts[0])
            return serials
        except Exception as e:
            logger.warning(f"{self.name}: detect_devices error: {e}")
            return []

    def get_package_snapshot(self, serial: str) -> Set[str]:
        """Get set of third-party package names installed on device."""
        try:
            result = subprocess.run(
                [self._adb, '-s', serial, 'shell', 'pm', 'list', 'packages', '-3'],
                capture_output=True, text=True, timeout=30
            )
            packages = set()
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith('package:'):
                    packages.add(line[8:].strip())
            return packages
        except Exception as e:
            logger.warning(f"{self.name}: package snapshot error for {serial}: {e}")
            return set()

    def get_package_info(self, serial: str, package: str) -> dict:
        """Get detailed package information via dumpsys."""
        try:
            result = subprocess.run(
                [self._adb, '-s', serial, 'shell', 'dumpsys', 'package', package],
                capture_output=True, text=True, timeout=30
            )
            info = {'raw_output': result.stdout[:2000]}
            # Parse version
            for line in result.stdout.splitlines():
                line = line.strip()
                if 'versionName=' in line:
                    info['version_name'] = line.split('versionName=')[-1].strip()
                elif 'versionCode=' in line:
                    info['version_code'] = line.split('versionCode=')[-1].split()[0].strip()
                elif 'firstInstallTime=' in line:
                    info['first_install_time'] = line.split('firstInstallTime=')[-1].strip()
                elif 'lastUpdateTime=' in line:
                    info['last_update_time'] = line.split('lastUpdateTime=')[-1].strip()
            return info
        except Exception as e:
            return {'error': str(e)}

    def _check_device(self, serial: str):
        """Compare current package list with last snapshot; record changes."""
        current = self.get_package_snapshot(serial)
        if not current:
            return

        previous = self._last_snapshots.get(serial)
        if previous is None:
            # First snapshot — record all existing packages as observations
            for pkg in current:
                self._store_package_event('android_package_observed', serial, pkg, {})
            logger.info(f"{self.name}: initial snapshot for {serial}: {len(current)} packages")
        else:
            # Detect newly installed packages
            new_packages = current - previous
            for pkg in new_packages:
                info = self.get_package_info(serial, pkg)
                self._store_package_event('apk_installed', serial, pkg, info)
                logger.info(f"{self.name}: NEW package detected on {serial}: {pkg}")

        self._last_snapshots[serial] = current

    def _store_package_event(self, event_type: str, serial: str, package: str, info: dict):
        """Persist Android package event to DB."""
        import django
        import os as _os
        _os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
        try:
            django.setup()
        except Exception:
            pass

        from database_app.models import Device, Event
        from processing.deduplicator import is_duplicate
        from processing.normalizer import normalize_event
        from processing.validator import validate_event

        source_record_id = f"android:{serial}:{package}:{event_type}"
        if is_duplicate(source_record_id, self.name):
            return

        try:
            device, _ = Device.objects.get_or_create(
                device_id=f"android:{serial}",
                defaults={'device_type': 'android_emulator', 'description': f"Android device {serial}"}
            )
        except Exception:
            device = None

        raw = {
            'event_timestamp': datetime.now(timezone.utc),
            'event_type': event_type,
            'source': f"adb:{serial}",
            'description': f"{event_type}: {package} on {serial}",
            'source_record_id': source_record_id,
            'collector_name': self.name,
            'metadata': {
                'serial': serial,
                'package': package,
                **info,
            },
        }
        try:
            normalized = normalize_event(raw)
            validation_status = validate_event(normalized)
            Event.objects.create(
                event_timestamp=normalized['event_timestamp'],
                event_type=event_type,
                source=normalized['source'],
                device=device,
                description=normalized['description'],
                source_record_id=source_record_id,
                collector_name=self.name,
                validation_status=validation_status,
                metadata=normalized['metadata'],
            )
            self._increment_events()
        except Exception as exc:
            self.report_error(f"Failed to store package event: {exc}", exc)
