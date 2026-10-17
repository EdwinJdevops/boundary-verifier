# Execution order and owner gates

1. Fix the existing EKS runner's assumption of a Pod literally named 'probe'; EKS Deployments generate names. Add deterministic selector-based pod resolution and unit tests.
2. Split provenance into generic execution metadata and implementation-specific fields; no kind/Calico labels in AWS evidence. Update schema and test fixtures together.
3. Add adversarial classifier tests (curl 0, 22, 28, 7; post-policy destination outage; DNS failure; CNI agent unhealthy). Timeout alone is INCONCLUSIVE absent sufficient corroboration.
4. Implement independent invariant declaration and authorization-verdict evaluation without modifying the raw observation statuses.
5. Add EXP-002 broken tenant authorization and EXP-003 safe tenant authorization, with exact canary assertions and a negative test that fails if the safe case is flagged.
6. Add EXP-004 measurement fault injection.
7. Benchmark against existing tooling with the same topology and evidence acceptance rules.
8. Complete AWS plan and full post-destroy inventory before EKS apply; no billable deployment without cost review.
9. Interview prospective buyers and record falsifiable purchase/pilot criteria.

No general-purpose control plane, multi-cloud abstraction, hosted dashboard, or auto-remediation until these gates justify them.
