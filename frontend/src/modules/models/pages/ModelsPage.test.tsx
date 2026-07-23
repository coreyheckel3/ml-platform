import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ModelsPage } from "./ModelsPage";

type FetchCall = [string, RequestInit | undefined];

const trainingRunId = "11111111-1111-4111-8111-111111111111";
const modelId = "model-1";

describe("ModelsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("promotes a succeeded training run and reviews the model version", async () => {
    const fetchMock = mockRegistryWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ModelsPage />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("form", { name: "Promote training run" })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Promote" })).not.toBeDisabled()
    );
    fireEvent.click(screen.getByRole("button", { name: "Promote" }));

    expect(await screen.findByText("Promoted v1 from 11111111")).toBeInTheDocument();
    const promoteCall = findFetchCall(fetchMock, "promote-training-run");
    expect(JSON.parse(String(promoteCall[1]?.body))).toMatchObject({
      training_run_id: trainingRunId,
      model_format: "xgboost-booster",
      signature: {
        metadata: {
          training_run_id: trainingRunId,
          model_type: "xgboost"
        }
      }
    });

    fireEvent.click(await screen.findByRole("button", { name: "Request approval" }));
    expect(await screen.findByText("Approval requested.")).toBeInTheDocument();
    expect(findFetchCall(fetchMock, "approval-request")).toBeTruthy();

    fireEvent.click(await screen.findByRole("button", { name: "Approve v1" }));
    expect(await screen.findByText("Version approved.")).toBeInTheDocument();
    const reviewCall = findFetchCall(fetchMock, "/review");
    expect(JSON.parse(String(reviewCall[1]?.body))).toMatchObject({
      status: "approved"
    });
  });
});

function mockRegistryWorkflow() {
  let versions: Array<Record<string, unknown>> = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    const method = init?.method ?? "GET";

    if (method === "GET" && path === "/api/v1/projects/project-1/models") {
      return jsonResponse({
        items: [
          {
            id: modelId,
            organization_id: "org-1",
            project_id: "project-1",
            name: "Fraud Risk XGB",
            slug: "fraud-risk-xgb",
            description: "Payment risk scoring",
            task_type: "classification",
            owner_user_id: "user-1",
            status: "active"
          }
        ],
        next_cursor: null
      });
    }

    if (method === "GET" && path === `/api/v1/models/${modelId}/versions`) {
      return jsonResponse({ items: versions, next_cursor: null });
    }

    if (method === "GET" && path === "/api/v1/projects/project-1/training-runs") {
      return jsonResponse({
        items: [
          {
            id: trainingRunId,
            organization_id: "org-1",
            project_id: "project-1",
            experiment_id: "experiment-1",
            experiment_run_id: "experiment-run-1",
            dataset_version_id: "dataset-version-1",
            feature_set_id: "feature-set-1",
            algorithm: "xgboost",
            model_type: "xgboost",
            objective_metric_name: "auc",
            hyperparameters: { max_depth: 6 },
            status: "succeeded",
            requested_by: "user-1",
            artifact_uri: "s3://forgeml/training-runs/run-1",
            orchestrator_run_id: "workflow-1",
            metrics: { auc: 0.94 },
            error_message: null
          }
        ],
        next_cursor: null
      });
    }

    if (method === "POST" && path.endsWith("/promote-training-run")) {
      const version = modelVersion("candidate");
      versions = [version];
      return jsonResponse(version);
    }

    if (method === "POST" && path.endsWith("/approval-request")) {
      versions = [modelVersion("pending_approval")];
      return jsonResponse({
        id: "approval-1",
        model_version_id: "model-version-1",
        status: "requested",
        requested_by: "user-1",
        reviewer_id: null,
        comment: "Requesting approval",
        policy_snapshot: {}
      });
    }

    if (method === "POST" && path.endsWith("/review")) {
      versions = [modelVersion("approved")];
      return jsonResponse({
        id: "approval-2",
        model_version_id: "model-version-1",
        status: "approved",
        requested_by: "user-1",
        reviewer_id: "user-1",
        comment: "Approved",
        policy_snapshot: {}
      });
    }

    return jsonResponse({ detail: "unexpected request" }, false);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function modelVersion(status: string): Record<string, unknown> {
  return {
    id: "model-version-1",
    registered_model_id: modelId,
    version: 1,
    training_run_id: trainingRunId,
    experiment_run_id: "experiment-run-1",
    artifact_uri: "s3://forgeml/training-runs/run-1/model.json",
    model_format: "xgboost-booster",
    signature: { inputs: [], outputs: [] },
    metrics: { auc: 0.94 },
    status,
    created_by: "user-1"
  };
}

function jsonResponse(payload: object, ok = true): Promise<Response> {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    json: async () => payload
  } as Response);
}

function findFetchCall(fetchMock: ReturnType<typeof vi.fn>, fragment: string): FetchCall {
  const call = fetchMock.mock.calls.find(([input]) => String(input).includes(fragment));
  if (!call) {
    throw new Error(`Expected fetch call containing ${fragment}`);
  }
  return call as FetchCall;
}
