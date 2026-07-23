# Terraform Strategy

Terraform should manage all AWS infrastructure needed for ForgeML staging and production. Infrastructure should be modular, environment-aware, and reviewable through CI.

## Directory Layout

```text
infra/terraform/
  environments/
    dev/
      main.tf
      variables.tf
      outputs.tf
      backend.tf
      terraform.tfvars.example
    staging/
    prod/
  modules/
    network/
    eks/
    rds/
    redis/
    s3/
    ecr/
    iam/
    observability/
    secrets/
    ci_oidc/
```

## Module Responsibilities

| Module | Responsibility |
| --- | --- |
| `network` | VPC, subnets, route tables, NAT, security group foundations |
| `eks` | Cluster, node groups, service account IAM integration |
| `rds` | PostgreSQL instance, subnet groups, backups, parameter groups |
| `redis` | ElastiCache Redis subnet group, replication group, security |
| `s3` | Artifact, dataset, reports, logs buckets and lifecycle rules |
| `ecr` | Container repositories and lifecycle policies |
| `iam` | Workload roles and least-privilege policies |
| `observability` | Prometheus/Grafana infrastructure hooks |
| `secrets` | Secret names, rotation metadata, KMS configuration |
| `ci_oidc` | GitHub Actions OIDC provider and deploy roles |

## State Management

Recommendation:

- Use one remote state backend per environment.
- Store Terraform state in S3.
- Use DynamoDB or equivalent state locking where supported.
- Restrict production state access to deployment roles and platform administrators.

## Environment Strategy

| Environment | Purpose | Apply Policy |
| --- | --- | --- |
| `dev` | Shared development infrastructure | Manual or protected branch |
| `staging` | Production-like validation | Automatic after merge with reviewable plan |
| `prod` | User-facing production | Manual approval required |

## CI/CD Integration

Pull requests:

- `terraform fmt -check`
- `terraform validate`
- Terraform plan for affected environments
- Static security scan

Main branch:

- Apply to staging after successful tests
- Require approval for production apply

## Secrets and Sensitive Values

Terraform should create secret containers and IAM permissions, but should not store secret values in version control.

Allowed in Terraform:

- Secret names
- KMS keys
- IAM policies
- Rotation metadata

Not allowed in Terraform variables committed to source:

- Database passwords
- JWT private keys
- API tokens
- Notification provider secrets

## Naming and Tagging

All resources should include:

- `Project = ForgeML`
- `Environment`
- `ManagedBy = Terraform`
- `Owner`
- `CostCenter` where applicable

Resource names should include environment prefixes, for example `forgeml-staging-rds`.

## Safety Rules

- Production destructive changes require a documented migration plan.
- RDS deletion protection is enabled in production.
- S3 critical buckets enable versioning.
- Terraform plans are stored as CI artifacts.
- IAM policies start least-privilege and expand only when needed.

