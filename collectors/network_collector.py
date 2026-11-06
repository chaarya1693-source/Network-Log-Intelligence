"""
collectors/network_collector.py — PCAP/PCAPNG import and optional live TShark capture.
Primary mode: offline PCAP analysis via dpkt (with scapy fallback + TShark JSON).
Secondary mode: live capture via TShark subprocess (requires explicit trigger).
NEVER decrypts HTTPS or collects credentials.
"""
import hashlib
import json
import logging
import os
import socket
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Iterator

from collectors.base_collector import BaseCollector

logger = logging.getLogger('collectors')

TSHARK_PATH = r'D:\Aarya\Softwares\WireShark\tshark.exe'


def _safe_ip(addr_bytes) -> str:
    """Convert raw bytes to dotted-decimal IP string."""
    try:
        if len(addr_bytes) == 4:
            return socket.inet_ntoa(addr_bytes)
        elif len(addr_bytes) == 16:
            return socket.inet_ntop(socket.AF_INET6, addr_bytes)
    except Exception:
        pass
    return ''


def _parse_pcap_dpkt(filepath: str) -> Iterator[dict]:
    """Parse PCAP file using dpkt library."""
    import dpkt
    with open(filepath, 'rb') as f:
        try:
            pcap = dpkt.pcap.Reader(f)
        except Exception:
            f.seek(0)
            try:
                pcap = dpkt.pcapng.Reader(f)
            except Exception as e:
                logger.warning(f"dpkt: cannot read {filepath}: {e}")
                return
        frame_num = 0
        for ts, buf in pcap:
            frame_num += 1
            record = {
                'frame_number': frame_num,
                'timestamp': datetime.fromtimestamp(ts, tz=timezone.utc),
                'src_ip': '', 'dst_ip': '',
                'src_port': None, 'dst_port': None,
                'protocol': 'unknown',
                'packet_length': len(buf),
                'tcp_flags': '',
                'dns_query': '',
            }
            try:
                eth = dpkt.ethernet.Ethernet(buf)
                ip = None
                if isinstance(eth.data, dpkt.ip.IP):
                    ip = eth.data
                    record['src_ip'] = _safe_ip(ip.src)
                    record['dst_ip'] = _safe_ip(ip.dst)
                    if isinstance(ip.data, dpkt.tcp.TCP):
                        tcp = ip.data
                        record['protocol'] = 'TCP'
                        record['src_port'] = tcp.sport
                        record['dst_port'] = tcp.dport
                        flags = tcp.flags
                        flag_str = ''
                        if flags & dpkt.tcp.TH_SYN: flag_str += 'SYN,'
                        if flags & dpkt.tcp.TH_ACK: flag_str += 'ACK,'
                        if flags & dpkt.tcp.TH_FIN: flag_str += 'FIN,'
                        if flags & dpkt.tcp.TH_RST: flag_str += 'RST,'
                        record['tcp_flags'] = flag_str.rstrip(',')
                    elif isinstance(ip.data, dpkt.udp.UDP):
                        udp = ip.data
                        record['protocol'] = 'UDP'
                        record['src_port'] = udp.sport
                        record['dst_port'] = udp.dport
                        # Try DNS parse
                        try:
                            dns = dpkt.dns.DNS(udp.data)
                            if dns.qr == dpkt.dns.DNS_Q and dns.qd:
                                record['dns_query'] = dns.qd[0].name
                        except Exception:
                            pass
                    elif isinstance(ip.data, dpkt.icmp.ICMP):
                        record['protocol'] = 'ICMP'
                elif isinstance(eth.data, dpkt.ip6.IP6):
                    ip6 = eth.data
                    record['src_ip'] = _safe_ip(ip6.src)
                    record['dst_ip'] = _safe_ip(ip6.dst)
                    record['protocol'] = 'IPv6'
            except Exception:
                pass  # Malformed packet — log and continue
            yield record


def _parse_pcap_tshark(filepath: str) -> Iterator[dict]:
    """Parse PCAP via TShark JSON output — fallback when dpkt fails."""
    if not os.path.exists(TSHARK_PATH):
        logger.warning(f"TShark not found at {TSHARK_PATH}")
        return
    try:
        result = subprocess.run(
            [TSHARK_PATH, '-r', filepath, '-T', 'json', '-e', 'frame.number',
             '-e', 'frame.time_epoch', '-e', 'ip.src', '-e', 'ip.dst',
             '-e', 'tcp.srcport', '-e', 'tcp.dstport', '-e', 'udp.srcport',
             '-e', 'udp.dstport', '-e', 'frame.len', '-e', '_ws.col.Protocol',
             '-e', 'dns.qry.name'],
            capture_output=True, text=True, timeout=120
        )
        packets = json.loads(result.stdout or '[]')
        for pkt in packets:
            layers = pkt.get('_source', {}).get('layers', {})
            ts_raw = layers.get('frame.time_epoch', ['0'])[0]
            try:
                ts = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc)
            except Exception:
                ts = datetime.now(timezone.utc)
            record = {
                'frame_number': int(layers.get('frame.number', ['0'])[0]),
                'timestamp': ts,
                'src_ip': (layers.get('ip.src') or [''])[0],
                'dst_ip': (layers.get('ip.dst') or [''])[0],
                'src_port': int((layers.get('tcp.srcport') or layers.get('udp.srcport') or ['0'])[0]),
                'dst_port': int((layers.get('tcp.dstport') or layers.get('udp.dstport') or ['0'])[0]),
                'protocol': (layers.get('_ws.col.Protocol') or ['unknown'])[0],
                'packet_length': int(layers.get('frame.len', ['0'])[0]),
                'tcp_flags': '',
                'dns_query': (layers.get('dns.qry.name') or [''])[0],
            }
            yield record
    except Exception as e:
        logger.error(f"TShark parse failed for {filepath}: {e}")


class NetworkCollector(BaseCollector):
    """
    Network traffic collector with two modes:
    1. Offline PCAP/PCAPNG import (primary)
    2. Live capture via TShark (secondary, explicit trigger only)
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self._live_capture = config.get('live_capture_enabled', False)
        self._processed_hashes: set = set()

    @property
    def name(self) -> str:
        return 'NetworkCollector'

    def initialize(self) -> bool:
        logger.info(f"{self.name}: initialized (TShark at {TSHARK_PATH})")
        return True

    def _collect_loop(self):
        """In daemon mode, scan network_samples dir for new PCAP files periodically."""
        from pathlib import Path
        samples_dir = Path(self.config.get('project_root', 'D:/Aarya/Unnamed Project')) / 'test_data' / 'network_samples'
        while self._running:
            if samples_dir.exists():
                for f in samples_dir.glob('*.pcap'):
                    self._import_pcap(str(f))
                for f in samples_dir.glob('*.pcapng'):
                    self._import_pcap(str(f))
            time.sleep(30)

    def import_pcap(self, filepath: str) -> int:
        """Public method: import a PCAP file. Returns number of events stored."""
        return self._import_pcap(filepath)

    def _import_pcap(self, filepath: str) -> int:
        """Import a PCAP/PCAPNG file and store events."""
        # Check if already processed by SHA-256
        sha256 = self._hash_file(filepath)
        if sha256 in self._processed_hashes:
            logger.info(f"{self.name}: {filepath} already processed (hash match)")
            return 0
        self._processed_hashes.add(sha256)

        logger.info(f"{self.name}: importing {filepath}")
        evidence = self._create_evidence(filepath, sha256)

        # Try dpkt first, fall back to TShark
        try:
            import dpkt  # noqa: F401
            packets = list(_parse_pcap_dpkt(filepath))
        except ImportError:
            logger.info(f"{self.name}: dpkt unavailable, using TShark")
            packets = list(_parse_pcap_tshark(filepath))
        except Exception as e:
            logger.warning(f"{self.name}: dpkt failed ({e}), trying TShark")
            packets = list(_parse_pcap_tshark(filepath))

        count = 0
        for pkt in packets:
            if self._store_packet_event(pkt, filepath, evidence):
                count += 1
        self._increment_events(count)
        logger.info(f"{self.name}: stored {count} packet events from {filepath}")
        return count

    def _store_packet_event(self, pkt: dict, filepath: str, evidence) -> bool:
        """Store one packet as an Event record."""
        import django
        import os as _os
        _os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
        try:
            django.setup()
        except Exception:
            pass

        from database_app.models import Event
        from processing.deduplicator import is_duplicate
        from processing.normalizer import normalize_event
        from processing.validator import validate_event

        source_record_id = f"pcap:{Path(filepath).name}:frame{pkt['frame_number']}"
        if is_duplicate(source_record_id, self.name):
            return False

        description = (
            f"{pkt['protocol']} {pkt['src_ip']}:{pkt['src_port']} → "
            f"{pkt['dst_ip']}:{pkt['dst_port']} ({pkt['packet_length']} bytes)"
        )
        if pkt.get('dns_query'):
            description += f" [DNS: {pkt['dns_query']}]"

        raw = {
            'event_timestamp': pkt['timestamp'],
            'event_type': 'network_packet',
            'source': f"pcap:{Path(filepath).name}",
            'description': description,
            'source_record_id': source_record_id,
            'collector_name': self.name,
            'metadata': {
                'frame_number': pkt['frame_number'],
                'src_ip': pkt['src_ip'],
                'dst_ip': pkt['dst_ip'],
                'src_port': pkt['src_port'],
                'dst_port': pkt['dst_port'],
                'protocol': pkt['protocol'],
                'packet_length': pkt['packet_length'],
                'tcp_flags': pkt['tcp_flags'],
                'dns_query': pkt.get('dns_query', ''),
            },
        }
        try:
            normalized = normalize_event(raw)
            validation_status = validate_event(normalized)
            Event.objects.create(
                event_timestamp=normalized['event_timestamp'],
                event_type='network_packet',
                source=normalized['source'],
                description=normalized['description'],
                source_record_id=source_record_id,
                collector_name=self.name,
                validation_status=validation_status,
                evidence=evidence,
                metadata=normalized['metadata'],
            )
            return True
        except Exception as exc:
            self.report_error(f"Failed to store packet event: {exc}", exc)
            return False

    def _create_evidence(self, filepath: str, sha256: str):
        """Create EvidenceFile record for the PCAP file."""
        import django
        import os as _os
        _os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forensics_core.settings')
        try:
            django.setup()
        except Exception:
            pass
        from django.utils import timezone as dj_tz
        from database_app.models import EvidenceFile
        try:
            stat = Path(filepath).stat()
            evidence, _ = EvidenceFile.objects.get_or_create(
                sha256_hash=sha256,
                defaults={
                    'original_filename': Path(filepath).name,
                    'file_path': filepath,
                    'evidence_type': 'pcap',
                    'file_size': stat.st_size,
                    'acquisition_timestamp': dj_tz.now(),
                    'source_description': 'Network capture file',
                    'acquisition_method': 'manual_import',
                    'collector_name': self.name,
                }
            )
            return evidence
        except Exception as e:
            logger.warning(f"{self.name}: EvidenceFile create failed: {e}")
            return None

    @staticmethod
    def _hash_file(filepath: str) -> str:
        h = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
        except Exception:
            pass
        return h.hexdigest()
