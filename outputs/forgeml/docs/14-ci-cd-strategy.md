# CI/CD Strategy

ForgeML should use GitHub Actions for validation, image builds, infrastructure plans, and controlled deployments.

## CI Principles

- Every pull request runs the same quality gates.
- Build artifacts are immutable.
- Images are promoted by digest.
- Infrastructure plans are reviewed before apply.
- Production deployment requires manual approval.
- Secrets are accessed through GitHub OIDC and cloud IAM, not static long-lived credentials.

## Pull Request Workflow

Required checks:

| Check | Scope |
| --- | --- |
| Backend format | Python formatting |
| Backend lint | Python lint rules |
| Backend tests | Unit, integration, API |
| Frontend format | TypeScript and CSS formatting |
| Frontend lint | React and TypeScript lint rules |
| Frontend tests | Unit and component tests |
| Playwright smoke | Critical browser flow |
| Docker build | API, frontend, worker, Airflow, training, inference images |
| Terraform validate | Changed Terraform modules and environments |
| Security scan | Dependencies and container images |
| Production readiness | Runbook, observability, load-test, Compose, and staging Terraform checks |

## Main Branch Workflow

After merge:

1. Build versioned Docker images.
2. Push images to ECR.
3. Generate OpenAPI contract artifact.
4. Run database migration dry-run against staging clone where available.
5. Deploy to staging.
6. Run API smoke tests and k6 smoke load tests against staging.
7. Publish build summary and artifact digests.

## Production Deployment Workflow

Production deployment should require:

- Successful staging deployment.
- Passing smoke tests.
- Passing production-readiness checks.
- Reviewed Terraform plan when infrastructure changes are included.
- Manual approval.
- Rollback instructions attached to the deployment record.

## Database Migrations

Migration policy:

- Migrations run before application rollout only when backward compatible.
- Breaking schema changes use expand-and-contract.
- Long-running backfills run as separate jobs.
- Production migration failure triggers rollback runbook.

## Docker Build Workflow

Each image build should:

- Use dependency lock files.
- Cache dependencies safely.
- Add image labels.
- Generate a software bill of materials where tooling is available.
- Run vulnerability scans.
- Push only on trusted branches.

## Release Artifacts

Each release should publish:

- Git SHA
- Image digests
- OpenAPI schema
- Alembic migration revision
- Terraform plan artifact when applicable
- Test summary
- Deployment environment

## Branch and Environment Policy

| Branch/Event | Action |
| --- | --- |
| Pull request | Validate only |
| Merge to main | Build and deploy staging |
| Tag or approved manual dispatch | Deploy production |
| Infrastructure PR | Terraform plan |
| Approved infrastructure workflow | Terraform apply |
