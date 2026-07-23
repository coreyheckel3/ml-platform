import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExperimentsPage } from "./ExperimentsPage";

type FetchCall = [string, RequestInit | undefined];

const initialExperimentId = "experiment-1";
const createdExperimentId = "experiment-2";
const initialRunId = "run-1";
const startedRunId = "run-2";

describe("ExperimentsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates experiments, starts runs, logs tracking data, and completes runs", async () => {
    const fetchMock = mockExperimentWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ExperimentsPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Fraud Experiment")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Experiment" }));
    fireEvent.change(screen.getByLabelText("Experiment Name"), {
      target: { value: "Fraud Offline Evaluation" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Weekly fraud model comparison." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create experiment" }));

    expect(
      await screen.findByText("Created experiment Fraud Offline Evaluation."),
    ).toBeInTheDocument();
    const createCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/experiments",
      "POST",
    );
    expect(JSON.parse(String(createCall[1]?.body))).toMatchObject({
      name: "Fraud Offline Evaluation",
      description: "Weekly fraud model comparison.",
    });

    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Start run" })).not.toBeDisabled(),
    );
    fireEvent.change(screen.getByLabelText("Run Name"), {
      target: { value: "fraud-xgb-depth-8" },
    });
    fireEvent.change(screen.getByLabelText("Model Type"), {
      target: { value: "xgboost" },
    });
    fireEvent.change(screen.getByLabelText("Artifact URI"), {
      target: { value: "s3://forgeml/experiments/fraud-xgb-depth-8" },
    });
    fireEvent.change(screen.getByLabelText("Parameters"), {
      target: { value: JSON.stringify({ max_depth: 8, learning_rate: 0.05 }) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start run" }));

    expect(
      await screen.findByText(`Started experiment run ${startedRunId}.`),
    ).toBeInTheDocument();
    const startCall = findFetchCall(
      fetchMock,
      `/api/v1/experiments/${createdExperimentId}/runs`,
      "POST",
    );
    expect(JSON.parse(String(startCall[1]?.body))).toMatchObject({
      run_name: "fraud-xgb-depth-8",
      model_type: "xgboost",
      artifact_uri: "s3://forgeml/experiments/fraud-xgb-depth-8",
      dataset_version_id: "dataset-version-1",
      feature_set_id: null,
      parameters: { max_depth: 8, learning_rate: 0.05 },
    });

    expect((await screen.findAllByText("fraud-xgb-depth-8")).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Metrics"), {
      target: { value: JSON.stringify({ auc: 0.951, log_loss: 0.16 }) },
    });
    fireEvent.change(screen.getByLabelText("Evaluation Report"), {
      target: {
        value: JSON.stringify({
          validation: { slice_count: 8, passed: true },
        }),
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Log metrics" }));

    expect(
      await screen.findByText("Logged metrics for fraud-xgb-depth-8."),
    ).toBeInTheDocument();
    const metricCall = findFetchCall(
      fetchMock,
      `/api/v1/experiment-runs/${startedRunId}/metrics`,
      "POST",
    );
    expect(JSON.parse(String(metricCall[1]?.body))).toMatchObject({
      metrics: { auc: 0.951, log_loss: 0.16 },
      evaluation_report: {
        validation: { slice_count: 8, passed: true },
      },
    });

    fireEvent.change(screen.getByLabelText("Artifact Name"), {
      target: { value: "fraud-model-card" },
    });
    fireEvent.change(screen.getByLabelText("Artifact Type"), {
      target: { value: "model_card" },
    });
    fireEvent.change(screen.getByLabelText("Artifact URI"), {
      target: {
        value: "s3://forgeml/experiments/fraud-xgb-depth-8/model-card.json",
      },
    });
    fireEvent.change(screen.getByLabelText("Metadata"), {
      target: { value: JSON.stringify({ stage: "offline", owner: "risk" }) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Log artifact" }));

    expect(await screen.findByText("Logged artifact fraud-model-card.")).toBeInTheDocument();
    const artifactCall = findFetchCall(
      fetchMock,
      `/api/v1/experiment-runs/${startedRunId}/artifacts`,
      "POST",
    );
    expect(JSON.parse(String(artifactCall[1]?.body))).toMatchObject({
      name: "fraud-model-card",
      artifact_type: "model_card",
      uri: "s3://forgeml/experiments/fraud-xgb-depth-8/model-card.json",
      metadata: { stage: "offline", owner: "risk" },
    });
    expect(await screen.findByText("fraud-model-card")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Complete run" }));
    expect(
      await screen.findByText("Completed fraud-xgb-depth-8 as succeeded."),
    ).toBeInTheDocument();
    const completeCall = findFetchCall(
      fetchMock,
      `/api/v1/experiment-runs/${startedRunId}/complete`,
      "POST",
    );
    expect(JSON.parse(String(completeCall[1]?.body))).toMatchObject({
      status: "succeeded",
      metrics: { auc: 0.951, log_loss: 0.16 },
      evaluation_report: {
        validation: { slice_count: 8, passed: true },
      },
      error_message: null,
    });
  });
});

function mockExperimentWorkflow() {
  let experiments = [
    experiment(initialExperimentId, "Fraud Experiment", "fraud-experiment"),
  ];
  const runsByExperiment: Record<string, Array<Record<string, unknown>>> = {
    [initialExperimentId]: [experimentRun(initialRunId, initialExperimentId, "running", {})],
  };
  const artifactsByRun: Record<string, Array<Record<string, unknown>>> = {
    [initialRunId]: [],
  };
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (method === "GET" && path === "/api/v1/projects/project-1/experiments") {
        return jsonResponse({ items: experiments, next_cursor: null });
      }

      if (method === "POST" && path === "/api/v1/projects/project-1/experiments") {
        const created = experiment(
          createdExperimentId,
          "Fraud Offline Evaluation",
          "fraud-offline-evaluation",
          "Weekly fraud model comparison.",
        );
        experiments = [created, ...experiments];
        runsByExperiment[createdExperimentId] = [];
        return jsonResponse(created);
      }

      if (method === "GET" && path.startsWith("/api/v1/experiments/")) {
        const experimentId = path.split("/api/v1/experiments/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: runsByExperiment[experimentId] ?? [],
          next_cursor: null,
        });
      }

      if (
        method === "POST" &&
        path === `/api/v1/experiments/${createdExperimentId}/runs`
      ) {
        const started = experimentRun(
          startedRunId,
          createdExperimentId,
          "running",
          {},
          "fraud-xgb-depth-8",
        );
        runsByExperiment[createdExperimentId] = [
          started,
          ...(runsByExperiment[createdExperimentId] ?? []),
        ];
        artifactsByRun[startedRunId] = [];
        return jsonResponse(started);
      }

      if (method === "POST" && path === `/api/v1/experiment-runs/${startedRunId}/metrics`) {
        const updated = experimentRun(
          startedRunId,
          createdExperimentId,
          "running",
          { auc: 0.951, log_loss: 0.16 },
          "fraud-xgb-depth-8",
          { validation: { slice_count: 8, passed: true } },
        );
        runsByExperiment[createdExperimentId] = runsByExperiment[createdExperimentId].map(
          (run) => (run.id === startedRunId ? updated : run),
        );
        return jsonResponse(updated);
      }

      if (method === "POST" && path === `/api/v1/experiment-runs/${startedRunId}/artifacts`) {
        const created = {
          id: "artifact-1",
          experiment_run_id: startedRunId,
          name: "fraud-model-card",
          artifact_type: "model_card",
          uri: "s3://forgeml/experiments/fraud-xgb-depth-8/model-card.json",
          metadata: { stage: "offline", owner: "risk" },
        };
        artifactsByRun[startedRunId] = [created, ...(artifactsByRun[startedRunId] ?? [])];
        return jsonResponse(created);
      }

      if (method === "GET" && path.startsWith("/api/v1/experiment-runs/")) {
        const runId = path.split("/api/v1/experiment-runs/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: artifactsByRun[runId] ?? [],
          next_cursor: null,
        });
      }

      if (method === "POST" && path === `/api/v1/experiment-runs/${startedRunId}/complete`) {
        const completed = experimentRun(
          startedRunId,
          createdExperimentId,
          "succeeded",
          { auc: 0.951, log_loss: 0.16 },
          "fraud-xgb-depth-8",
          { validation: { slice_count: 8, passed: true } },
        );
        runsByExperiment[createdExperimentId] = runsByExperiment[createdExperimentId].map(
          (run) => (run.id === startedRunId ? completed : run),
        );
        return jsonResponse(completed);
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
              description: "Validated fraud labels",
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
              version: 4,
              object_uri: "s3://forgeml/datasets/fraud/v4.csv",
              content_hash: "sha256:abc123",
              row_count: 14000,
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

      return jsonResponse(
        { detail: `unexpected request: ${method} ${path}` },
        false,
      );
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function experiment(
  id: string,
  name: string,
  slug: string,
  description = "Fraud model training",
): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    name,
    slug,
    description,
    owner_user_id: "user-1",
    status: "active",
  };
}

function experimentRun(
  id: string,
  experimentId: string,
  status: string,
  metrics: Record<string, number>,
  runName = "fraud-baseline-run",
  evaluationReport: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    id,
    experiment_id: experimentId,
    project_id: "project-1",
    run_name: runName,
    status,
    model_type: "xgboost",
    started_by: "user-1",
    dataset_version_id: "dataset-version-1",
    feature_set_id: null,
    parameters: { max_depth: 6 },
    metrics,
    artifact_uri: `s3://forgeml/experiments/${id}`,
    evaluation_report: evaluationReport,
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
    return String(input).includes(fragment) && (init?.method ?? "GET") === method;
  });
  if (!call) {
    throw new Error(`Expected ${method} fetch call containing ${fragment}`);
  }
  return call as FetchCall;
}
