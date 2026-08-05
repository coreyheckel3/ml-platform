# Operations Contracts

Operations contracts capture release and operator checks that should stay stable
across local, staging, and production validation.

## Release Smoke

`release-smoke.v1.json` records the non-mutating API stages that a release
candidate smoke run must execute against a live ForgeML API.

Regenerate after an intentional smoke-surface change:

```bash
PYTHONPATH=. python scripts/ci/check_release_smoke_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_release_smoke_contract.py
```

Run the live smoke check against a seeded local API:

```bash
PYTHONPATH=. python scripts/ops/release_smoke.py --base-url http://127.0.0.1:8001
```

## Release Manifest

`release-manifest.v1.json` records the required structure for release provenance
manifests: source revision, required contract hashes, Docker image targets,
quality gates, and release evidence.

Regenerate after an intentional manifest-surface change:

```bash
PYTHONPATH=. python scripts/ci/check_release_manifest_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_release_manifest_contract.py
```

Build a release manifest:

```bash
PYTHONPATH=. python scripts/ops/build_release_manifest.py --output /tmp/forgeml-release-manifest.json
```
