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
