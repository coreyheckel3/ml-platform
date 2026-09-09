import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminControlsPage } from "./AdminControlsPage";
import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_EXPIRES_AT_KEY,
  TOKEN_TYPE_KEY,
} from "../../auth/session/sessionStore";
import type { PlatformAdminControls } from "../api/adminControls";

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("AdminControlsPage", () => {
  it("renders organization, RBAC, environment, and safe workflow controls", async () => {
    seedSession();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe("/api/v1/admin/controls");
      expect(init?.headers).toMatchObject({
        authorization: "Bearer token-123",
      });
      return jsonResponse(adminControls());
    });
    vi.stubGlobal("fetch", fetchMock);

    renderAdminControlsPage();

    expect(
      await screen.findByRole("heading", { name: "Admin Controls" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Organization Overview")).toBeInTheDocument();
    expect(screen.getByText("ForgeML Local")).toBeInTheDocument();
    expect(screen.getByText("forgeml.platform_admin_controls.v1")).toBeInTheDocument();
    expect(screen.getByText("User Access")).toBeInTheDocument();
    expect(screen.getByText("admin@forgeml.dev")).toBeInTheDocument();
    expect(screen.getByText("RBAC Matrix")).toBeInTheDocument();
    expect(screen.getAllByText("Platform Admin").length).toBeGreaterThan(0);
    expect(screen.getByText("Permission Catalog")).toBeInTheDocument();
    expect(screen.getByText("admin:controls:read")).toBeInTheDocument();
    expect(screen.getByText("Environment Visibility")).toBeInTheDocument();
    expect(screen.getByText("github_actions")).toBeInTheDocument();
    expect(screen.getByText("Safe Admin Workflows")).toBeInTheDocument();
    expect(screen.getByText("Tenant isolation")).toBeInTheDocument();
    expect(screen.getByText("RBAC mutations")).toBeInTheDocument();
    expect(screen.getByText("make production-readiness")).toBeInTheDocument();
    expect(
      screen.getByText(
        "PYTHONPATH=. python scripts/ci/check_platform_admin_controls_contract.py",
      ),
    ).toBeInTheDocument();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });

  it("does not fetch controls when signed out", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderAdminControlsPage();

    expect(screen.getByText("Sign in to view platform admin controls.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function renderAdminControlsPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <AdminControlsPage />
    </QueryClientProvider>,
  );
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function seedSession() {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, "token-123");
  window.localStorage.setItem(REFRESH_TOKEN_KEY, "refresh-token");
  window.localStorage.setItem(TOKEN_TYPE_KEY, "bearer");
  window.localStorage.setItem(
    TOKEN_EXPIRES_AT_KEY,
    new Date(Date.now() + 900_000).toISOString(),
  );
}

function adminControls(): PlatformAdminControls {
  return {
    schema_version: "forgeml.platform_admin_controls.v1",
    organization: {
      id: "org-1",
      name: "ForgeML Local",
      slug: "forgeml-local",
      status: "active",
      created_at: "2026-08-17T12:00:00Z",
    },
    users: [
      {
        id: "user-1",
        email: "admin@forgeml.dev",
        display_name: "Platform Admin",
        status: "active",
        permissions: ["admin:controls:read", "projects:read"],
        permission_count: 2,
        role_codes: ["platform_admin"],
        last_login_at: "2026-08-17T12:30:00Z",
        created_at: "2026-08-17T12:00:00Z",
        updated_at: "2026-08-17T12:15:00Z",
      },
    ],
    role_presets: [
      {
        code: "platform_admin",
        name: "Platform Admin",
        description: "Full organization administration.",
        permissions: ["admin:controls:read", "projects:read"],
        permission_count: 2,
        assigned_user_count: 1,
        granted_to_current_principal: true,
      },
    ],
    permission_groups: [
      {
        module: "administration",
        permission_count: 1,
        granted_count: 1,
        permissions: [
          {
            code: "admin:controls:read",
            module: "administration",
            action: "read",
            description: "Read organization administration controls.",
            granted_to_current_principal: true,
          },
        ],
      },
    ],
    environment: {
      environment: "local",
      production_like: false,
      docs_enabled: true,
      rate_limit_enabled: true,
      request_logging_enabled: true,
      structured_logging_enabled: true,
      readiness_checks_enabled: true,
      external_training_profiles_enabled: true,
      release_evidence_provider: "github_actions",
      release_evidence_repository: "coreyheckel3/ml-platform",
      release_evidence_branch: "main",
      release_evidence_workflow: "ci.yml",
      release_evidence_artifact_name: "forgeml-release-manifest",
      object_storage_configured: true,
      redis_configured: true,
      mlflow_tracking_configured: true,
      airflow_orchestration_enabled: false,
      cors_origin_count: 1,
      access_token_ttl_seconds: 900,
      refresh_token_ttl_seconds: 2_592_000,
      jwt_issuer: "forgeml",
    },
    safeguards: [
      {
        label: "Tenant isolation",
        status: "enforced",
        detail: "Admin controls are organization scoped.",
        evidence: "backend/tests/integration/security/test_tenant_isolation.py",
      },
      {
        label: "RBAC mutations",
        status: "read-only",
        detail: "Role changes require audited workflows.",
        evidence: "contracts/security/permission-catalog.v1.json",
      },
    ],
    operator_commands: [
      "make production-readiness",
      "PYTHONPATH=. python scripts/ci/check_platform_admin_controls_contract.py",
    ],
    stats: {
      total_users: 1,
      active_users: 1,
      disabled_users: 0,
      project_count: 3,
      audit_event_count: 8,
      release_evidence_report_count: 2,
      role_preset_count: 1,
      permission_count: 2,
      permission_group_count: 1,
    },
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
