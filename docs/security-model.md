# Security model

## Claim boundary

Boundary Verifier reports experimentally observed capabilities. It does not certify that an environment is secure.

Absence of an observed path is not evidence that no path exists.

## Trust assumptions

EXP-001 trusts:

- the Kubernetes control plane hosting the lab;
- the verifier's local evidence store;
- unique canary generation;
- clocks only for ordering within the experiment, not as a cryptographic trust anchor.

The sandboxed workloads and shared lab service are treated as potentially capable of communicating only through the capabilities intentionally exposed by the fixture.

## Safe probing rules

- use synthetic canaries only;
- never read real tenant secrets;
- never probe third-party infrastructure;
- never attempt sandbox escapes;
- keep targets inside the controlled lab unless a later experiment explicitly provisions an owned canary endpoint;
- probes must be bounded by timeout and payload size;
- cleanup must remove generated canaries and temporary workloads.

## Result semantics

`OBSERVED_REACHABLE` requires positive evidence from both the initiating probe and destination/intermediary evidence where applicable.

`OBSERVED_BLOCKED` means one defined probe did not traverse the tested edge under the tested conditions.

`UNKNOWN` means the verifier cannot make a defensible statement from available evidence.

`NOT_EVALUATED` means no test for that capability/path class ran.
