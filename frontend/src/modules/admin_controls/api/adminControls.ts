import { apiGet } from "../../../shared/api/client";

export type AdminOrganization = {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string | null;
};

export type AdminUserAccess = {
  id: string;
  email: string;
  display_name: string;
  status: string;
  permissions: string[];
  permission_count: number;
  role_codes: string[];
  last_login_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AdminRolePreset = {
  code: string;
  name: string;
  description: string;
  permissions: string[];
  permission_count: number;
  assigned_user_count: number;
  granted_to_current_principal: boolean;
};

export type AdminPermission = {
  code: string;
  module: string;
  action: string;
  description: string;
  granted_to_current_principal: boolean;
};

export type AdminPermissionGroup = {
  module: string;
  permission_count: number;
  granted_count: number;
  permissions: AdminPermission[];
};

export type AdminEnvironment = {
  environment: string;
  production_like: boolean;
  docs_enabled: boolean;
  rate_limit_enabled: boolean;
  request_logging_enabled: boolean;
  structured_logging_enabled: boolean;
  readiness_checks_enabled: boolean;
  external_training_profiles_enabled: boolean;
  release_evidence_provider: string;
  release_evidence_repository: string | null;
  release_evidence_branch: string | null;
  release_evidence_workflow: string | null;
  release_evidence_artifact_name: string | null;
  object_storage_configured: boolean;
  redis_configured: boolean;
  mlflow_tracking_configured: boolean;
  airflow_orchestration_enabled: boolean;
  cors_origin_count: number;
  access_token_ttl_seconds: number;
  refresh_token_ttl_seconds: number;
  jwt_issuer: string;
};

export type AdminSafeguard = {
  label: string;
  status: string;
  detail: string;
  evidence: string;
};

export type AdminControlPlaneStats = {
  total_users: number;
  active_users: number;
  disabled_users: number;
  project_count: number;
  audit_event_count: number;
  release_evidence_report_count: number;
  role_preset_count: number;
  permission_count: number;
  permission_group_count: number;
};

export type PlatformAdminControls = {
  schema_version: string;
  organization: AdminOrganization;
  users: AdminUserAccess[];
  role_presets: AdminRolePreset[];
  permission_groups: AdminPermissionGroup[];
  environment: AdminEnvironment;
  safeguards: AdminSafeguard[];
  operator_commands: string[];
  stats: AdminControlPlaneStats;
};

export function getPlatformAdminControls(
  token: string,
): Promise<PlatformAdminControls> {
  return apiGet<PlatformAdminControls>("/api/v1/admin/controls", { token });
}
