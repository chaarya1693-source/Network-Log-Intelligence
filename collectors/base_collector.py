"""
collectors/base_collector.py — Abstract base class for all Stage 1 collectors.
"""
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('collectors')


class BaseCollector(ABC):
    """
    Abstract base class for all forensic data collectors.
    Provides lifecycle management, error tracking, and CollectorRun DB integration.
    """

    def __init__(self, config: dict):
        self.config = config
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_collection_time: Optional[datetime] = None
        self._total_events = 0
        self._total_errors = 0
        self._last_error: Optional[str] = None
        self._collector_run_id: Optional[int] = None
        self._lock = threading.Lock()

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable collector name."""
        ...

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_collection_time(self) -> Optional[datetime]:
        return self._last_collection_time

    @property
    def total_events(self) -> int:
        return self._total_events

    @property
    def total_errors(self) -> int:
        return self._total_errors

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @abstractmethod
    def initialize(self) -> bool:
        """Validate prerequisites and prepare resources. Return True if ready."""
        ...

    @abstractmethod
    def _collect_loop(self):
        """Main collection loop — runs in background thread."""
        ...

    def start(self):
        """Start the collector in a background thread."""
        if self._running:
            logger.warning(f"{self.name}: already running")
            return
        if not self.initialize():
            logger.error(f"{self.name}: initialization failed — not starting")
            return
        self._start_collector_run()
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, name=self.name, daemon=True)
        self._thread.start()
        logger.info(f"{self.name}: started")

    def stop(self):
        """Signal the collector to stop and wait for thread to finish."""
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._complete_collector_run()
        logger.info(f"{self.name}: stopped (events={self._total_events}, errors={self._total_errors})")

    def get_status(self) -> dict:
        return {
            'name': self.name,
            'is_running': self._running,
            'total_events': self._total_events,
            'total_errors': self._total_errors,
            'last_error': self._last_error,
            'last_collection_time': self._last_collection_time.isoformat() if self._last_collection_time else None,
            'collector_run_id': self._collector_run_id,
        }

    def report_error(self, msg: str, exc: Optional[Exception] = None):
        with self._lock:
            self._total_errors += 1
            self._last_error = msg
            if exc:
                logger.error(f"{self.name}: {msg}", exc_info=exc)
            else:
                logger.error(f"{self.name}: {msg}")
        self._update_run_errors()

    def _increment_events(self, count: int = 1):
        with self._lock:
            self._total_events += count
            self._last_collection_time = datetime.now(timezone.utc)
        self._update_run_count()

    # ---- DB integration (lazy import to avoid circular dependency) ----

    def _start_collector_run(self):
        try:
            import django
            os_env = __import__('os').environ
            os_env.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
            django.setup()
        except Exception:
            pass
        try:
            from database_app.models import CollectorRun
            run = CollectorRun.objects.create(collector_name=self.name, status='running')
            self._collector_run_id = run.id
        except Exception as e:
            logger.warning(f"{self.name}: could not create CollectorRun record: {e}")

    def _complete_collector_run(self):
        if not self._collector_run_id:
            return
        try:
            from database_app.models import CollectorRun
            from django.utils import timezone as dj_tz
            run = CollectorRun.objects.get(id=self._collector_run_id)
            run.status = 'completed'
            run.end_time = dj_tz.now()
            run.event_count = self._total_events
            run.error_count = self._total_errors
            run.save()
        except Exception as e:
            logger.warning(f"{self.name}: could not update CollectorRun: {e}")

    def _update_run_count(self):
        if not self._collector_run_id:
            return
        try:
            from database_app.models import CollectorRun
            CollectorRun.objects.filter(id=self._collector_run_id).update(event_count=self._total_events)
        except Exception:
            pass

    def _update_run_errors(self):
        if not self._collector_run_id:
            return
        try:
            from database_app.models import CollectorRun
            CollectorRun.objects.filter(id=self._collector_run_id).update(
                error_count=self._total_errors,
                error_details=[self._last_error],
            )
        except Exception:
            pass
