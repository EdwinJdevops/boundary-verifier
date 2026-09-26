# EXP-001 — EKS + Amazon VPC CNI independent reproduction

Status: design gate only. This document authorizes no AWS resource creation.

## Objective

Re-run the existing EXP-001 semantics on an independent Kubernetes NetworkPolicy implementation: Amazon EKS on EC2 Linux nodes with Amazon VPC CNI NetworkPolicy enforcement.

This is a reproduction, not a new experiment. The acceptance condition remains:

- tenant-a -> tenant-b: OBSERVED_BLOCKED
- tenant-b -> tenant-a: OBSERVED_BLOCKED
- tenant-a -> shared canary -> tenant-b: OBSERVED_REACHABLE
- exact per-run canary equality is required

No result may be promoted to OBSERVED_BLOCKED merely because a command failed. The same evidence-v2 classification contract applies.

## Isolation from the kind/Calico run

The EKS run must not reuse Calico. It uses the Amazon VPC CNI NetworkPolicy implementation so a passing result is evidence across two independent enforcement implementations.

Use EC2 Linux worker nodes. Do not use Fargate or Windows for this experiment.

## Version and configuration gates

Before resource creation, resolve and record:

1. EKS Kubernetes version.
2. Managed Amazon VPC CNI add-on version compatible with that EKS version.
3. EC2 node AMI/release and instance type.
4. VPC CNI NetworkPolicy support enabled.
5. Enforcement mode used by the run.
6. IPv4/IPv6 family.
7. AWS region and account ID.
8. IaC revision SHA.

The first reproduction should use IPv4.

NetworkPolicy must be enabled explicitly on the VPC CNI add-on. The run must verify the network-policy agent is healthy before applying experiment workloads.

## Cost boundary

The experiment is ephemeral. Do not create NAT gateways, load balancers, RDS, EFS, public application endpoints, or other unrelated managed resources.

Prefer a minimal dedicated VPC and the smallest EC2 capacity that can run the three experiment namespaces reliably. Resource count and estimated hourly cost must be reviewed before apply.

All experiment resources require:

- Project=boundary-verifier
- Experiment=EXP-001
- Environment=ephemeral
- ManagedBy=terraform

Terraform state must not contain application secrets.

## Lifecycle

The AWS execution path is:

plan -> cost/resource review -> apply -> infrastructure readiness -> positive controls -> policy application -> EXP-001 -> evidence validation -> artifact retention -> destroy -> post-destroy verification.

A failed experiment still proceeds to evidence/log collection and teardown.

No run is complete until post-destroy verification confirms experiment-owned billable resources are gone.

## Network design

Use a dedicated VPC with subnets sufficient for EKS control-plane ENIs and EC2 worker nodes. Avoid NAT gateway dependency. If the selected implementation requires outbound package/image access, solve that explicitly before apply rather than silently adding a NAT gateway.

No internet-facing Service or LoadBalancer is needed. The probes communicate only through Kubernetes ClusterIP Services.

Security groups are infrastructure controls, not EXP-001 evidence. They must not independently block the tenant-to-tenant paths being tested; otherwise NetworkPolicy attribution is confounded.

## Workload design

Reuse the logical EXP-001 fixtures:

- tenant-a
- tenant-b
- shared-services
- tenant peer endpoints
- tenant probes
- canary-store
- default-deny policies
- narrow shared-canary allowances

EKS-specific manifests may change scheduling/runtime details but must not change the logical boundary or acceptance condition.

All selected probe workloads must be controller-owned where practical because Amazon EKS documents stronger NetworkPolicy enforcement behavior for Pods with ownerReferences. The existing standalone probe Pods therefore require an EKS-specific controller-owned form before execution.

Service port and container port must remain aligned.

## Measurement sequence

1. Verify cluster, nodes, VPC CNI and network-policy agent health.
2. Deploy workloads with NetworkPolicies absent.
3. Prove A -> B, B -> A, A -> shared, and B -> shared liveness.
4. Record positive-control evidence.
5. Apply the four policy manifests.
6. Wait for policy endpoints/enforcement to converge using implementation-observable readiness, not a blind sleep.
7. Execute the existing evidence-v2 runner.
8. Validate schema and cross-record invariants.
9. Record implementation provenance.
10. Destroy infrastructure and verify deletion.

If a positive control fails, EXP-001 is NOT_EVALUATED/fixture failure; it is not a policy result.

## Evidence additions for the EKS run

Keep evidence_version=2 unless the schema must change. Add implementation provenance only through an intentional schema revision.

Required environment provenance for the reproduction:

- AWS account ID
- region
- EKS cluster ARN/name
- Kubernetes version
- VPC CNI add-on version
- node AMI/release
- node instance type
- NetworkPolicy configuration/enforcement mode
- git SHA
- Terraform plan/apply identity
- SHA-256 hashes of policy manifests

Do not persist credentials, tokens, kubeconfig bearer material, private keys, or the raw canary.

## Failure attribution

Transport failures that are not the accepted post-liveness blocking signature remain UNKNOWN.

AWS infrastructure failures, image-pull failures, scheduling failures, CNI-agent failures, DNS failures, Kubernetes API failures, and teardown failures are separate failure classes. They must not be collapsed into NetworkPolicy blocking.

## Terraform boundary

Terraform may create only experiment infrastructure. Kubernetes experiment fixtures remain applied by the experiment harness unless a later design change proves Terraform ownership is necessary.

Terraform modules should expose explicit outputs required by the runner and teardown verifier. Avoid a general-purpose EKS platform module for this experiment.

## Pre-apply blockers

AWS apply is prohibited until all are true:

- exact EKS/VPC CNI versions resolved
- region selected
- resource inventory reviewed
- cost-sensitive resources enumerated
- no NAT gateway or LoadBalancer in plan unless explicitly justified
- controller-owned EKS probe fixture implemented
- evidence schema decision made for AWS provenance
- teardown verifier implemented
- Terraform plan reviewed for destructive effects outside experiment scope

## Definition of done

EXP-001/EKS is complete only when:

1. positive controls passed before policy enforcement;
2. both direct paths are OBSERVED_BLOCKED under the accepted classifier;
3. the shared-state path is OBSERVED_REACHABLE with exact canary equality;
4. evidence validates against its declared schema;
5. provenance identifies the AWS enforcement implementation precisely;
6. the artifact is retained with a digest;
7. Terraform destroy succeeds; and
8. an independent AWS inventory confirms no experiment-owned billable resources remain.

A single successful EKS run demonstrates reproduction under the pinned EKS/VPC CNI environment. It does not establish universal NetworkPolicy behavior.
