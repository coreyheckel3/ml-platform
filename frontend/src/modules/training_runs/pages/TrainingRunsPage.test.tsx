import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TrainingRunsPage } from "./TrainingRunsPage";

type FetchCall = [string, RequestInit | undefined];

const initialRunId = "run-1";
const startedRunId = "run-2";

describe("TrainingRunsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("starts training runs, records results, and cancels queued runs", async () => {
    const fetchMock = mockTrainingWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <TrainingRunsPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Training run was queued.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Start run" })).not.toBeDisabled(),
    );
    fireEvent.change(screen.getByLabelText("Run Name"), {
      target: { value: "fraud-xgb-depth-8" },
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
      target: { value: JSON.stringify({ max_depth: 8, learning_rate: 0.05 }) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start run" }));

    expect(await screen.findByText(`Started training run ${startedRunId}.`)).toBeInTheDocument();
    const startCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/training-runs",
      "POST",
    );
    expect(JSON.parse(String(startCall[1]?.body))).toMatchObject({
      experiment_id: "experiment-1",
      run_name: "fraud-xgb-depth-8",
      dataset_version_id: "dataset-version-1",
      feature_set_id: null,
      algorithm: "xgboost",
      model_type: "xgboost",
      objective_metric_name: "auc",
      hyperparameters: { max_depth: 8, learning_rate: 0.05 },
    });

    expect(await screen.findByText("Started from the training UI.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Record result" }));

    expect(
      await screen.findByText(`Recorded succeeded result for ${startedRunId}.`),
    ).toBeInTheDocument();
    const resultCall = findFetchCall(
      fetchMock,
      `/api/v1/training-runs/${startedRunId}/result`,
      "POST",
    );
    expect(JSON.parse(String(resultCall[1]?.body))).toMatchObject({
      status: "succeeded",
      metrics: { auc: 0.94, log_loss: 0.18 },
      evaluation_report: {
        validation: {
          slice_count: 4,
          passed: true,
        },
      },
      error_message: null,
    });
    expect((await screen.findAllByText("auc 0.940")).length).toBeGreaterThan(0);

    fireEvent.click(
      await screen.findByRole("button", {
        name: `Cancel training run ${initialRunId}`,
      }),
    );
    expect(await screen.findByText(`Canceled training run ${initialRunId}.`)).toBeInTheDocument();
    expect(
      findFetchCall(fetchMock, `/api/v1/training-runs/${initialRunId}/cancel`, "POST"),
    ).toBeTruthy();
  });
});

function mockTrainingWorkflow() {
  let runs = [
    trainingRun({
      id: initialRunId,
      status: "queued",
      metrics: {},
      orchestrator_run_id: "workflow-1",
    }),
  ];
  const eventMap: Record<string, Array<Record<string, unknown>>> = {
    [initialRunId]: [trainingEvent(initialRunId, "queued", "Training run was queued.")],
  };
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (method === "GET" && path === "/api/v1/projects/project-1/training-runs") {
        return jsonResponse({ items: runs, next_cursor: null });
      }

      if (method === "GET" && path.startsWith("/api/v1/training-runs/")) {
        const suffix = path.split("/api/v1/training-runs/")[1] ?? "";
        const [runId, nested] = suffix.split("/");
        if (nested === "events") {
          return jsonResponse({ items: eventMap[runId] ?? [], next_cursor: null });
        }
        const run = runs.find((item) => item.id === runId);
        return run ? jsonResponse(run) : jsonResponse({ detail: "not found" }, false);
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
              description: "Validated labels",
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

      if (method === "POST" && path === "/api/v1/projects/project-1/training-runs") {
        const started = trainingRun({
          id: startedRunId,
          status: "queued",
          metrics: {},
          orchestrator_run_id: "workflow-2",
        });
        runs = [started, ...runs];
        eventMap[startedRunId] = [
          trainingEvent(startedRunId, "queued", "Started from the training UI."),
        ];
        return jsonResponse(started);
      }

      if (method === "POST" && path === `/api/v1/training-runs/${startedRunId}/result`) {
        const succeeded = trainingRun({
          id: startedRunId,
          status: "succeeded",
          metrics: { auc: 0.94, log_loss: 0.18 },
          orchestrator_run_id: "workflow-2",
        });
        runs = runs.map((run) => (run.id === startedRunId ? succeeded : run));
        eventMap[startedRunId] = [
          trainingEvent(startedRunId, "succeeded", "Training run finished with status succeeded."),
          ...(eventMap[startedRunId] ?? []),
        ];
        return jsonResponse(succeeded);
      }

      if (method === "POST" && path === `/api/v1/training-runs/${initialRunId}/cancel`) {
        const canceled = trainingRun({
          id: initialRunId,
          status: "canceled",
          metrics: {},
          orchestrator_run_id: "workflow-1",
          error_message: "Training run was canceled.",
        });
        runs = runs.map((run) => (run.id === initialRunId ? canceled : run));
        eventMap[initialRunId] = [
          trainingEvent(initialRunId, "canceled", "Training run was canceled."),
          ...(eventMap[initialRunId] ?? []),
        ];
        return jsonResponse(canceled);
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

function trainingRun({
  id,
  status,
  metrics,
  orchestrator_run_id,
  error_message = null,
}: {
  id: string;
  status: string;
  metrics: Record<string, number>;
  orchestrator_run_id: string;
  error_message?: string | null;
}): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    experiment_id: "experiment-1",
    experiment_run_id: `${id}-experiment`,
    dataset_version_id: "dataset-version-1",
    feature_set_id: null,
    algorithm: "xgboost",
    model_type: "xgboost",
    objective_metric_name: "auc",
    hyperparameters: { max_depth: 6 },
    status,
    requested_by: "user-1",
    artifact_uri: `s3://forgeml/training-runs/${id}`,
    orchestrator_run_id,
    metrics,
    error_message,
  };
}

function trainingEvent(
  trainingRunId: string,
  eventType: string,
  message: string,
): Record<string, unknown> {
  return {
    id: `${trainingRunId}-${eventType}`,
    training_run_id: trainingRunId,
    event_type: eventType,
    message,
    metadata: {
      orchestrator_run_id: trainingRunId === startedRunId ? "workflow-2" : "workflow-1",
    },
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
