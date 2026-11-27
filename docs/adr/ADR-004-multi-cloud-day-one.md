# ADR-004: Multi-Cloud from Day One

## Status
Accepted

## Context
Enterprise customers require:
- Cloud flexibility (avoid vendor lock-in)
- Data residency compliance (EU, US, APAC)
- Disaster recovery across providers
- Cost optimization via competitive pricing

Evaluated options:
1. **Cloud-agnostic from day one** - Terraform, Kubernetes, managed service abstractions
2. **Single cloud first, port later** - Faster initial delivery, high migration cost
3. **Cloud-specific optimizations** - Better performance, vendor lock-in

## Decision
Build **cloud-agnostic architecture from day one** using Terraform modules, Kubernetes, and abstracted managed services.

## Consequences

### Positive
- Deploy to AWS, Azure, GCP with same manifests
- Customer choice of cloud provider
- Data residency per tenant (EU tenants → EU region)
- Negotiation leverage with cloud providers
- Disaster recovery across providers

### Negative
- Cannot use cloud-specific optimizations by default (e.g., Bedrock, Vertex AI Search)
- More complex Terraform modules
- Must maintain parity across cloud providers
- Slightly higher initial development effort

## Implementation Notes
- Terraform modules in `infra/modules/` with cloud-agnostic inputs
- Kubernetes (EKS/AKS/GKE) for compute abstraction
- Managed services abstracted: PostgreSQL, Redis, Kafka, Object Storage
- Optional cloud-specific optimizations via feature flags (ADR-012)
- CI/CD pipelines identical across clouds

## Related
- ADR-003: PostgreSQL Primary Store (cloud-managed on all three)
- ADR-012: Optional Cloud-Specific Optimizations