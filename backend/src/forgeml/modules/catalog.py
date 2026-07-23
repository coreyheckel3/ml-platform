from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleDefinition:
    name: str
    owner: str
    description: str


MODULES: tuple[ModuleDefinition, ...] = (
    ModuleDefinition("auth", "Platform Security", "Identity, JWT authentication, RBAC."),
    ModuleDefinition("projects", "Platform Core", "Project lifecycle and membership."),
    ModuleDefinition("datasets", "Data Platform", "Dataset metadata, versions, schemas."),
    ModuleDefinition(
        "feature_store",
        "Feature Platform",
        "Feature definitions and materialization.",
    ),
    ModuleDefinition("training", "ML Runtime", "Training job lifecycle and orchestration."),
    ModuleDefinition("experiments", "ML Runtime", "Experiment runs, metrics, params, artifacts."),
    ModuleDefinition("model_registry", "ML Governance", "Model versions, approvals, lineage."),
    ModuleDefinition("deployments", "ML Operations", "Rollouts, canaries, rollback."),
    ModuleDefinition("inference", "ML Operations", "Online and batch prediction contracts."),
    ModuleDefinition("monitoring", "Observability", "Metrics and dashboard metadata."),
    ModuleDefinition("alerting", "Observability", "Alert rules, events, notification routing."),
    ModuleDefinition("drift_detection", "ML Quality", "Drift profiles, reports, triggers."),
    ModuleDefinition("retraining", "ML Automation", "Retraining policies and job triggers."),
    ModuleDefinition("administration", "Platform Administration", "Settings, audit, quotas."),
)


def module_names() -> set[str]:
    return {module.name for module in MODULES}
