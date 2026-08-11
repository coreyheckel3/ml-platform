# ForgeML Orchestration Contracts

This directory contains checked-in contracts for workflow orchestration adapters.

`airflow-training.v1.json` defines the Airflow training DAG adapter boundary,
the stable REST operations ForgeML calls, the versioned training DAG run
configuration, state mapping, polling API surface, local fallback behavior, and
CI gates.
