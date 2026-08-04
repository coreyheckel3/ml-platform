# API Contracts

API contracts capture stable cross-client behavior that should remain explicit
even when route implementations evolve.

## Problem Details

`problem-details.v1.json` records the required ForgeML API error envelope, handled
exception classes, domain error code mappings, and sanitized internal-error detail.

Regenerate after an intentional API error response change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_problem_details_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_problem_details_contract.py
```
