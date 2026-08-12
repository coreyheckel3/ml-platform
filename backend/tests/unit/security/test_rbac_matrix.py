import pytest

from forgeml.platform.security.permissions import ROLE_PRESETS, permission_codes
from forgeml.platform.security.rbac import Principal

ROLE_PERMISSIONS = {role.code: role.permissions for role in ROLE_PRESETS}


@pytest.mark.parametrize(
    ("role_code", "allowed", "denied"),
    [
        (
            "platform_admin",
            {
                "admin:audit_log:read",
                "model_versions:review",
                "deployments:rollback",
                "retraining_runs:approve",
            },
            set(),
        ),
        (
            "ml_engineer",
            {
                "datasets:create",
                "training_runs:create",
                "model_versions:request_approval",
                "drift_reports:create",
            },
            {
                "admin:audit_log:read",
                "deployments:rollback",
                "model_versions:review",
                "retraining_runs:approve",
            },
        ),
        (
            "ml_operator",
            {
                "deployments:rollback",
                "inference:predict",
                "alert_events:resolve",
                "retraining_runs:approve",
            },
            {
                "admin:audit_log:read",
                "datasets:create",
                "model_versions:review",
            },
        ),
        (
            "ml_viewer",
            {
                "projects:read",
                "datasets:read",
                "monitoring:read",
                "retraining_runs:read",
            },
            {
                "datasets:create",
                "training_runs:create",
                "deployment_revisions:traffic",
                "alert_events:resolve",
            },
        ),
        (
            "security_auditor",
            {
                "admin:audit_log:read",
                "projects:read",
            },
            {
                "datasets:read",
                "training_runs:create",
                "monitoring:read",
                "deployments:rollback",
            },
        ),
    ],
)
def test_role_preset_permissions_match_security_matrix(
    role_code: str,
    allowed: set[str],
    denied: set[str],
) -> None:
    principal = Principal(
        user_id="user-1",
        email=f"{role_code}@example.com",
        organization_id="organization-1",
        permissions=ROLE_PERMISSIONS[role_code],
    )

    for permission in allowed:
        assert principal.has(permission), f"{role_code} should allow {permission}"
    for permission in denied:
        assert not principal.has(permission), f"{role_code} should deny {permission}"


def test_non_admin_role_presets_do_not_use_wildcard_permissions() -> None:
    for role in ROLE_PRESETS:
        if role.code == "platform_admin":
            assert role.permissions == frozenset({"*"})
            continue
        assert "*" not in role.permissions
        assert role.permissions.issubset(permission_codes())
