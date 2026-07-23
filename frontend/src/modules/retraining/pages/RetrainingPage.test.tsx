import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RetrainingPage } from "./RetrainingPage";

type FetchCall = [string, RequestInit | undefined];

const policyId = "policy-2";
const initialRunId = "run-1";
const triggeredRunId = "run-2";

describe("RetrainingPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates a policy, triggers manual retraining, and handles approval actions", async () => {
    const fetchMock = mockRetrainingWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <RetrainingPage />
      </QueryClientProvider>,
    );

    expect((await screen.findAllByText("Fraud Drift Retraining")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Policy" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Create policy" })).not.toBeDisabled(),
    );

    fireEvent.change(screen.getByLabelText("Policy Name"), {
      target: { value: "Fraud Auto Retraining" },
    });
    fireEvent.change(screen.getByLabelText("Policy Description"), {
      target: { value: "Automated retraining for serving quality regressions." },
    });
    fireEvent.change(screen.getByLabelText("Minimum Drift Score"), {
      target: { value: "0.25" },
    });
    fireEvent.change(screen.getByLabelText("Minimum Drifted Features"), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText("Run Name Prefix"), {
      target: { value: "fraud-retrain" },
    });
    fireEvent.change(screen.getByLabelText("Algorithm"), {
      target: { value: "xgboost" },
    });
    fireEvent.change(screen.getByLabelText("Model Type"), {
      target: { value: "xgboost" },
    });
    fireEvent.change(screen.getByLabelText("Objective Metric"), {
      target: { value: "auc" },
    });
    fireEvent.change(screen.getByLabelText("Hyperparameters"), {
      target: { value: JSON.stringify({ max_depth: 6, learning_rate: 0.05 }) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create policy" }));

    expect(
      await screen.findByText("Created retraining policy Fraud Auto Retraining."),
    ).toBeInTheDocument();
    const createCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/retraining-policies",
      "POST",
    );
    expect(JSON.parse(String(createCall[1]?.body))).toMatchObject({
      deployment_id: "deployment-1",
      name: "Fraud Auto Retraining",
      description: "Automated retraining for serving quality regressions.",
      trigger_type: "drift",
      trigger_config: {
        min_drift_score: 0.25,
        min_drifted_features: 2,
      },
      training_template: {
        experiment_id: "experiment-1",
        dataset_version_id: "dataset-version-1",
        feature_set_id: null,
        run_name_prefix: "fraud-retrain",
        algorithm: "xgboost",
        model_type: "xgboost",
        objective_metric_name: "auc",
        hyperparameters: { max_depth: 6, learning_rate: 0.05 },
      },
      cooldown_seconds: 3600,
      max_runs_per_day: 3,
      approval_required: true,
      enabled: true,
    });

    fireEvent.change(screen.getByLabelText("Manual Reason"), {
      target: { value: "Operator verified drift remediation." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Trigger manual run" }));

    expect(
      await screen.findByText("Manual retraining is waiting for approval."),
    ).toBeInTheDocument();
    const triggerCall = findFetchCall(
      fetchMock,
      `/api/v1/retraining-policies/${policyId}/trigger`,
      "POST",
    );
    expect(JSON.parse(String(triggerCall[1]?.body))).toMatchObject({
      reason: "Operator verified drift remediation.",
    });

    fireEvent.click(
      await screen.findByRole("button", {
        name: `Approve retraining run ${triggeredRunId}`,
      }),
    );
    expect(
      await screen.findByText(`Approved retraining run ${triggeredRunId}.`),
    ).toBeInTheDocument();
    expect(
      findFetchCall(fetchMock, `/api/v1/retraining-runs/${triggeredRunId}/approve`, "POST"),
    ).toBeTruthy();

    fireEvent.click(
      await screen.findByRole("button", {
        name: `Reject retraining run ${initialRunId}`,
      }),
    );
    expect(
      await screen.findByText(`Rejected retraining run ${initialRunId}.`),
    ).toBeInTheDocument();
    expect(
      findFetchCall(fetchMock, `/api/v1/retraining-runs/${initialRunId}/reject`, "POST"),
    ).toBeTruthy();
  });
});

function mockRetrainingWorkflow() {
  let policies = [retrainingPolicy("policy-1", "Fraud Drift Retraining")];
  let runs = [
    retrainingRun({
      id: initialRunId,
      policy_id: "policy-1",
      status: "pending_approval",
      training_run_id: null,
    }),
  ];
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/retraining-policies"
      ) {
        return jsonResponse({ items: policies, next_cursor: null });
      }

      if (method === "GET" && path === "/api/v1/projects/project-1/retraining-runs") {
        return jsonResponse({ items: runs, next_cursor: null });
      }

      if (method === "GET" && path === "/api/v1/projects/project-1/deployments") {
        return jsonResponse({
          items: [
            {
              id: "deployment-1",
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud API",
              slug: "fraud-api",
              description: "Payment risk serving",
              environment: "production",
              status: "active",
              created_by: "user-1",
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === "/api/v1/projects/project-1/experiments") {
        return jsonResponse({
          items: [
            {
              id: "experiment-1",
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud Experiment",
              slug: "fraud-experiment",
              description: "Fraud model training",
              owner_user_id: "user-1",
              status: "active",
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === "/api/v1/projects/project-1/datasets") {
        return jsonResponse({
          items: [
            {
              id: "dataset-1",
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud Labels",
              slug: "fraud-labels",
              description: "Validated training labels",
              source_type: "upload",
              status: "active",
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === "/api/v1/datasets/dataset-1/versions") {
        return jsonResponse({
          items: [
            {
              id: "dataset-version-1",
              dataset_id: "dataset-1",
              version: 3,
              object_uri: "s3://forgeml/datasets/fraud/v3.csv",
              content_hash: "sha256:abc123",
              row_count: 12000,
              size_bytes: 4096,
              status: "validated",
              created_by: "user-1",
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === "/api/v1/projects/project-1/feature-sets") {
        return jsonResponse({
          items: [
            {
              id: "feature-set-1",
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud Features",
              slug: "fraud-features",
              description: "Online fraud features",
              entity_key: "account_id",
              status: "active",
            },
          ],
          next_cursor: null,
        });
      }

      if (
        method === "POST" &&
        path === "/api/v1/projects/project-1/retraining-policies"
      ) {
        const created = retrainingPolicy(policyId, "Fraud Auto Retraining");
        policies = [created, ...policies];
        return jsonResponse(created);
      }

      if (method === "POST" && path === `/api/v1/retraining-policies/${policyId}/trigger`) {
        const run = retrainingRun({
          id: triggeredRunId,
          policy_id: policyId,
          status: "pending_approval",
          training_run_id: null,
        });
        runs = [run, ...runs];
        return jsonResponse({
          policy_id: policyId,
          decision: "pending_approval",
          triggered: true,
          reason: "Retraining run is waiting for approval.",
          run,
        });
      }

      if (method === "POST" && path === `/api/v1/retraining-runs/${triggeredRunId}/approve`) {
        const approved = retrainingRun({
          id: triggeredRunId,
          policy_id: policyId,
          status: "queued",
          training_run_id: "training-run-2",
          approved_by: "user-1",
        });
        runs = runs.map((run) => (run.id === triggeredRunId ? approved : run));
        return jsonResponse(approved);
      }

      if (method === "POST" && path === `/api/v1/retraining-runs/${initialRunId}/reject`) {
        const rejected = retrainingRun({
          id: initialRunId,
          policy_id: "policy-1",
          status: "rejected",
          training_run_id: null,
          rejected_by: "user-1",
        });
        runs = runs.map((run) => (run.id === initialRunId ? rejected : run));
        return jsonResponse(rejected);
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

function retrainingPolicy(id: string, name: string): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    deployment_id: "deployment-1",
    name,
    slug: name.toLowerCase().replaceAll(" ", "-"),
    description: "Retrain fraud model when drift breaches thresholds.",
    trigger_type: "drift",
    trigger_config: { min_drift_score: 0.2, min_drifted_features: 1 },
    training_template: {
      experiment_id: "experiment-1",
      dataset_version_id: "dataset-version-1",
      feature_set_id: null,
      run_name_prefix: "fraud-retrain",
      algorithm: "xgboost",
      model_type: "xgboost",
      objective_metric_name: "auc",
      hyperparameters: { max_depth: 6 },
    },
    cooldown_seconds: 3600,
    max_runs_per_day: 3,
    approval_required: true,
    enabled: true,
    status: "active",
    created_by: "user-1",
    created_at: null,
    updated_at: null,
  };
}

function retrainingRun({
  id,
  policy_id,
  status,
  training_run_id,
  approved_by = null,
  rejected_by = null,
}: {
  id: string;
  policy_id: string;
  status: string;
  training_run_id: string | null;
  approved_by?: string | null;
  rejected_by?: string | null;
}): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    policy_id,
    deployment_id: "deployment-1",
    trigger_type: status === "pending_approval" ? "manual" : "drift",
    drift_report_id: status === "pending_approval" ? null : "drift-report-1",
    alert_event_id: null,
    training_run_id,
    status,
    reason: "Operator verified drift remediation.",
    training_config: {
      run_name: `${id}-fraud-retrain`,
      algorithm: "xgboost",
      model_type: "xgboost",
      objective_metric_name: "auc",
    },
    decision_metadata: {
      reason: "Retraining run is waiting for approval.",
      drift_score: 0.42,
    },
    requested_by: "user-1",
    approved_by,
    rejected_by,
    created_at: null,
    updated_at: null,
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
