"""
main.py — Orchestrator for HPC-Accelerated AI-Enhanced Digital Forensics System Stage 1.
Starts collectors and Django dev server together.

Usage:
    .venv\Scripts\python.exe main.py [--collectors usb,file,network,android] [--port 8000]
"""
import argparse
import os
import sys
import signal
import threading
import time
import logging

# Set up Django before importing anything Django-related
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')

import django
django.setup()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('main')


def load_config() -> dict:
    """Load configuration from config/settings.yaml."""
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'settings.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Could not load config: {e} — using defaults")
        return {}


def start_collectors(names: list, config: dict) -> dict:
    """Initialize and start selected collectors. Returns registry dict."""
    registry = {}

    if 'usb' in names:
        try:
            from collectors.usb_collector import USBCollector
            c = USBCollector(config)
            registry['USBCollector'] = c
            logger.info("USBCollector registered")
        except Exception as e:
            logger.error(f"USBCollector init failed: {e}")

    if 'file' in names:
        try:
            from collectors.file_collector import FileCollector
            c = FileCollector({**config, 'project_root': os.path.dirname(__file__)})
            registry['FileCollector'] = c
            logger.info("FileCollector registered")
        except Exception as e:
            logger.error(f"FileCollector init failed: {e}")

    if 'network' in names:
        try:
            from collectors.network_collector import NetworkCollector
            c = NetworkCollector({**config, 'project_root': os.path.dirname(__file__)})
            registry['NetworkCollector'] = c
            logger.info("NetworkCollector registered")
        except Exception as e:
            logger.error(f"NetworkCollector init failed: {e}")

    if 'android' in names:
        try:
            from collectors.android_collector import AndroidCollector
            c = AndroidCollector(config)
            registry['AndroidCollector'] = c
            logger.info("AndroidCollector registered")
        except Exception as e:
            logger.error(f"AndroidCollector init failed: {e}")

    # Inject registry into API views
    try:
        from api_app.views import set_collector_registry
        set_collector_registry(registry)
    except Exception as e:
        logger.warning(f"Could not set collector registry in API: {e}")

    # Start all registered collectors
    for name, collector in registry.items():
        try:
            collector.start()
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")

    return registry


def stop_all(registry: dict):
    """Gracefully stop all running collectors."""
    logger.info("Stopping all collectors...")
    for name, collector in registry.items():
        try:
            if collector.is_running:
                collector.stop()
                logger.info(f"{name} stopped")
        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")


def run_django_server(port: int = 8000):
    """Start Django development server in this thread (blocking)."""
    from django.core.management import call_command
    logger.info(f"Starting Django server at http://127.0.0.1:{port}/")
    try:
        call_command('runserver', f'0.0.0.0:{port}', '--noreload')
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description='ForensicsOS Stage 1 Orchestrator')
    parser.add_argument('--collectors', default='file', help='Comma-separated: usb,file,network,android')
    parser.add_argument('--port', type=int, default=8000, help='Django server port (default: 8000)')
    parser.add_argument('--no-server', action='store_true', help='Skip Django server (collectors only)')
    args = parser.parse_args()

    collector_names = [c.strip().lower() for c in args.collectors.split(',')]
    config = load_config()

    logger.info(f"=== ForensicsOS Stage 1 Starting ===")
    logger.info(f"Collectors: {collector_names}")
    logger.info(f"Dashboard: http://127.0.0.1:{args.port}/")
    logger.info(f"API:       http://127.0.0.1:{args.port}/api/")

    registry = start_collectors(collector_names, config)
    logger.info(f"Started {len(registry)} collector(s)")

    # Handle Ctrl+C
    def shutdown(signum, frame):
        logger.info("Received shutdown signal")
        stop_all(registry)
        sys.exit(0)
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if args.no_server:
        logger.info("Running collectors only (no Django server)")
        try:
            while True:
                time.sleep(10)
                for name, c in registry.items():
                    logger.info(f"  {name}: events={c.total_events}, errors={c.total_errors}, running={c.is_running}")
        except KeyboardInterrupt:
            stop_all(registry)
    else:
        try:
            run_django_server(args.port)
        finally:
            stop_all(registry)


if __name__ == '__main__':
    main()
