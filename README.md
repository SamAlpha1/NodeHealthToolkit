# Node Health Toolkit

A lightweight Linux node-health reporter for VPS and blockchain-node operators.

It summarizes system load, memory, disk, uptime, network counters, and can optionally test an EVM-compatible JSON-RPC endpoint from the same machine.

## Features

- Linux load averages and CPU count
- Memory and swap usage from `/proc/meminfo`
- Disk usage for a selected path
- System uptime
- Aggregate network RX/TX counters
- Optional EVM RPC latency, chain ID, and block height
- Human-readable or JSON output
- Standard-library only

## Requirements

- Linux
- Python 3.10+

## Quick start

```bash
git clone https://github.com/SamAlpha1/NodeHealthToolkit.git
cd NodeHealthToolkit
python node_health.py
```

Check a specific filesystem:

```bash
python node_health.py --disk-path /var/lib
```

Include an RPC health check:

```bash
python node_health.py --rpc https://ethereum-rpc.publicnode.com
```

JSON output:

```bash
python node_health.py --rpc https://ethereum-rpc.publicnode.com --json
```

Environment configuration is available through `.env.example`.

## Security

The tool only reads local system statistics and optionally performs read-only JSON-RPC calls. It does not require private keys or wallet credentials.

---

## More from SamAlpha1

Before running unfamiliar GitHub or Web3 code, scan the account and its public repositories with **[GitHub Trust Auditor](https://samalpha1.github.io/GitHubTrustAuditor/)**.

Maintained by **[SamAlpha1](https://github.com/SamAlpha1)** · Follow **[@samalpha_ on X](https://x.com/samalpha_)**
