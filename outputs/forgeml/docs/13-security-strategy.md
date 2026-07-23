# Security Strategy

ForgeML should ship with secure defaults from the first implementation sprint. Security is part of platform architecture, not an afterthought.

## Security Principles

- Authenticate every non-public API.
- Authorize in application services, not only in route handlers.
- Use least privilege for users, service accounts, and cloud workloads.
- Store secrets outside source control.
- Validate all input at API boundaries.
- Treat uploaded datasets and model artifacts as untrusted content.
- Log security-relevant actions without logging secrets.
- Make dangerous production actions auditable and reversible where possible.

## Identity and Authentication

Initial authentication:

- Email and password login.
- Strong password hashing.
- Short-lived JWT access tokens.
- Refresh tokens stored as hashes.
- Refresh token revocation.
- Service accounts for automation.
- API keys stored only as hashes.

Future extension:

- SSO through an identity-provider adapter.
- SCIM provisioning.
- Organization-level identity policies.

## Authorization Model

RBAC should support organization and project scopes.

Recommended system roles:

| Role | Scope | Capabilities |
| --- | --- | --- |
| Organization Admin | Organization | Manage users, roles, settings, all projects |
| Project Admin | Project | Manage project settings and memberships |
| ML Engineer | Project | Manage datasets, features, experiments, training |
| Model Reviewer | Project | Approve or reject model versions |
| Operator | Project | Deploy, roll back, acknowledge alerts |
| Viewer | Project | Read-only access |

Permission checks should be named explicitly, such as:

- `datasets:create`
- `dataset_versions:finalize`
- `training_runs:create`
- `retraining_runs:create`
- `model_versions:approve`
- `deployments:rollback`
- `admin:audit_log:read`

## Input Validation

Validation layers:

| Layer | Responsibility |
| --- | --- |
| Pydantic API schemas | Shape, type, allowed values, size limits |
| Domain value objects | Business invariants |
| Application services | Authorization, state transitions, idempotency |
| Database constraints | Uniqueness, foreign keys, required fields |
| Dataset validators | Schema, nulls, ranges, categorical values, data quality |

## Uploaded Artifact Safety

Dataset and artifact handling should:

- Use signed upload URLs.
- Enforce file size limits.
- Compute content hashes.
- Store immutable object versions.
- Avoid executing uploaded code.
- Scan archives before extraction if archive support is added.
- Record uploader identity and source metadata.

## Rate Limiting

Implemented local rate limits protect API routes through a configurable fixed-window middleware.
The middleware returns rate-limit headers, emits Prometheus metrics, and exempts health,
metrics, and documentation routes by default. A Redis-backed adapter should replace the
process-local store before horizontally scaling the API.

Rate limits should protect:

- Login attempts
- API key creation
- Dataset upload finalization
- Training job creation
- Inference endpoints
- Admin APIs

Rate-limit decisions should emit metrics and structured security logs.

## Secure Response Headers

Implemented API responses include:

- `x-content-type-options: nosniff`
- `x-frame-options: DENY`
- `referrer-policy: no-referrer`
- `permissions-policy` denying camera, microphone, and geolocation
- `cross-origin-opener-policy: same-origin`
- HSTS outside local environments

## Secrets Management

Local development:

- `.env.example` documents required variables.
- Real secrets stay in untracked `.env` files.

Production:

- AWS Secrets Manager or SSM Parameter Store stores secret values.
- IAM roles control access to secrets.
- Kubernetes workloads receive only the secrets they need.
- Secret rotation runbooks exist before production release.

## Audit Logging

Audit events should be written for:

- Login success and failure
- API key creation and revocation
- Role changes
- Dataset version finalization
- Training job creation and cancellation
- Model approval and rejection
- Deployment rollout, promotion, and rollback
- Alert acknowledgement and resolution
- Admin configuration changes

Audit logs should include actor, action, resource, timestamp, trace ID, and safe metadata.

## Threat Model Focus Areas

Initial threat model should cover:

- Unauthorized project access
- Privilege escalation through role changes
- Malicious file upload
- Secrets leakage through logs
- Training job abuse for compute exhaustion
- Model artifact tampering
- Inference endpoint abuse
- Cross-tenant data exposure
- Supply-chain risk in Docker images and dependencies

The first committed threat model lives at `docs/security/threat-model.md`.
