# Invariant and evidence contract v1 — design specification

This is a proposed contract, not an implemented verifier API.

## Invariant

An invariant identifies a source workload identity, a protected destination tenant/data domain, a capability class, an explicitly forbidden outcome, and the authorization source. It MUST be defined independently of the test fixture.

Example (illustrative, not a real customer policy):

```yaml
id: tenant-write-isolation
owner: platform-security
source: tenant-a
destination: tenant-b
capability: shared-state-write-visible-to-other-tenant
expected: forbidden
authorization_reference: security-requirements/tenant-isolation-v1
```

## Observation

Record: run ID, invariant ID, environment fingerprint, exact source/destination identity, probe type, start/end timestamps, control results, transport results, destination-side receipt, canary digest, policy/config hashes, and evidence artifact digest.

## Verdicts

- VIOLATED: an independently forbidden capability was positively observed with destination-side evidence.
- SATISFIED_FOR_TESTED_CASE: controls passed and bounded tests did not observe a violation; **not** a universal safety guarantee.
- INCONCLUSIVE: health, control, attribution, or probe evidence insufficient.
- NOT_TESTED: capability class was not exercised.

The existing OBSERVED_* statuses remain transport observations, not authorization verdicts. A successful shared-state path with no independently forbidden invariant is OBSERVED_REACHABLE, **not automatically VIOLATED**.

## Proof obligations

A VIOLATED verdict requires: independent invariant, positive source operation, destination receipt with exact per-run canary match, and no synthetic bypass that invalidates the policy under test.

A SATISFIED_FOR_TESTED_CASE verdict requires: healthy destination before and after negative probe, passing safe controls, policy-agent readiness where relevant, bounded retries, and full probe audit trail. If any fails: INCONCLUSIVE.

## Safety and operations

Probe only controlled synthetic data and explicitly approved tenant targets. No customer secrets. Default read-only; synthetic writes require scoped authorization. Never conflate failure to observe with impossibility. Do not store the raw canary.
