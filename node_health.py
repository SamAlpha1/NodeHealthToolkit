#!/usr/bin/env python3
"""Linux node health reporter with optional EVM JSON-RPC check."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any
from urllib import request


def read_meminfo() -> dict[str, int]:
    data: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        if not parts:
            continue
        amount = int(parts[0])
        if len(parts) > 1 and parts[1].lower() == "kb":
            amount *= 1024
        data[key] = amount
    return data


def read_uptime() -> float:
    return float(Path("/proc/uptime").read_text().split()[0])


def read_network_totals() -> tuple[int, int]:
    rx = 0
    tx = 0
    lines = Path("/proc/net/dev").read_text().splitlines()[2:]
    for line in lines:
        if ":" not in line:
            continue
        _iface, values = line.split(":", 1)
        fields = values.split()
        if len(fields) >= 9:
            rx += int(fields[0])
            tx += int(fields[8])
    return rx, tx


def rpc_call(url: str, method: str, params: list[Any], timeout: float) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "NodeHealthToolkit/1.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode())
    if "error" in body:
        raise RuntimeError(body["error"])
    return body.get("result")


def rpc_health(url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        chain_id = int(rpc_call(url, "eth_chainId", [], timeout), 16)
        block = int(rpc_call(url, "eth_blockNumber", [], timeout), 16)
        return {
            "healthy": True,
            "chain_id": chain_id,
            "block_number": block,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "healthy": False,
            "chain_id": None,
            "block_number": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "error": str(exc),
        }


def human_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{value} B"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report Linux node health and optional EVM RPC status.")
    parser.add_argument("--disk-path", default="/", help="Filesystem path to inspect.")
    parser.add_argument("--rpc", default=os.getenv("RPC_URL"), help="Optional EVM JSON-RPC URL.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.name != "posix" or not Path("/proc/meminfo").exists():
        raise SystemExit("NodeHealthToolkit currently targets Linux systems with /proc.")

    mem = read_meminfo()
    disk = shutil.disk_usage(args.disk_path)
    rx, tx = read_network_totals()
    load1, load5, load15 = os.getloadavg()
    total_mem = mem.get("MemTotal", 0)
    available_mem = mem.get("MemAvailable", mem.get("MemFree", 0))
    used_mem = max(0, total_mem - available_mem)
    swap_total = mem.get("SwapTotal", 0)
    swap_free = mem.get("SwapFree", 0)

    report: dict[str, Any] = {
        "cpu_count": os.cpu_count(),
        "load_average": {"1m": load1, "5m": load5, "15m": load15},
        "uptime_seconds": read_uptime(),
        "memory": {
            "total_bytes": total_mem,
            "used_bytes": used_mem,
            "available_bytes": available_mem,
            "used_percent": round((used_mem / total_mem * 100), 2) if total_mem else None,
        },
        "swap": {
            "total_bytes": swap_total,
            "used_bytes": max(0, swap_total - swap_free),
        },
        "disk": {
            "path": args.disk_path,
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "used_percent": round((disk.used / disk.total * 100), 2) if disk.total else None,
        },
        "network": {"received_bytes": rx, "transmitted_bytes": tx},
        "rpc": rpc_health(args.rpc, args.timeout) if args.rpc else None,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"CPU: {report['cpu_count']} cores | load: {load1:.2f} {load5:.2f} {load15:.2f}")
        print(f"Uptime: {report['uptime_seconds']:.0f}s")
        print(f"Memory: {human_bytes(used_mem)} / {human_bytes(total_mem)} ({report['memory']['used_percent']}%)")
        print(f"Disk {args.disk_path}: {human_bytes(disk.used)} / {human_bytes(disk.total)} ({report['disk']['used_percent']}%)")
        print(f"Network: RX {human_bytes(rx)} | TX {human_bytes(tx)}")
        if report["rpc"]:
            rpc = report["rpc"]
            state = "OK" if rpc["healthy"] else "FAIL"
            print(f"RPC: {state} | chain={rpc['chain_id']} | block={rpc['block_number']} | latency={rpc['latency_ms']}ms")
            if rpc["error"]:
                print(f"RPC error: {rpc['error']}")
    return 0 if not report["rpc"] or report["rpc"]["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
