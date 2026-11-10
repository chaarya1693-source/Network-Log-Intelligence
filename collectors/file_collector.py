"""
collectors/file_collector.py — Watches test_data/watched_downloads/ for file activity.
Uses watchdog for filesystem event detection.
"""
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from collectors.base_collector import BaseCollector

logger = logging.getLogger('collectors')

TEMP_EXTENSIONS = {'.crdownload', '.part', '.tmp', '.download', '.partial'}
APK_EXTENSION = '.apk'


def compute_sha256(filepath: str) -> Optional[str]:
    """Compute SHA-256 hash of a file. Returns None on error."""
    try:
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.warning(f"SHA-256 failed for {filepath}: {e}")
        return None


def wait_for_stability(filepath: str, wait_secs: float = 2.0, max_wait: float = 30.0) -> bool:
    """Wait until file size stops changing. Returns True when stable."""
    start = time.monotonic()
    prev_size = -1
    stable_count = 0
    while time.monotonic() - start < max_wait:
        try:
            size = os.path.getsize(filepath)
        except OSError:
            return False
        if size == prev_size:
            stable_count += 1
            if stable_count >= 2:
                return True
        else:
            stable_count = 0
        prev_size = size
        time.sleep(wait_secs / 2)
    return True  # Accept after timeout


class _ForensicEventHandler(FileSystemEventHandler):
    """Watchdog event handler — dispatches events to the FileCollector."""

    def __init__(self, collector: 'FileCollector'):
        super().__init__()
        self._collector = collector

    def on_created(self, event):
        if not event.is_directory:
            self._collector._handle_file_event('file_created', event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._collector._handle_file_event('file_modified', event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._collector._handle_file_event('file_moved', event.dest_path, src_path=event.src_path)


class FileCollector(BaseCollector):
    """
    Monitors test_data/watched_downloads/ for file system events.
    Records SHA-256, metadata, and creates EvidenceFile records.
    Never executes downloaded files.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        project_root = Path(config.get('project_root') or Path(__file__).resolve().parent.parent)
        self._watch_dir = project_root / 'test_data' / 'watched_downloads'
        self._stability_wait = config.get('stability_wait_seconds', 2.0)
        self._observer: Optional[Observer] = None
        self._processed: set = set()  # Track processed paths to deduplicate

    @property
    def name(self) -> str:
        return 'FileCollector'

    def initialize(self) -> bool:
        if not self._watch_dir.exists():
            try:
                self._watch_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"{self.name}: created watch directory {self._watch_dir}")
            except Exception as e:
                self.report_error(f"Cannot create watch directory: {e}", e)
                return False
        logger.info(f"{self.name}: watching {self._watch_dir}")
        return True

    def _collect_loop(self):
        """Start watchdog observer and block until stopped."""
        handler = _ForensicEventHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self._watch_dir), recursive=False)
        self._observer.start()
        logger.info(f"{self.name}: watchdog observer started")
        try:
            while self._running:
                time.sleep(1)
        finally:
            self._observer.stop()
            self._observer.join()
            logger.info(f"{self.name}: watchdog observer stopped")

    def stop(self):
        super().stop()
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()

    def _handle_file_event(self, event_type: str, filepath: str, src_path: Optional[str] = None):
        """Process a watchdog file system event."""
        path = Path(filepath)
        suffix = path.suffix.lower()

        # Skip temp/partial download files
        if suffix in TEMP_EXTENSIONS:
            logger.debug(f"{self.name}: skipping temp file {path.name}")
            return

        # Wait for file to stabilize
        wait_for_stability(filepath, self._stability_wait)

        # Avoid reprocessing same path within seconds
        key = f"{event_type}:{filepath}"
        if key in self._processed:
            return
        self._processed.add(key)
        # Expire cache after 100 entries
        if len(self._processed) > 100:
            self._processed = set(list(self._processed)[-50:])

        # Compute SHA-256
        sha256 = compute_sha256(filepath)

        # Determine specific event type
        if suffix == APK_EXTENSION:
            final_event_type = 'apk_file_observed'
        elif event_type == 'file_created':
            final_event_type = 'file_download_observed'
        else:
            final_event_type = event_type

        try:
            stat = path.stat()
            file_size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        except Exception:
            file_size = 0
            mtime = datetime.now(timezone.utc)

        self._store_event(
            event_type=final_event_type,
            filepath=filepath,
            filename=path.name,
            extension=suffix,
            file_size=file_size,
            sha256=sha256,
            mtime=mtime,
            src_path=src_path,
        )

    def _store_event(self, event_type, filepath, filename, extension, file_size, sha256, mtime, src_path=None):
        """Persist event and evidence record to DB."""
        import django
        import os as _os
        _os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
        try:
            django.setup()
        except Exception:
            pass

        from django.utils import timezone as dj_tz
        from database_app.models import Event, EvidenceFile
        from processing.deduplicator import is_duplicate_hash

        # Deduplicate by SHA-256
        if sha256 and is_duplicate_hash(sha256):
            logger.debug(f"{self.name}: skipping duplicate file {filename} (hash match)")
            return

        source_record_id = f"file:{sha256 or filepath}"

        try:
            # Create evidence record
            evidence = EvidenceFile.objects.create(
                original_filename=filename,
                file_path=filepath,
                evidence_type='apk' if extension == APK_EXTENSION else 'file',
                sha256_hash=sha256 or '',
                file_size=file_size,
                acquisition_timestamp=dj_tz.now(),
                source_description=f"Monitored folder: {self._watch_dir}",
                acquisition_method='watchdog_observer',
                collector_name=self.name,
                metadata={
                    'extension': extension,
                    'mtime': mtime.isoformat(),
                    'src_path': src_path,
                },
            )
        except Exception as e:
            logger.warning(f"{self.name}: EvidenceFile create failed: {e}")
            evidence = None

        try:
            from processing.normalizer import normalize_event
            from processing.validator import validate_event
            raw = {
                'event_timestamp': mtime,
                'event_type': event_type,
                'source': f"watchdog:{self._watch_dir}",
                'description': f"{event_type}: {filename} ({file_size} bytes)",
                'source_record_id': source_record_id,
                'collector_name': self.name,
                'metadata': {
                    'filename': filename,
                    'extension': extension,
                    'file_size': file_size,
                    'sha256': sha256,
                    'src_path': src_path,
                },
            }
            normalized = normalize_event(raw)
            validation_status = validate_event(normalized)
            Event.objects.create(
                event_timestamp=normalized['event_timestamp'],
                event_type=normalized['event_type'],
                source=normalized['source'],
                description=normalized['description'],
                source_record_id=source_record_id,
                collector_name=self.name,
                validation_status=validation_status,
                evidence=evidence,
                metadata=normalized['metadata'],
            )
            self._increment_events()
            logger.info(f"{self.name}: recorded {event_type} for {filename}")
        except Exception as exc:
            self.report_error(f"Failed to store file event: {exc}", exc)
