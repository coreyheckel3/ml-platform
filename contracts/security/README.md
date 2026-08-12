# Security Contracts

Security contracts capture platform invariants that should be reviewed and gated in CI.

## API Authorization

`api-authorization.v1.json` is generated from the FastAPI route table. It records every
public endpoint and every endpoint protected by the `get_current_principal` dependency.

Regenerate after an intentional API auth posture change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_api_authorization_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_api_authorization_contract.py
```

## Permission Catalog

`permission-catalog.v1.json` captures the canonical ForgeML permission vocabulary,
role presets, and the service-layer locations where permissions are enforced.

Regenerate after an intentional permission or role change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_permission_catalog.py --write
```

Verify the checked-in catalog:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_permission_catalog.py
```

## Runtime Config Policy

`runtime-config-policy.v1.json` captures production-like startup guardrails for
secrets, docs exposure, rate limiting, structured request logging, readiness checks,
CORS, and backing service endpoints.

Regenerate after an intentional production configuration policy change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_runtime_config_policy.py --write
```

Verify the checked-in policy:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_runtime_config_policy.py
```

## Security Hardening

`security-hardening.v1.json` captures the Sprint 57 security hardening contract:
organization isolation coverage, RBAC role matrix coverage, rate-limit partitioning,
audit metadata redaction, and secrets/runtime guardrail evidence.

Regenerate after an intentional security-hardening control change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_security_hardening_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_security_hardening_contract.py
```
