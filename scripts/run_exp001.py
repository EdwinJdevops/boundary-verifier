#!/usr/bin/env python3
"""EXP-001 runner: execute controls and emit schema-compatible evidence JSON."""

from __future__ import annotations
import datetime as dt
import hashlib
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
STORE = "canary-store.shared-services.svc.cluster.local:8080"
A_PEER = "peer-endpoint.tenant-a.svc.cluster.local:8080"
B_PEER = "peer-endpoint.tenant-b.svc.cluster.local:8080"

def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)

def kexec(ns: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("kubectl", "-n", ns, "exec", "probe", "--", *args, check=check)

def curl(ns: str, url: str, *extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return kexec(ns, "curl", "--silent", "--show-error", "--fail", "--max-time", "3", *extra, url, check=check)

def edge(src: str, relation: str, dst: str, evidence: str) -> dict[str, str]:
    return {"from": src, "relation": relation, "to": dst, "evidence": evidence}

def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def record(run_id: str, scenario: str, status: str, edges: list[dict[str, str]], digest: str | None = None) -> dict:
    value = {"run_id": run_id, "scenario": scenario, "status": status, "observed_at": now(), "edges": edges}
    if digest is not None:
        value["canary_sha256"] = digest
    return value

def blocked_control(run_id: str, scenario: str, source_ns: str, destination: str, destination_name: str) -> dict:
    probe = curl(source_ns, f"http://{destination}/healthz", check=False)
    if probe.returncode != 0:
        return record(run_id, scenario, "OBSERVED_BLOCKED", [])
    return record(run_id, scenario, "OBSERVED_REACHABLE", [
        edge(f"{source_ns}/probe", "CAN_CONNECT", destination_name, "HTTP health probe succeeded")
    ])

def main() -> int:
    run_id = f"exp001-{int(time.time())}-{secrets.token_hex(4)}"
    canary = secrets.token_hex(32)
    digest = hashlib.sha256(canary.encode()).hexdigest()
    results = [
        blocked_control(run_id, "direct-tenant-a-to-tenant-b", "tenant-a", B_PEER, "tenant-b/peer-endpoint"),
        blocked_control(run_id, "direct-tenant-b-to-tenant-a", "tenant-b", A_PEER, "tenant-a/peer-endpoint"),
    ]

    write = curl("tenant-a", f"http://{STORE}/v1/{run_id}", "-X", "PUT", "--data-binary", canary, check=False)
    if write.returncode != 0:
        results.append(record(run_id, "shared-state-path", "UNKNOWN", []))
    else:
        read = curl("tenant-b", f"http://{STORE}/v1/{run_id}", check=False)
        observed = None
        if read.returncode == 0:
            try:
                observed = json.loads(read.stdout)["value"]
            except (KeyError, json.JSONDecodeError):
                pass
        if observed == canary:
            results.append(record(run_id, "shared-state-path", "OBSERVED_REACHABLE", [
                edge("tenant-a/probe", "CAN_WRITE", "shared-services/canary-store", "HTTP PUT succeeded"),
                edge("shared-services/canary-store", "CAN_PROXY_THROUGH", "tenant-b/probe", "tenant-b HTTP GET returned exact per-run canary"),
            ], digest))
        else:
            results.append(record(run_id, "shared-state-path", "UNKNOWN", [
                edge("tenant-a/probe", "CAN_WRITE", "shared-services/canary-store", "HTTP PUT succeeded")
            ], digest))

    OUT.mkdir(exist_ok=True)
    path = OUT / f"{run_id}.json"
    path.write_text(json.dumps({"experiment": "EXP-001", "results": results}, indent=2) + "\n")
    print(path)
    print(json.dumps({"run_id": run_id, "statuses": {r["scenario"]: r["status"] for r in results}}, indent=2))

    expected = {
        "direct-tenant-a-to-tenant-b": "OBSERVED_BLOCKED",
        "direct-tenant-b-to-tenant-a": "OBSERVED_BLOCKED",
        "shared-state-path": "OBSERVED_REACHABLE",
    }
    return 0 if all(next(r for r in results if r["scenario"] == scenario)["status"] == status for scenario, status in expected.items()) else 1

if __name__ == "__main__":
    sys.exit(main())
