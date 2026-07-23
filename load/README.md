# ForgeML Load Tests

ForgeML load tests are written for k6 and target stable control-plane endpoints. They are intentionally lightweight enough to run in staging before deployments and expressive enough to enforce latency and error-budget gates.

Run the smoke load test against a local or staging API:

```bash
k6 run -e FORGEML_BASE_URL=http://127.0.0.1:8000 load/k6/api_smoke.js
```

The smoke profile checks:

- readiness latency
- metrics endpoint availability
- auth validation behavior for unauthenticated requests
- rate-limit stability under a small request burst

Use the output trend metrics as deployment evidence in release reviews.
