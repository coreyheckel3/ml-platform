import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReleaseEvidencePage } from "./ReleaseEvidencePage";
import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_EXPIRES_AT_KEY,
  TOKEN_TYPE_KEY,
} from "../../auth/session/sessionStore";
import type { ReleaseEvidenceReport } from "../api/releaseEvidence";

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("ReleaseEvidencePage", () => {
  it("renders release artifact evidence and reviewer commands", () => {
    renderReleaseEvidencePage();

    expect(
      screen.getByRole("heading", { name: "Release Evidence" }),
    ).toBeInTheDocument();
    expect(screen.getByText("37")).toBeInTheDocument();
    expect(screen.getByText("26")).toBeInTheDocument();
    expect(screen.getAllByText("forgeml-release-manifest").length).toBeGreaterThan(1);
    expect(screen.getByText("Release Manifest")).toBeInTheDocument();
    expect(screen.getByText("Live Evidence Retrieval")).toBeInTheDocument();
    expect(screen.getByText("API Evidence Drilldown")).toBeInTheDocument();
    expect(screen.getByText("GitHubActionsReleaseEvidenceGateway")).toBeInTheDocument();
    expect(screen.getByText("Comparison Signals")).toBeInTheDocument();
    expect(screen.getByText("required_artifact_coverage")).toBeInTheDocument();
    expect(screen.getByText("OpenAPI Contract")).toBeInTheDocument();
    expect(
      screen.getAllByText("Release Evidence Retrieval Contract").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Release Evidence Drilldown API Contract").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("Security Hardening Contract").length).toBeGreaterThan(0);
    expect(screen.getByText("make production-readiness")).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "PYTHONPATH=backend/src:. python scripts/ops/retrieve_release_evidence.py --repo coreyheckel3/ml-platform --branch main --workflow ci.yml --artifact-name forgeml-release-manifest",
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("make demo-screenshots")).toBeInTheDocument();
  });

  it("surfaces quality gates and screenshot evidence", () => {
    renderReleaseEvidencePage();

    expect(screen.getByText("Quality Gate Coverage")).toBeInTheDocument();
    expect(screen.getByText("backend_tests")).toBeInTheDocument();
    expect(screen.getByText("frontend_e2e")).toBeInTheDocument();
    expect(screen.getByText("release_manifest_verifier_contract")).toBeInTheDocument();
    expect(screen.getByText("operational_audit_ux_contract")).toBeInTheDocument();
    expect(screen.getByText("release_evidence_retrieval_contract")).toBeInTheDocument();
    expect(screen.getByText("release_evidence_drilldown_api_contract")).toBeInTheDocument();
    expect(screen.getByText("Demo Screenshot Evidence")).toBeInTheDocument();
    expect(screen.getByText("09-release-evidence.png")).toBeInTheDocument();
    expect(screen.getByText("10-operational-audit.png")).toBeInTheDocument();
    expect(screen.getByText("/release-evidence")).toBeInTheDocument();
  });

  it("loads release evidence reports and can trigger retrieval", async () => {
    writeSession();
    const report = releaseEvidenceReport("report-1", "passed");
    const retrievedReport = releaseEvidenceReport("report-2", "failed", {
      error_message: "release_evidence_drilldown_api_contract is missing",
      missing_quality_gates: ["release_evidence_drilldown_api_contract"],
    });
    let reports = [report];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.includes("/api/v1/admin/release-evidence/reports?")) {
        return jsonResponse({ items: reports, next_cursor: null });
      }
      if (url.endsWith(`/api/v1/admin/release-evidence/reports/${report.id}`)) {
        return jsonResponse(report);
      }
      if (url.endsWith(`/api/v1/admin/release-evidence/reports/${retrievedReport.id}`)) {
        return jsonResponse(retrievedReport);
      }
      if (url.endsWith("/api/v1/admin/release-evidence/reports/retrieve")) {
        expect(init?.method).toBe("POST");
        reports = [retrievedReport, ...reports];
        return jsonResponse(retrievedReport, 201);
      }
      return jsonResponse({ detail: `unexpected request: ${url}` }, 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderReleaseEvidencePage();

    expect(await screen.findByText("release_evidence.retrieve")).toBeInTheDocument();
    expect(screen.getByText("1 loaded")).toBeInTheDocument();
    expect(screen.getByText("abc123def456")).toBeInTheDocument();

    const listCall = fetchMock.mock.calls.find((call) =>
      call[0].toString().includes("/api/v1/admin/release-evidence/reports?"),
    );
    expect(listCall?.[1]?.headers).toMatchObject({
      authorization: "Bearer token-123",
    });

    fireEvent.click(screen.getByRole("button", { name: /retrieve evidence/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/admin/release-evidence/reports/retrieve",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(await screen.findByText("Retrieval recorded as failed.")).toBeInTheDocument();
    expect(screen.getByText("release_evidence.retrieve_failed")).toBeInTheDocument();
    expect(
      screen.getAllByText("release_evidence_drilldown_api_contract").length,
    ).toBeGreaterThan(0);
  });
});

function renderReleaseEvidencePage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ReleaseEvidencePage />
    </QueryClientProvider>,
  );
}

function writeSession() {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, "token-123");
  window.localStorage.setItem(REFRESH_TOKEN_KEY, "refresh-token");
  window.localStorage.setItem(TOKEN_TYPE_KEY, "bearer");
  window.localStorage.setItem(
    TOKEN_EXPIRES_AT_KEY,
    new Date(Date.now() + 3_600_000).toISOString(),
  );
}

function releaseEvidenceReport(
  id: string,
  status: "passed" | "failed",
  overrides: Partial<ReleaseEvidenceReport> = {},
): ReleaseEvidenceReport {
  return {
    id,
    organization_id: "org-1",
    requested_by_user_id: "user-1",
    provider: "github_actions",
    status,
    repository: "coreyheckel3/ml-platform",
    branch: "main",
    workflow: "ci.yml",
    artifact_name: "forgeml-release-manifest",
    run_id: "12345",
    run_url: "https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
    manifest_git_sha: "abc123def4567890",
    manifest_git_branch: "main",
    ci_run_url: "https://github.com/coreyheckel3/ml-platform/actions/runs/12345",
    artifact_count: 37,
    quality_gate_count: 26,
    missing_artifacts: [],
    missing_quality_gates: [],
    comparison: { passed: status === "passed" },
    manifest_summary: {
      artifact_names: ["release_evidence_drilldown_api_contract"],
      quality_gate_names: ["release_evidence_drilldown_api_contract"],
    },
    report: {
      schema_version: "forgeml.release_evidence_retrieval.v1",
      status,
    },
    error_message: null,
    created_at: "2026-08-17T12:30:00Z",
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
