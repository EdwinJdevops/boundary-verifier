#!/usr/bin/env python3
"""EXP-001 runner: execute controls and emit auditable evidence JSON."""

from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def service_ip(namespace: str, name: str) -> str:
    result = run("kubectl", "-n", namespace, "get", "service", name, "-o", "jsonpath={.spec.clusterIP}")
    value = result.stdout.strip()
    if not value or value == "None":
        raise RuntimeError(f"service {namespace}/{name} has no ClusterIP")
    return value


def kexec(ns: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("kubectl", "-n", ns, "exec", "probe", "--", *args, check=check)


def curl(ns: str, url: str, *extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return kexec(ns, "curl", "--silent", "--show-error", "--fail", "--connect-timeout", "1", "--max-time", "3", *extra, url, check=check)


def edge(src: str, relation: str, dst: str, evidence: str) -> dict[str, str]:
    return {"from": src, "relation": relation, "to": dst, "evidence": evidence}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def classify_connect_probe(probe: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    """Classify curl without turning arbitrary transport failures into policy evidence.

    curl 28 is a timeout. EXP-001 establishes endpoint liveness immediately before
    policy application, so a post-policy timeout is the narrow negative observation
    accepted by this experiment. DNS, connection-refused, TLS, HTTP and exec errors
    remain UNKNOWN rather than being mislabeled as policy enforcement.
    """
    if probe.returncode == 0:
        return "OBSERVED_REACHABLE", "HTTP health probe succeeded"
    if probe.returncode == 28:
        return "OBSERVED_BLOCKED", "HTTP probe timed out after pre-policy liveness control"
    detail = (probe.stderr or probe.stdout or "curl failed").strip()[-500:]
    return "UNKNOWN", f"probe failed with curl exit {probe.returncode}: {detail}"


def record(run_id: str, scenario: str, status: str, edges: list[dict[str, str]], observation: dict, digest: str | None = None) -> dict:
    value = {
        "run_id": run_id,
        "scenario": scenario,
        "status": status,
        "observed_at": now(),
        "observation": observation,
        "edges": edges,
    }
    if digest is not None:
        value["canary_sha256"] = digest
    return value


def blocked_control(run_id: str, scenario: str, source_ns: str, destination_ip: str, destination_name: str) -> dict:
    probe = curl(source_ns, f"http://{destination_ip}:8080/healthz", check=False)
    status, detail = classify_connect_probe(probe)
    edges = []
    if status == "OBSERVED_REACHABLE":
        edges.append(edge(f"{source_ns}/probe", "CAN_CONNECT", destination_name, detail))
    return record(run_id, scenario, status, edges, {
        "probe": "http-health",
        "curl_exit_code": probe.returncode,
        "detail": detail,
    })


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provenance() -> dict:
    policy_files = [
        ROOT / "lab/kubernetes/10-default-deny.yaml",
        ROOT / "lab/kubernetes/11-default-deny-ingress.yaml",
        ROOT / "lab/kubernetes/20-allow-shared-canary.yaml",
        ROOT / "lab/kubernetes/21-allow-canary-ingress.yaml",
    ]
    git_sha = os.getenv("BV_GIT_SHA") or run("git", "rev-parse", "HEAD").stdout.strip()
    server = run("kubectl", "version", "-o", "json")
    server_version = json.loads(server.stdout)["serverVersion"]["gitVersion"]
    return {
        "git_sha": git_sha,
        "kubernetes_version": server_version,
        "kind_node_image": os.getenv("KIND_NODE_IMAGE", "UNKNOWN"),
        "calico_commit": os.getenv("CALICO_COMMIT", "UNKNOWN"),
        "policy_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in policy_files},
    }


def main() -> int:
    run_id = f"exp001-{int(time.time())}-{secrets.token_hex(4)}"
    canary = secrets.token_hex(32)
    digest = hashlib.sha256(canary.encode()).hexdigest()
    store_ip = service_ip("shared-services", "canary-store")
    a_peer_ip = service_ip("tenant-a", "peer-endpoint")
    b_peer_ip = service_ip("tenant-b", "peer-endpoint")

    results = [
        blocked_control(run_id, "direct-tenant-a-to-tenant-b", "tenant-a", b_peer_ip, "tenant-b/peer-endpoint"),
        blocked_control(run_id, "direct-tenant-b-to-tenant-a", "tenant-b", a_peer_ip, "tenant-a/peer-endpoint"),
    ]

    write = curl("tenant-a", f"http://{store_ip}:8080/v1/{run_id}", "-X", "PUT", "--data-binary", canary, check=False)
    if write.returncode != 0:
        detail = (write.stderr or write.stdout or "write failed").strip()[-500:]
        results.append(record(run_id, "shared-state-path", "UNKNOWN", [], {
            "write_curl_exit_code": write.returncode,
            "read_curl_exit_code": None,
            "detail": detail,
        }, digest))
    else:
        read = curl("tenant-b", f"http://{store_ip}:8080/v1/{run_id}", check=False)
        observed = None
        if read.returncode == 0:
            try:
                observed = json.loads(read.stdout)["value"]
            except (KeyError, json.JSONDecodeError):
                pass
        exact_match = observed == canary
        observation = {
            "write_curl_exit_code": write.returncode,
            "read_curl_exit_code": read.returncode,
            "exact_canary_match": exact_match,
        }
        if exact_match:
            results.append(record(run_id, "shared-state-path", "OBSERVED_REACHABLE", [
                edge("tenant-a/probe", "CAN_WRITE", "shared-services/canary-store", "HTTP PUT succeeded"),
                edge("shared-services/canary-store", "CAN_PROXY_THROUGH", "tenant-b/probe", "tenant-b HTTP GET returned exact per-run canary"),
            ], observation, digest))
        else:
            results.append(record(run_id, "shared-state-path", "UNKNOWN", [
                edge("tenant-a/probe", "CAN_WRITE", "shared-services/canary-store", "HTTP PUT succeeded")
            ], observation, digest))

    document = {
        "experiment": "EXP-001",
        "evidence_version": 2,
        "provenance": provenance(),
        "results": results,
    }
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{run_id}.json"
    path.write_text(json.dumps(document, indent=2) + "\n")
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
