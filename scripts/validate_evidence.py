#!/usr/bin/env python3
"""Validate EXP-001 evidence schema and cross-record invariants."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/evidence.schema.json").read_text())
EXPECTED = {
    "direct-tenant-a-to-tenant-b": "OBSERVED_BLOCKED",
    "direct-tenant-b-to-tenant-a": "OBSERVED_BLOCKED",
    "shared-state-path": "OBSERVED_REACHABLE",
}


def validate(path: Path) -> None:
    doc = json.loads(path.read_text())
    Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(doc)
    results = doc["results"]
    if len(results) != 3:
        raise ValueError(f"expected exactly 3 results, got {len(results)}")
    run_ids = {r["run_id"] for r in results}
    if len(run_ids) != 1:
        raise ValueError("all observations must belong to one run_id")
    scenarios = {r["scenario"] for r in results}
    if scenarios != set(EXPECTED):
        raise ValueError(f"scenario set mismatch: {sorted(scenarios)}")
    by_scenario = {r["scenario"]: r for r in results}
    for scenario, expected in EXPECTED.items():
        if by_scenario[scenario]["status"] != expected:
            raise ValueError(f"{scenario}: expected {expected}, got {by_scenario[scenario]['status']}")
    for scenario in ("direct-tenant-a-to-tenant-b", "direct-tenant-b-to-tenant-a"):
        observation = by_scenario[scenario]["observation"]
        if observation.get("curl_exit_code") != 28:
            raise ValueError(f"{scenario}: blocked evidence must be curl timeout exit 28")
    shared = by_scenario["shared-state-path"]
    if shared["observation"].get("write_curl_exit_code") != 0 or shared["observation"].get("read_curl_exit_code") != 0:
        raise ValueError("shared-state evidence requires successful write and read")
    if shared["observation"].get("exact_canary_match") is not True:
        raise ValueError("shared-state evidence requires exact per-run canary equality")
    print(f"validated {path}: run_id={next(iter(run_ids))}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate_evidence.py <evidence.json> [...]", file=sys.stderr)
        return 2
    for arg in sys.argv[1:]:
        validate(Path(arg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
