import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MemoryRouter } from "../../../shared/routing/router";
import {
  ACCESS_TOKEN_KEY,
  PROJECT_CONTEXT_KEY,
} from "../../auth/session/sessionStore";
import { EvaluationPage } from "./EvaluationPage";

describe("EvaluationPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("renders evaluation comparison and reviewer evidence from the API", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      expect(String(input)).toBe("/api/v1/projects/project-1/evaluation/comparison");
      return jsonResponse({
        schema_version: "forgeml.evaluation_comparison.v1",
        project_id: "project-1",
        project_name: "Fraud Detection",
        project_slug: "fraud-detection",
        project_status: "active",
        primary_metric_name: "auc",
        higher_is_better: true,
        candidate_count: 2,
        recommended_experiment_run_id: "experiment-run-champion",
        leaderboard: [
          {
            rank: 1,
            experiment_run_id: "experiment-run-champion",
            run_name: "fraud-xgb-v2",
            experiment_name: "Fraud Risk Baseline",
            status: "succeeded",
            model_type: "binary_classifier",
            primary_metric_name: "auc",
            primary_metric_value: 0.9624,
            delta_from_baseline: 0.0312,
            quality_score: 100,
            model_version_label: "Fraud Risk XGB v2",
            approval_status: "approved",
            evidence_summary: "Fraud Risk XGB v2 is approved with registry evidence.",
          },
        ],
        metric_slices: [
          {
            metric_name: "auc",
            candidate_count: 2,
            best_value: 0.9624,
            baseline_value: 0.9312,
            delta_from_baseline: 0.0312,
            best_experiment_run_id: "experiment-run-champion",
            best_run_name: "fraud-xgb-v2",
            higher_is_better: true,
          },
        ],
        model_cards: [
          {
            model_version_id: "model-version-2",
            model_name: "Fraud Risk XGB",
            version: 2,
            status: "approved",
            approval_status: "approved",
            model_format: "xgboost-booster",
            metric_summary: [{ label: "auc", value: 0.9624, tone: "success" }],
            signature_summary: ["6 inputs", "1 outputs"],
            artifact_uri: "s3://forgeml/models/fraud-risk-xgb/v2",
            artifact_manifest_uri: "s3://forgeml/models/fraud-risk-xgb/v2/manifest.json",
            artifact_manifest_hash: "sha256:model-manifest",
            lineage_summary: ["dataset_version:validated", "feature_set:merchant"],
            risk_flags: [],
          },
        ],
        approval_checklist: [
          {
            key: "offline_metrics",
            label: "Offline metrics",
            status: "passed",
            detail: "2 metrics are attached to the candidate run.",
            evidence: "fraud-xgb-v2",
          },
        ],
        narrative: ["fraud-xgb-v2 currently leads the comparison on auc=0.9624."],
        generated_at: "2026-08-18T16:30:00Z",
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.setItem(ACCESS_TOKEN_KEY, "token-123");
    window.localStorage.setItem(PROJECT_CONTEXT_KEY, "project-1");

    renderPage();

    expect(screen.getByRole("heading", { name: "Evaluation" })).toBeInTheDocument();
    expect((await screen.findAllByText("fraud-xgb-v2")).length).toBeGreaterThan(0);
    expect(screen.getByText("Run Leaderboard")).toBeInTheDocument();
    expect(screen.getByText("Metric Slices")).toBeInTheDocument();
    expect(screen.getByText("Model Card Evidence")).toBeInTheDocument();
    expect(screen.getByText("Approval Checklist")).toBeInTheDocument();
    expect(screen.getByText("Evaluation Narrative")).toBeInTheDocument();
    expect(screen.getByText("Reviewer ready")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Experiments" })).toHaveAttribute(
      "href",
      "/experiments",
    );
    expect(screen.getByRole("link", { name: "Models" })).toHaveAttribute(
      "href",
      "/models",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/projects/project-1/evaluation/comparison",
      expect.objectContaining({
        headers: expect.objectContaining({
          authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("does not call the API without signed-in project context", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    expect(screen.getByRole("heading", { name: "Evaluation" })).toBeInTheDocument();
    expect(screen.getByText(/Sign in to load evaluation comparisons/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <EvaluationPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    json: async () => body,
  } as Response;
}
