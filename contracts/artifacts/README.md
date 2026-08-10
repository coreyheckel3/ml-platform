# Artifact Contracts

ForgeML stores datasets, model packages, reports, and training outputs outside the
relational database. These contracts define the manifest shape and storage adapter
requirements that keep those artifacts auditable from the control plane.

- `artifact-manifest.v1.json` defines the required manifest fields, checksum policy,
  storage gateway boundary, dataset producer, and model registry producer.
