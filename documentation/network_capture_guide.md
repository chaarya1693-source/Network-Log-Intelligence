# Network Capture & Offline Import Guide — Stage 1

This document explains the network monitoring subsystem, offline PCAP/PCAPNG ingestion, and protocol metadata extraction.

---

## 1. Network Subsystem Philosophy

Stage 1 prioritizes **offline PCAP/PCAPNG capture import** over fragile live capture for three forensic reasons:
1. **Evidence Repeatability**: An exported PCAP file can be hashed, archived, and re-analyzed with deterministic results.
2. **Permission Safety**: Offline parsing runs in user space without requiring administrator privileges, custom Npcap drivers, or promiscuous mode adapter bindings.
3. **Chain of Custody**: Cryptographic integrity (SHA-256) is established directly on the imported capture file before any packet parsing occurs.

---

## 2. Ingesting PCAP Files

### 2.1 Supported File Types
- Standard Libpcap (`.pcap`)
- Next Generation PCAP (`.pcapng`)

### 2.2 Ingestion via CLI
Use the `NetworkCollector` programmatically or via CLI import:
```python
from collectors.network_collector import NetworkCollector

collector = NetworkCollector({})
collector.initialize()
stored_count = collector.import_pcap("test_data/network_samples/sample_traffic.pcap")
print(f"Stored {stored_count} packet events.")
```

### 2.3 Automated Folder Watch
In daemon mode, `NetworkCollector` automatically scans `test_data/network_samples/` for newly placed `.pcap` and `.pcapng` files and ingests them without human intervention.

---

## 3. Metadata Extracted per Frame

For each network packet in the capture:
- **Frame Number**: Original frame index within the PCAP (evidence reference).
- **Timestamp**: Epoch time normalized to UTC-aware datetime.
- **Source IP & Port**: Extracted from IPv4 (`dpkt.ip.IP`) or IPv6 (`dpkt.ip6.IP6`) headers.
- **Destination IP & Port**: Extracted from network layer.
- **Protocol**: TCP, UDP, ICMP, IPv6, or raw protocol name.
- **Packet Length**: Byte length of the captured frame.
- **TCP Flags**: Explicit string flags (`SYN`, `ACK`, `FIN`, `RST`).
- **DNS Queries**: Extracted from UDP port 53 DNS query structures (`dpkt.dns.DNS`).

---

## 4. Privacy & Forensic Boundaries

> [!IMPORTANT]
> - **No HTTPS Decryption**: The collector never attempts TLS interception, Man-in-the-Middle (MitM) certificate proxying, or session key recovery.
> - **No Credential Harvesting**: Packet payloads containing user passwords, cookies, or personal content are never scraped or stored in plaintext.
> - **Switched Network Caveat**: In standard Wi-Fi or switched Ethernet environments, a workstation only captures unicast packets intended for its own MAC address, alongside broadcast/multicast traffic. Traffic from other devices on the same Wi-Fi network cannot be seen without specialized port mirroring or monitor-mode hardware.

