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
| [interview-mode.md](interview-mode.md) | Productized reviewer walkthrough for `/portfolio`, architecture explanations, validation commands, and interview prompts. |
| [evidence-map.md](evidence-map.md) | Traceability from portfolio claims to implementation files, tests, CI gates, and docs. |
| [architecture-diagrams.md](architecture-diagrams.md) | Mermaid diagrams for system shape, training lifecycle, deployment lifecycle, and release governance. |
| [screenshot-catalog.md](screenshot-catalog.md) | Screenshot inventory produced by the deterministic Playwright demo capture flow. |

## Recommended Review Path

1. Read the one-page project framing in [reviewer-guide.md](reviewer-guide.md).
2. Open `/portfolio` or read [interview-mode.md](interview-mode.md) for the
   productized interview walkthrough.
3. Skim [architecture-diagrams.md](architecture-diagrams.md) to understand the
   modular monolith, adapter boundaries, and release governance loop.
4. Use [evidence-map.md](evidence-map.md) to jump from a claim to the code and
   tests that support it.
5. Run `make demo-stack`, open `/release-evidence` and `/operational-audit`,
   or run `make demo-screenshots` for deterministic browser evidence.
6. Use [resume-bullets.md](resume-bullets.md) to adapt the project for ML,
   MLOps, AI platform, or backend/platform engineering applications.
