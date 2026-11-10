"""
tests/test_network_collector.py — Unit tests for offline network packet collector.
Verifies PCAP/PCAPNG parsing via dpkt, packet metadata extraction,
and resilience against malformed or empty captures.
"""
import os
from pathlib import Path
import pytest
from collectors.network_collector import NetworkCollector, _parse_pcap_dpkt, get_tshark_path


@pytest.fixture
def network_samples_dir():
    return Path(__file__).resolve().parent.parent / "test_data" / "network_samples"


def test_parse_valid_synthetic_pcap(network_samples_dir):
    """Test dpkt extracts expected packet metadata from generated PCAP."""
    pcap_path = str(network_samples_dir / "sample_traffic.pcap")
    assert os.path.exists(pcap_path), "sample_traffic.pcap must exist"

    packets = list(_parse_pcap_dpkt(pcap_path))
    assert len(packets) == 5

    # Check DNS packet (frame 1)
    dns_pkt = packets[0]
    assert dns_pkt["protocol"] == "UDP"
    assert dns_pkt["dst_port"] == 53
    assert "forensics.local" in dns_pkt["dns_query"]

    # Check TCP SYN packet (frame 2)
    syn_pkt = packets[1]
    assert syn_pkt["protocol"] == "TCP"
    assert syn_pkt["dst_port"] == 80
    assert "SYN" in syn_pkt["tcp_flags"]


def test_parse_empty_pcap(network_samples_dir):
    """Test parsing an empty PCAP file returns 0 packets without crashing."""
    empty_pcap = str(network_samples_dir / "sample_empty.pcap")
    packets = list(_parse_pcap_dpkt(empty_pcap))
    assert len(packets) == 0


def test_parse_malformed_pcap(network_samples_dir):
    """Test parsing a truncated or corrupted PCAP handles errors gracefully."""
    malformed_pcap = str(network_samples_dir / "sample_malformed.pcap")
    packets = list(_parse_pcap_dpkt(malformed_pcap))
    assert len(packets) == 0


@pytest.mark.django_db
def test_network_collector_import_pcap(network_samples_dir):
    """Test NetworkCollector imports PCAP file into EvidenceFile and Event models."""
    pcap_path = str(network_samples_dir / "sample_traffic.pcap")
    collector = NetworkCollector({"project_root": str(Path(__file__).resolve().parent.parent)})
    collector.initialize()

    count = collector.import_pcap(pcap_path)
    assert count == 5

    from database_app.models import Event, EvidenceFile
    evidence = EvidenceFile.objects.filter(original_filename="sample_traffic.pcap").first()
    assert evidence is not None
    assert evidence.evidence_type == "pcap"
    assert len(evidence.sha256_hash) == 64

    events = Event.objects.filter(collector_name="NetworkCollector")
    assert events.count() == 5
    for ev in events:
        assert ev.event_type == "network_packet"
        assert ev.evidence == evidence
        assert "src_ip" in ev.metadata

    # Re-importing same file must deduplicate (return 0 new events)
    reimport_count = collector.import_pcap(pcap_path)
    assert reimport_count == 0

