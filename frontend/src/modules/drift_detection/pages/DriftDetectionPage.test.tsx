import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DriftDetectionPage } from "./DriftDetectionPage";

type FetchCall = [string, RequestInit | undefined];

const profileId = "profile-2";
const reportId = "report-2";
const endpointId = "endpoint-1";
const policyId = "policy-1";

describe("DriftDetectionPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates profiles, runs drift reports, and evaluates retraining handoff", async () => {
    const fetchMock = mockDriftWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DriftDetectionPage />
      </QueryClientProvider>,
    );

    expect((await screen.findAllByText("Fraud Reference")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Profile" }));
    fireEvent.change(screen.getByLabelText("Profile Name"), {
      target: { value: "Production Baseline" },
    });
    fireEvent.change(screen.getByLabelText("Profile Description"), {
      target: { value: "Validated production reference profile" },
    });
    fireEvent.change(screen.getByLabelText("Baseline Profile"), {
      target: {
        value: JSON.stringify({
          transaction_amount: {
            type: "numeric",
            mean: 130,
            std: 41,
            threshold: 0.18,
          },
          merchant_category: {
            type: "categorical",
            distribution: { grocery: 0.4, travel: 0.2, digital: 0.4 },
            threshold: 0.2,
          },
        }),
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));

    expect(
      await screen.findByText("Created drift profile Production Baseline."),
    ).toBeInTheDocument();
    const createProfileCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/drift-profiles",
      "POST",
    );
    expect(JSON.parse(String(createProfileCall[1]?.body))).toMatchObject({
      name: "Production Baseline",
      description: "Validated production reference profile",
      baseline_profile: {
        transaction_amount: {
          type: "numeric",
          mean: 130,
          std: 41,
          threshold: 0.18,
        },
      },
    });

    expect((await screen.findAllByText("Production Baseline")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Reference Profile"), {
      target: { value: profileId },
    });
    fireEvent.change(screen.getByLabelText("Drift Threshold"), {
      target: { value: "0.15" },
    });
    fireEvent.change(screen.getByLabelText("Report Window"), {
      target: { value: "1800" },
    });
    fireEvent.change(screen.getByLabelText("Sample Limit"), {
      target: { value: "500" },
    });
    fireEvent.change(screen.getByLabelText("Report URI"), {
      target: { value: "s3://forgeml/reports/report-2.json" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run drift report" }));

    expect(
      await screen.findByText("Completed drift report for Fraud Online."),
    ).toBeInTheDocument();
    const runReportCall = findFetchCall(
      fetchMock,
      `/api/v1/drift-profiles/${profileId}/reports`,
      "POST",
    );
    expect(JSON.parse(String(runReportCall[1]?.body))).toMatchObject({
      endpoint_id: endpointId,
      window_seconds: 1800,
      drift_threshold: 0.15,
      sample_limit: 500,
      report_uri: "s3://forgeml/reports/report-2.json",
    });
    expect((await screen.findAllByText("transaction_amount")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Evaluate retraining" }));

    expect(
      await screen.findByText("Retraining approval requested for drift report report-2."),
    ).toBeInTheDocument();
    const evaluateCall = findFetchCall(
      fetchMock,
      `/api/v1/retraining-policies/${policyId}/evaluate`,
      "POST",
    );
    expect(JSON.parse(String(evaluateCall[1]?.body))).toMatchObject({
      drift_report_id: reportId,
      alert_event_id: null,
    });
  });
});

function mockDriftWorkflow() {
  let profiles = [driftProfile("profile-1", "Fraud Reference")];
  let reports = [driftReport("report-1", "profile-1", 0.12, 0)];
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/drift-profiles"
      ) {
        return jsonResponse({ items: profiles, next_cursor: null });
      }

      if (
        method === "POST" &&
        path === "/api/v1/projects/project-1/drift-profiles"
      ) {
        const profile = driftProfile(profileId, "Production Baseline");
        profiles = [profile, ...profiles];
        return jsonResponse(profile);
      }

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/drift-reports"
      ) {
        return jsonResponse({ items: reports, next_cursor: null });
      }

      if (
        method === "POST" &&
        path === `/api/v1/drift-profiles/${profileId}/reports`
      ) {
        const report = driftReport(reportId, profileId, 0.31, 2);
        reports = [report, ...reports];
        return jsonResponse(report);
      }

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/monitoring/inference-endpoints"
      ) {
        return jsonResponse({
          items: [
            {
              endpoint_id: endpointId,
              endpoint_name: "Fraud Online",
              route_path: "/inference/fraud-online",
              status: "active",
              deployment_id: "deployment-1",
              deployment_revision_id: "revision-1",
              latest_window_seconds: 300,
              prediction_count: 1800,
              error_count: 8,
              request_count: 1800,
              error_rate: 0.0044,
              p50_latency_ms: 42,
              p95_latency_ms: 118,
            },
          ],
          next_cursor: null,
        });
      }

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/retraining-policies"
      ) {
        return jsonResponse({
          items: [
            {
              id: policyId,
              organization_id: "org-1",
              project_id: "project-1",
              deployment_id: "deployment-1",
              name: "Fraud drift retraining",
              slug: "fraud-drift-retraining",
              description: "Retrain when drift exceeds quality guardrails.",
              trigger_type: "drift",
              trigger_config: { min_drift_score: 0.2, min_drifted_features: 1 },
              training_template: { algorithm: "xgboost" },
              cooldown_seconds: 3600,
              max_runs_per_day: 3,
              approval_required: true,
              enabled: true,
              status: "active",
              created_by: "user-1",
              created_at: null,
              updated_at: null,
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === `/api/v1/drift-reports/${reportId}/features`) {
        return jsonResponse({
          items: [
            {
              id: "feature-1",
              drift_report_id: reportId,
              feature_name: "transaction_amount",
              feature_type: "numeric",
              drift_score: 0.31,
              threshold: 0.18,
              drift_detected: true,
              statistics: {
                baseline_mean: 130,
                observed_mean: 178,
                sample_count: 500,
              },
            },
            {
              id: "feature-2",
              drift_report_id: reportId,
              feature_name: "merchant_category",
              feature_type: "categorical",
              drift_score: 0.24,
              threshold: 0.2,
              drift_detected: true,
              statistics: {
                sample_count: 500,
              },
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === "/api/v1/drift-reports/report-1/features") {
        return jsonResponse({
          items: [
            {
              id: "feature-0",
              drift_report_id: "report-1",
              feature_name: "request_score",
              feature_type: "numeric",
              drift_score: 0.12,
              threshold: 0.2,
              drift_detected: false,
              statistics: { sample_count: 200 },
            },
          ],
          next_cursor: null,
        });
      }

      if (
        method === "POST" &&
        path === `/api/v1/retraining-policies/${policyId}/evaluate`
      ) {
        return jsonResponse({
          policy_id: policyId,
          decision: "triggered",
          triggered: true,
          reason: "Drift report exceeds retraining policy thresholds.",
          run: {
            id: "run-1",
            organization_id: "org-1",
            project_id: "project-1",
            policy_id: policyId,
            deployment_id: "deployment-1",
            trigger_type: "drift",
            drift_report_id: reportId,
            alert_event_id: null,
            training_run_id: null,
            status: "pending_approval",
            reason: "Drift report exceeds retraining policy thresholds.",
            training_config: { run_name: "fraud-drift-retraining" },
            decision_metadata: { drift_score: 0.31 },
            requested_by: "user-1",
            approved_by: null,
            rejected_by: null,
            created_at: null,
            updated_at: null,
          },
        });
      }

      return jsonResponse(
        { detail: `unexpected request: ${method} ${path}` },
        false,
      );
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function driftProfile(id: string, name: string): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    name,
    slug: name.toLowerCase().replaceAll(" ", "-"),
    description: "Reference distribution for production drift checks.",
    model_version_id: null,
    dataset_version_id: null,
    baseline_profile: {
      request_score: {
        type: "numeric",
        mean: 0.55,
        std: 0.12,
        threshold: 0.2,
      },
    },
    status: "active",
    created_by: "user-1",
  };
}

function driftReport(
  id: string,
  driftProfileId: string,
  driftScore: number,
  driftedFeatureCount: number,
): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    drift_profile_id: driftProfileId,
    endpoint_id: endpointId,
    deployment_id: "deployment-1",
    deployment_revision_id: "revision-1",
    status: "completed",
    drift_score: driftScore,
    drifted_feature_count: driftedFeatureCount,
    evaluated_feature_count: 2,
    window_seconds: 1800,
    drift_threshold: 0.15,
    summary: {
      endpoint_name: "Fraud Online",
      route_path: "/inference/fraud-online",
      sample_count: 500,
      drifted_feature_ratio: driftedFeatureCount / 2,
    },
    report_uri: "s3://forgeml/reports/report.json",
    error_message: null,
  };
}

function jsonResponse(payload: object, ok = true): Promise<Response> {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    json: async () => payload,
  } as Response);
}

function findFetchCall(
  fetchMock: ReturnType<typeof vi.fn>,
  fragment: string,
  method: string,
): FetchCall {
  const call = fetchMock.mock.calls.find(([input, init]) => {
    return (
      String(input).includes(fragment) && (init?.method ?? "GET") === method
    );
  });
  if (!call) {
    throw new Error(`Expected ${method} fetch call containing ${fragment}`);
  }
  return call as FetchCall;
}
