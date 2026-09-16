# AGENTS.md

## Mission

Build EXP-001 as a falsification-grade isolation experiment. Do not expand into a product platform until the experiment and incumbent comparison justify it.

## Engineering constraints

1. Preserve the distinction between declared policy, observed evidence, and inferred graph edges.
2. Never convert a failed probe into a universal security claim.
3. Every positive path finding must be reproducible with a unique run ID and synthetic canary.
4. Keep the initial lab local and deterministic.
5. Do not add LLM inference to the verifier. The core result must be deterministic.
6. Do not implement CER concepts here: consequential-action authorization, execution state machines, recovery contracts, mutation envelopes, or non-expanding delegation.
7. Avoid UI, databases, cloud resources, eBPF, and managed services until EXP-001 requires them.
8. Tests and experiment documentation change with behavior.

## First implementation order

1. Kubernetes fixtures and network policy.
2. Controlled shared canary service.
3. Probe runner.
4. Evidence schema.
5. Effective-path reconstruction.
6. Automated assertions for ground truth.
7. Baseline-tool comparison.
