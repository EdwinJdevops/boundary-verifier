# Boundary Verifier

Experimental infrastructure-security research project for testing whether a declared workload isolation boundary matches the capabilities that can actually be demonstrated from inside the workload's execution context.

## Status

**EXP-001 only. Product thesis is not validated.**

This repository starts as a falsification harness, not a production security platform. The project should be killed or materially reframed if established tooling detects the same meaningful isolation violations with comparable evidence quality and deployment effort.

## EXP-001 question

Can a workload be directly isolated by Kubernetes network controls while still gaining a forbidden effective communication path through an allowed intermediary, and can we produce deterministic, reproducible evidence of that path?

The first experiment intentionally constructs ground truth. It is not evidence of a Kubernetes vulnerability.

## Initial boundary property

For sandbox `tenant-a`:

- direct Internet egress is denied;
- direct communication to `tenant-b` is denied;
- writing a canary in a shared mutable namespace that `tenant-b` can observe is forbidden;
- failure to observe a path is **not** proof that the path is impossible.

## Evidence vocabulary

- `OBSERVED_REACHABLE`: a controlled probe produced evidence that the path worked.
- `OBSERVED_BLOCKED`: the specific controlled probe was blocked.
- `UNKNOWN`: available evidence is insufficient.
- `NOT_EVALUATED`: the path class was outside the experiment.

EXP-001 deliberately avoids claiming universal `PROVEN_BLOCKED`.

## Non-goals

This is not an agent IAM system, MCP firewall, prompt-injection detector, generic CNAPP, SIEM, sandbox implementation, or consequential-action authorization/recovery runtime. It is independent from CER.

See `docs/exp-001.md` and `docs/security-model.md`.
