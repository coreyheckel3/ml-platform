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

Sprint 57 adds a checked RBAC matrix for the role presets in
`forgeml.platform.security.permissions`. The matrix verifies platform admin,
ML engineer, ML operator, ML viewer, and security auditor behavior against
high-risk permissions so role changes are reviewed as code.

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

Sprint 57 adds route and client partitioning coverage for the fixed-window
rate limiter. This proves one client exhausting a specific endpoint does not
block other endpoints or another caller under the same local API process.

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
- Refresh-token rotation and logout
- Project creation
- API key creation and revocation
- Role changes
- Dataset version finalization
- Training job creation and cancellation
- Model approval and rejection
- Deployment rollout, promotion, and rollback
- Alert acknowledgement and resolution
- Admin configuration changes

Audit logs should include actor, action, resource, timestamp, trace ID, and safe metadata.

Implemented audit writers currently cover successful login, refresh-token rotation, logout, project creation, training queue and cancellation, model approval workflows, deployment rollout and rollback workflows, alert lifecycle transitions, and retraining decisions. Event metadata intentionally excludes credentials, access tokens, refresh tokens, bearer token claims that are not needed for operator review, free-form approval comments, and raw operator notes.

Common audit writers sanitize metadata before persistence. Keys containing
credential, token, password, authorization, secret, JWT, refresh-token, or API-key
markers are replaced with a redacted value recursively, while operational IDs
and lineage metadata are preserved for investigation.

## Multi-Tenant Isolation

Repository and service boundaries must scope reads and writes by organization.
Cross-tenant IDs should produce not-found or permission-denied outcomes rather
than leaking resource existence across organizations.

Sprint 57 adds integration coverage for project, dataset, training-run, and
audit-log repository isolation using two organizations in one database. The
security hardening contract keeps these isolation tests, RBAC matrix tests,
rate-limit tests, audit redaction tests, and secrets/runtime guardrail docs
release-gated under `contracts/security/security-hardening.v1.json`.

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
