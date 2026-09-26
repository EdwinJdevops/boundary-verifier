#!/usr/bin/env python3
"""Fail if Boundary Verifier EXP-001 resources remain after Terraform destroy."""
from __future__ import annotations
import json
import subprocess
import sys

PROJECT = "boundary-verifier"
EXPERIMENT = "EXP-001"


def aws(*args: str) -> dict:
    result = subprocess.run(["aws", *args, "--output", "json"], check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def main() -> int:
    region = sys.argv[1] if len(sys.argv) > 1 else "us-east-1"
    clusters = aws("eks", "list-clusters", "--region", region).get("clusters", [])
    leftovers = []
    for name in clusters:
        detail = aws("eks", "describe-cluster", "--region", region, "--name", name)["cluster"]
        tags = detail.get("tags", {})
        if tags.get("Project") == PROJECT and tags.get("Experiment") == EXPERIMENT:
            leftovers.append({"type": "eks-cluster", "name": name})
    if leftovers:
        print(json.dumps({"leftovers": leftovers}, indent=2))
        return 1
    print(json.dumps({"leftovers": []}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
