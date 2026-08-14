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

## Release Evidence Workflow

`release-evidence-workflow.v1.json` records the CI workflow requirements for
building and uploading the release manifest after backend, frontend, Docker, and
production-readiness gates pass on `main`.

Regenerate after an intentional release-evidence workflow change:

```bash
PYTHONPATH=. python scripts/ci/check_release_evidence_workflow.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_release_evidence_workflow.py
```

## Release Evidence UX

`release-evidence-ux.v1.json` records the frontend evidence workspace
requirements: `/release-evidence` routing, navigation, release manifest
signals, reviewer commands, deterministic screenshot capture, screenshot
catalog coverage, and portfolio evidence mapping.

Regenerate after an intentional release evidence product-surface change:

```bash
PYTHONPATH=. python scripts/ci/check_release_evidence_ux_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_release_evidence_ux_contract.py
```

## Operational Audit UX

`operational-audit-ux.v1.json` records the frontend operator audit workspace
requirements: `/operational-audit` routing, navigation, admin audit API usage,
release evidence annotations, timeline signal families, deterministic
screenshot capture, screenshot catalog coverage, and portfolio evidence mapping.

Regenerate after an intentional operational audit product-surface change:

```bash
PYTHONPATH=. python scripts/ci/check_operational_audit_ux_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_operational_audit_ux_contract.py
```

## Release Manifest Verification

`release-manifest-verification.v1.json` records the required verifier behavior for
release manifests: manifest schema checks, source metadata checks, artifact hash
verification, Dockerfile hash verification, image digest shape checks, quality
gate coverage, CI evidence linkage, and release smoke evidence verification.

Regenerate after an intentional release manifest verifier change:

```bash
PYTHONPATH=. python scripts/ci/check_release_manifest_verifier_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_release_manifest_verifier_contract.py
```

Verify a release manifest:

```bash
PYTHONPATH=. python scripts/ops/verify_release_manifest.py --manifest /tmp/forgeml-release-manifest.json --require-ci-evidence
```

## Demo Readiness

`demo-readiness.v1.json` records the local demo contract: one-command stack
startup, seeded data refresh, deterministic screenshot capture, manual review
runbook coverage, and architecture walkthrough coverage.

Regenerate after an intentional demo-surface change:

```bash
PYTHONPATH=. python scripts/ci/check_demo_readiness_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_demo_readiness_contract.py
```

Run the local demo stack:

```bash
PYTHONPATH=. python scripts/dev/demo_stack.py
```

## CI Runtime

`ci-runtime.v1.json` records the required GitHub Actions runtime pins for the
main CI workflow and Terraform plan workflow. It prevents deprecated action
majors from quietly reappearing in release evidence.

Regenerate after an intentional workflow runtime change:

```bash
PYTHONPATH=. python scripts/ci/check_ci_runtime_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_ci_runtime_contract.py
```

## Portfolio Readiness

`portfolio-readiness.v1.json` records the reviewer-facing portfolio package:
reviewer guide, resume bullets, evidence map, architecture diagrams, screenshot
catalog, and its CI quality gate.

Regenerate after an intentional portfolio asset change:

```bash
PYTHONPATH=. python scripts/ci/check_portfolio_readiness_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=. python scripts/ci/check_portfolio_readiness_contract.py
```
