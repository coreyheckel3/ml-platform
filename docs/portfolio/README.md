# ForgeML Portfolio Review Kit

This folder packages ForgeML for engineering portfolio review, interview
walkthroughs, and recruiter-facing project summaries. The assets are intentionally
source controlled and CI-checked so claims about the platform point back to
verifiable code, contracts, tests, and release evidence.

## Assets

| Asset | Purpose |
| --- | --- |
| [reviewer-guide.md](reviewer-guide.md) | Guided path for a technical reviewer to understand scope, architecture, and proof points. |
| [resume-bullets.md](resume-bullets.md) | Role-specific bullets for ML Engineer, MLOps Engineer, AI Platform Engineer, and Software Engineer applications. |
| [evidence-map.md](evidence-map.md) | Traceability from portfolio claims to implementation files, tests, CI gates, and docs. |
| [architecture-diagrams.md](architecture-diagrams.md) | Mermaid diagrams for system shape, training lifecycle, deployment lifecycle, and release governance. |
| [screenshot-catalog.md](screenshot-catalog.md) | Screenshot inventory produced by the deterministic Playwright demo capture flow. |

## Recommended Review Path

1. Read the one-page project framing in [reviewer-guide.md](reviewer-guide.md).
2. Skim [architecture-diagrams.md](architecture-diagrams.md) to understand the
   modular monolith, adapter boundaries, and release governance loop.
3. Use [evidence-map.md](evidence-map.md) to jump from a claim to the code and
   tests that support it.
4. Run `make demo-stack`, open `/release-evidence`, or run
   `make demo-screenshots` for deterministic browser evidence.
5. Use [resume-bullets.md](resume-bullets.md) to adapt the project for ML,
   MLOps, AI platform, or backend/platform engineering applications.
