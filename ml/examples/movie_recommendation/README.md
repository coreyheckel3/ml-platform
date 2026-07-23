# Movie Recommendation Example

This example exercises ForgeML through dataset registration, feature pipelines, training, evaluation, model registration, and deployment.

Run the local baseline trainer:

```bash
PYTHONPATH=. python -m ml.examples.movie_recommendation.train
```

The trainer produces a versioned `model.json` artifact and an `evaluation.json` report under `artifacts/examples/movie-recommendation`.
