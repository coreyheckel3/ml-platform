# Fraud Detection Example

This example exercises ForgeML through transaction dataset versioning, feature materialization, classifier training, approval, deployment, monitoring, drift detection, and retraining.

Run the local baseline trainer:

```bash
PYTHONPATH=. python -m ml.examples.fraud_detection.train
```

The trainer produces a versioned `model.json` artifact and an `evaluation.json` report under `artifacts/examples/fraud-detection`.
