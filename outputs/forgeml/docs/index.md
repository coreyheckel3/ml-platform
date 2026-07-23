# ForgeML Architecture Documentation

Status: proposed architecture baseline
Date: 2026-07-18

ForgeML is an end-to-end machine learning platform for teams that need to ingest datasets, build feature pipelines, train models, evaluate experiments, register and deploy models, monitor production behavior, detect drift, and trigger retraining. This documentation package defines the architecture before implementation begins.

No implementation code has been generated. These documents are the implementation gate for the project.

## Document Map

1. [Repository Structure](./00-repository-structure.md)
2. [System Architecture](./01-system-architecture.md)
3. [Database Schema](./02-database-schema.md)
4. [API Specification](./03-api-specification.md)
5. [Implementation Roadmap](./04-implementation-roadmap.md)
6. [Sprint Breakdown](./05-sprint-breakdown.md)
7. [Architecture Decision Records](./06-architecture-decision-records.md)
8. [Sequence Diagrams](./07-sequence-diagrams.md)
9. [Deployment Architecture](./08-deployment-architecture.md)
10. [Docker Strategy](./09-docker-strategy.md)
11. [Terraform Strategy](./10-terraform-strategy.md)
12. [Testing Strategy](./11-testing-strategy.md)
13. [Monitoring Strategy](./12-monitoring-strategy.md)

Additional platform requirements:

- [Security Strategy](./13-security-strategy.md)
- [CI/CD Strategy](./14-ci-cd-strategy.md)
- [Dashboard and Product Surface](./15-dashboard-product-surface.md)

## Core Recommendation

Build ForgeML as a modular monolith first. The platform should have one backend deployable for the API/control plane, a separate worker process for asynchronous application work, Airflow for long-running ML orchestration, MLflow for experiment and model artifact interoperability, and strict internal module boundaries so high-scale modules can later be extracted into services.

This architecture optimizes for correctness and maintainability early while preserving extraction paths for training, inference, monitoring, and feature store workloads.

## Major Decision Checkpoints

These are major decisions that should be confirmed before implementation:

| Decision | Recommendation | Why It Matters |
| --- | --- | --- |
| Backend architecture | Modular monolith with ports/adapters | Keeps delivery fast while preserving service extraction paths. |
| Production runtime | AWS EKS | Better fit than ECS for Airflow, inference workloads, autoscaling, and future GPU jobs. |
| Orchestration | Airflow for ML workflows | Mature scheduling, retries, lineage hooks, backfills, and operational visibility. |
| Experiment tracking | MLflow behind ForgeML interfaces | Avoids rebuilding commodity experiment storage while preventing hard dependency leakage. |
| Artifact storage | S3-compatible object storage | Required for large datasets, models, reports, and immutable versions. |
| Local development | Docker Compose | Gives engineers one-command local infrastructure without cloud dependency. |
| Auth model | JWT plus RBAC | Fits web APIs, CI automation, and future service accounts. |

Implementation should begin only after these choices are accepted or revised.
