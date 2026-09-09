# Platform Admin Controls Runbook

The Admin Controls page is the organization-level operations surface for ForgeML
administrators. It answers four questions before an operator changes or
promotes anything:

- Which organization is the current principal scoped to?
- Which users and role presets are visible for the tenant?
- Which runtime controls are enabled for this environment?
- Which safeguards and verification commands should be checked before admin
  workflows become mutable?

## Access

The browser route is `/admin` and the backend route is:

```bash
GET /api/v1/admin/controls
```

The route requires the `admin:controls:read` permission. The response schema is
`forgeml.platform_admin_controls.v1` and is intentionally read-only in this
sprint. Role changes should go through a dedicated audited mutation workflow in
a later sprint.

## Local Verification

Run the focused contract:

```bash
make admin-controls
```

The target executes:

```bash
PYTHONPATH=. python scripts/ci/check_platform_admin_controls_contract.py
```

Run the broader release gate before merging:

```bash
make production-readiness
```

## Operator Review

1. Open `http://127.0.0.1:5173/admin`.
2. Confirm Organization Overview shows the expected organization ID, slug,
   project count, audit event count, and release report count.
3. Confirm User Access lists only users from the signed-in principal's
   organization.
4. Confirm RBAC Matrix and Permission Catalog include `admin:controls:read` and
   mark whether permissions are granted to the current principal.
5. Confirm Environment Visibility reports production-like posture, rate
   limiting, request logging, structured logging, readiness checks, object
   storage, Redis, MLflow, Airflow, and external training profile wiring.
6. Confirm Safe Admin Workflows lists Tenant isolation, RBAC mutations, Release
   governance, and Runtime guardrails with evidence paths.

## Production Notes

- Keep docs disabled in production-like environments unless an explicit
  internal access control layer is present.
- Keep rate limiting, request logging, structured logging, and readiness checks
  enabled before exposing admin routes outside local development.
- Treat RBAC mutation endpoints as a separate release because they require
  audit events, permission checks, conflict handling, and rollback semantics.
- Use Release Evidence and Operational Audit together when reviewing admin
  control-plane changes.
