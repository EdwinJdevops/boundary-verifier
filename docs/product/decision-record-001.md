# ADR-001 — Boundary Verifier product reset

Status: proposed for review. Research implementation, not a product launch.

## Product claim

Boundary Verifier evaluates **declared workload isolation invariants** against bounded, observed capabilities. It reports contradictions with replayable evidence and explicit uncertainty. It does not claim to prove the absence of all communication paths, or to replace runtime enforcement.

## Customer and deployment hypothesis

Initial buyer hypothesis: security/platform engineering teams operating multi-tenant Kubernetes services with shared infrastructure and explicit isolation requirements. Unvalidated until customer interviews. No pricing or revenue claims.

Initial deployment: customer-owned, ephemeral verifier job with read-only discovery and separately authorized synthetic probes. No permanent control plane, SaaS ingestion, or broad cluster-admin permissions in v1. Evidence export is local and sanitized.

## Adversarial objections

1. A shared service permitting both tenants is not itself a vulnerability. Require an independent invariant and an expected-allowed control.
2. NetworkPolicy governs L3/L4 connectivity, not tenant authorization or information flow. Never attribute shared-state exposure to a CNI defect.
3. A timeout is not proof of enforcement. Require destination health, agent health, repeat observations, and explicit UNKNOWN on ambiguity.
4. Existing products and integration tests may solve the problem. Compare with a representative existing tool before platform expansion.
5. Synthetic fixtures prove harness correctness, not commercial value. Require a realistic customer-derived use case.

## Falsification gates

- G0: fixture validity: fail closed on broken positive controls, no raw canary retained, deterministic per-run evidence.
- G1: negative and safe controls: deliberately broken tenant authorization produces a contradiction; correctly enforced tenant authorization does not.
- G2: measurement fault injection: endpoint crash, probe failure, agent unready, and DNS failure never report a policy-enforced block.
- G3: comparator: documented side-by-side reproduction with existing network/security testing tools, including setup effort and evidence quality.
- G4: demand: interviews with at least five relevant practitioners; document specific incidents, current workaround, procurement owner and willingness to pilot. No fabricated testimonials.
- G5: independent cloud reproduction only after executable Terraform plan, cost ceiling, provenance, and complete teardown inventory pass.

## Stop conditions

Stop or pivot if G1 cannot distinguish authorized from forbidden information flow, if comparator gives no meaningful advantage, or if buyers cannot identify a high-value recurring workflow.

## Explicit non-goals

No agent framework, LLM verdict engine, auto-remediation, graph database, hosted SaaS, universal policy proof, or production write access during this phase.
