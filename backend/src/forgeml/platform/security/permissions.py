from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    module: str
    action: str
    description: str


@dataclass(frozen=True)
class RolePreset:
    code: str
    name: str
    description: str
    permissions: frozenset[str]


PERMISSIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        "admin:audit_log:read",
        "administration",
        "read",
        "Read organization audit log events.",
    ),
    PermissionDefinition("projects:create", "projects", "create", "Create projects."),
    PermissionDefinition("projects:read", "projects", "read", "Read project metadata."),
    PermissionDefinition("datasets:create", "datasets", "create", "Create datasets."),
    PermissionDefinition("datasets:read", "datasets", "read", "Read datasets and versions."),
    PermissionDefinition(
        "dataset_versions:create",
        "datasets",
        "create",
        "Create immutable dataset version upload records.",
    ),
    PermissionDefinition(
        "dataset_versions:finalize",
        "datasets",
        "write",
        "Finalize dataset versions after object upload.",
    ),
    PermissionDefinition(
        "dataset_versions:validate",
        "datasets",
        "write",
        "Run schema validation for dataset versions.",
    ),
    PermissionDefinition(
        "feature_sets:create",
        "feature_store",
        "create",
        "Create feature sets.",
    ),
    PermissionDefinition(
        "feature_sets:read",
        "feature_store",
        "read",
        "Read feature sets, features, materializations, and lineage.",
    ),
    PermissionDefinition(
        "feature_definitions:write",
        "feature_store",
        "write",
        "Register feature definitions.",
    ),
    PermissionDefinition(
        "feature_pipelines:write",
        "feature_store",
        "write",
        "Register feature pipelines.",
    ),
    PermissionDefinition(
        "feature_materializations:create",
        "feature_store",
        "create",
        "Trigger feature materialization jobs.",
    ),
    PermissionDefinition(
        "experiments:create",
        "experiments",
        "create",
        "Create experiment containers.",
    ),
    PermissionDefinition(
        "experiments:read",
        "experiments",
        "read",
        "Read experiment metadata.",
    ),
    PermissionDefinition(
        "experiment_runs:create",
        "experiments",
        "create",
        "Create experiment runs.",
    ),
    PermissionDefinition(
        "experiment_runs:read",
        "experiments",
        "read",
        "Read experiment run metadata, metrics, parameters, and reports.",
    ),
    PermissionDefinition(
        "experiment_runs:write",
        "experiments",
        "write",
        "Write experiment run metrics and status updates.",
    ),
    PermissionDefinition(
        "experiment_artifacts:write",
        "experiments",
        "write",
        "Attach experiment artifacts.",
    ),
    PermissionDefinition(
        "training_runs:create",
        "training",
        "create",
        "Queue training runs.",
    ),
    PermissionDefinition(
        "training_runs:read",
        "training",
        "read",
        "Read training runs, events, and logs.",
    ),
    PermissionDefinition(
        "training_runs:write",
        "training",
        "write",
        "Record training results and execute training runs.",
    ),
    PermissionDefinition(
        "training_runs:cancel",
        "training",
        "write",
        "Cancel queued or running training runs.",
    ),
    PermissionDefinition("models:create", "model_registry", "create", "Create registered models."),
    PermissionDefinition("models:read", "model_registry", "read", "Read model registry records."),
    PermissionDefinition(
        "model_versions:create",
        "model_registry",
        "create",
        "Register model versions and promote training artifacts.",
    ),
    PermissionDefinition(
        "model_versions:request_approval",
        "model_registry",
        "write",
        "Request model-version approval.",
    ),
    PermissionDefinition(
        "model_versions:review",
        "model_registry",
        "approve",
        "Approve or reject model versions.",
    ),
    PermissionDefinition("deployments:create", "deployments", "create", "Create deployments."),
    PermissionDefinition("deployments:read", "deployments", "read", "Read deployments."),
    PermissionDefinition(
        "deployments:rollback",
        "deployments",
        "write",
        "Roll back deployments to a prior healthy revision.",
    ),
    PermissionDefinition(
        "deployment_revisions:create",
        "deployments",
        "create",
        "Create deployment revisions.",
    ),
    PermissionDefinition(
        "deployment_revisions:traffic",
        "deployments",
        "write",
        "Update deployment revision traffic allocations.",
    ),
    PermissionDefinition(
        "deployment_health:write",
        "deployments",
        "write",
        "Record deployment revision health checks.",
    ),
    PermissionDefinition(
        "inference_endpoints:create",
        "inference",
        "create",
        "Create inference endpoints.",
    ),
    PermissionDefinition(
        "inference_endpoints:read",
        "inference",
        "read",
        "Read inference endpoints and prediction request logs.",
    ),
    PermissionDefinition(
        "inference:predict",
        "inference",
        "execute",
        "Invoke online prediction endpoints.",
    ),
    PermissionDefinition(
        "inference_metrics:write",
        "inference",
        "write",
        "Record inference metric snapshots.",
    ),
    PermissionDefinition(
        "monitoring:read",
        "monitoring",
        "read",
        "Read monitoring summaries and endpoint dashboards.",
    ),
    PermissionDefinition(
        "alert_rules:create",
        "alerting",
        "create",
        "Create alert rules.",
    ),
    PermissionDefinition(
        "alert_rules:read",
        "alerting",
        "read",
        "Read alert rules.",
    ),
    PermissionDefinition(
        "alert_rules:evaluate",
        "alerting",
        "execute",
        "Evaluate alert rules against observed metrics.",
    ),
    PermissionDefinition(
        "alert_events:read",
        "alerting",
        "read",
        "Read alert events.",
    ),
    PermissionDefinition(
        "alert_events:acknowledge",
        "alerting",
        "write",
        "Acknowledge alert events.",
    ),
    PermissionDefinition(
        "alert_events:resolve",
        "alerting",
        "write",
        "Resolve alert events.",
    ),
    PermissionDefinition(
        "drift_profiles:create",
        "drift_detection",
        "create",
        "Create drift profiles.",
    ),
    PermissionDefinition(
        "drift_profiles:read",
        "drift_detection",
        "read",
        "Read drift profiles.",
    ),
    PermissionDefinition(
        "drift_reports:create",
        "drift_detection",
        "create",
        "Run drift reports.",
    ),
    PermissionDefinition(
        "drift_reports:read",
        "drift_detection",
        "read",
        "Read drift reports and feature-level drift results.",
    ),
    PermissionDefinition(
        "retraining_policies:create",
        "retraining",
        "create",
        "Create retraining policies.",
    ),
    PermissionDefinition(
        "retraining_policies:read",
        "retraining",
        "read",
        "Read retraining policies.",
    ),
    PermissionDefinition(
        "retraining_runs:create",
        "retraining",
        "create",
        "Evaluate or trigger retraining runs.",
    ),
    PermissionDefinition(
        "retraining_runs:read",
        "retraining",
        "read",
        "Read retraining runs.",
    ),
    PermissionDefinition(
        "retraining_runs:approve",
        "retraining",
        "approve",
        "Approve pending retraining runs.",
    ),
    PermissionDefinition(
        "retraining_runs:reject",
        "retraining",
        "approve",
        "Reject pending retraining runs.",
    ),
)


ROLE_PRESETS: tuple[RolePreset, ...] = (
    RolePreset(
        code="platform_admin",
        name="Platform Admin",
        description="Full ForgeML platform administration across all modules.",
        permissions=frozenset({"*"}),
    ),
    RolePreset(
        code="ml_engineer",
        name="ML Engineer",
        description="Build datasets, features, experiments, training runs, and models.",
        permissions=frozenset(
            {
                "projects:create",
                "projects:read",
                "datasets:create",
                "datasets:read",
                "dataset_versions:create",
                "dataset_versions:finalize",
                "dataset_versions:validate",
                "feature_sets:create",
                "feature_sets:read",
                "feature_definitions:write",
                "feature_pipelines:write",
                "feature_materializations:create",
                "experiments:create",
                "experiments:read",
                "experiment_runs:create",
                "experiment_runs:read",
                "experiment_runs:write",
                "experiment_artifacts:write",
                "training_runs:create",
                "training_runs:read",
                "training_runs:write",
                "training_runs:cancel",
                "models:create",
                "models:read",
                "model_versions:create",
                "model_versions:request_approval",
                "drift_profiles:create",
                "drift_profiles:read",
                "drift_reports:create",
                "drift_reports:read",
            }
        ),
    ),
    RolePreset(
        code="ml_operator",
        name="ML Operator",
        description="Operate deployments, inference endpoints, monitoring, alerts, and retraining.",
        permissions=frozenset(
            {
                "projects:read",
                "models:read",
                "deployments:create",
                "deployments:read",
                "deployments:rollback",
                "deployment_revisions:create",
                "deployment_revisions:traffic",
                "deployment_health:write",
                "inference_endpoints:create",
                "inference_endpoints:read",
                "inference:predict",
                "inference_metrics:write",
                "monitoring:read",
                "alert_rules:create",
                "alert_rules:read",
                "alert_rules:evaluate",
                "alert_events:read",
                "alert_events:acknowledge",
                "alert_events:resolve",
                "drift_profiles:create",
                "drift_profiles:read",
                "drift_reports:create",
                "drift_reports:read",
                "retraining_policies:create",
                "retraining_policies:read",
                "retraining_runs:create",
                "retraining_runs:read",
                "retraining_runs:approve",
                "retraining_runs:reject",
                "training_runs:create",
                "training_runs:read",
            }
        ),
    ),
    RolePreset(
        code="ml_viewer",
        name="ML Viewer",
        description="Read-only access across ForgeML project and ML lifecycle resources.",
        permissions=frozenset(
            {
                "projects:read",
                "datasets:read",
                "feature_sets:read",
                "experiments:read",
                "experiment_runs:read",
                "training_runs:read",
                "models:read",
                "deployments:read",
                "inference_endpoints:read",
                "monitoring:read",
                "alert_rules:read",
                "alert_events:read",
                "drift_profiles:read",
                "drift_reports:read",
                "retraining_policies:read",
                "retraining_runs:read",
            }
        ),
    ),
    RolePreset(
        code="security_auditor",
        name="Security Auditor",
        description="Read audit trails and platform activity without mutation rights.",
        permissions=frozenset({"admin:audit_log:read", "projects:read"}),
    ),
)


def permission_codes() -> frozenset[str]:
    return frozenset(permission.code for permission in PERMISSIONS)


def role_preset_codes() -> frozenset[str]:
    return frozenset(role.code for role in ROLE_PRESETS)
