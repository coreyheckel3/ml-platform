# Incident Response Runbook

ForgeML incidents are triaged by user impact, platform availability, and ML quality risk.

## Severity Levels

| Severity | Criteria | Response |
| --- | --- | --- |
| SEV1 | Control plane unavailable, model serving unavailable, or data exposure suspected | Page platform owner immediately |
| SEV2 | Deployment, training, registry, or monitoring workflows degraded | Assign incident lead within 30 minutes |
| SEV3 | Non-urgent correctness issue, dashboard gap, or isolated workflow failure | Track in the engineering backlog |

## First 15 Minutes

1. Confirm whether `/health/ready` and `/metrics` are reachable.
2. Check Grafana panels for request rate, p95 latency, 5xx errors, and rate-limited requests.
3. Identify the affected project, deployment, model version, or dataset version.
4. Freeze risky rollout actions until the impact is understood.
5. Capture the request ID, deployment revision, and relevant alert event IDs.

## Mitigation Paths

- API saturation: increase replicas, lower client retry pressure, or tighten rate-limit exemptions.
- Inference failures: roll back to the previous healthy deployment revision.
- Drift incident: evaluate retraining policies and hold auto-deploy until approval review.
- Schema issue: disable affected dataset version and restore the last known-good backup if needed.
- Credential issue: rotate the affected secret and audit recent access.

## Closeout

Every SEV1 and SEV2 requires:

- Root cause summary
- User impact window
- Detection source
- Mitigation timeline
- Preventive action with an owner and due date
