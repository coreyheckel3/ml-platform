# Training Contracts

Training contracts define execution boundaries used by ForgeML workers and the
training control plane.

## External Package Runner

The external package runner lets ForgeML execute reviewed local ML packages
through named profiles. The first profile targets
`conversational-movie-recommender` by running its `movie-rec-build` CLI, storing
artifacts under `FORGEML_LOCAL_TRAINING_ARTIFACT_ROOT`, and importing top-k
ranking metrics into the training run.

Regenerate or verify the contract:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_external_training_package_contract.py --write
PYTHONPATH=backend/src:. python scripts/ci/check_external_training_package_contract.py
```
