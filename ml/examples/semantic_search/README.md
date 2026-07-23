# Semantic Search Example

This example exercises ForgeML through corpus ingestion, embedding feature generation, retrieval model evaluation, model registration, and deployment.

Run the local index builder:

```bash
PYTHONPATH=. python -m ml.examples.semantic_search.build_index
```

The index builder produces a versioned `model.json` artifact and an `evaluation.json` report under `artifacts/examples/semantic-search`.
