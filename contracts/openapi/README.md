# OpenAPI Contracts

The backend generates the authoritative OpenAPI schema from FastAPI. The checked-in
contract is used by CI, SDK work, frontend integration planning, and release reviews.

Regenerate the contract after intentional API changes:

```bash
PYTHONPATH=backend/src:. python scripts/ci/generate_openapi_contract.py
```

Verify that the checked-in contract is current:

```bash
PYTHONPATH=backend/src:. python scripts/ci/generate_openapi_contract.py --check
```
