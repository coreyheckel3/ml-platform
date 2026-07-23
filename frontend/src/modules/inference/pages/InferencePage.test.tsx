import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InferencePage } from "./InferencePage";

type FetchCall = [string, RequestInit | undefined];

const deploymentId = "deployment-1";
const revisionId = "revision-1";
const endpointId = "endpoint-1";

describe("InferencePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates an endpoint, probes it, and records a metric snapshot", async () => {
    const fetchMock = mockInferenceWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <InferencePage />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("form", { name: "Create inference endpoint" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Fraud Scoring Endpoint" },
    });
    fireEvent.change(screen.getByLabelText("Route"), {
      target: { value: "/inference/fraud-scoring" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Payment risk online scoring" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create endpoint" }));

    expect(
      await screen.findByText("Created endpoint Fraud Scoring Endpoint."),
    ).toBeInTheDocument();
    const createCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/inference-endpoints",
      "POST",
    );
    expect(JSON.parse(String(createCall[1]?.body))).toMatchObject({
      deployment_id: deploymentId,
      deployment_revision_id: revisionId,
      name: "Fraud Scoring Endpoint",
      route_path: "/inference/fraud-scoring",
    });

    expect(
      await screen.findByRole("form", { name: "Probe inference endpoint" }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Probe endpoint" }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Probe endpoint" }));

    expect(
      await screen.findByText("Probe control-plane-probe succeeded in 17.5ms."),
    ).toBeInTheDocument();
    const probeCall = findFetchCall(
      fetchMock,
      `/api/v1/inference-endpoints/${endpointId}/predict`,
      "POST",
    );
    expect(JSON.parse(String(probeCall[1]?.body))).toMatchObject({
      request_id: "control-plane-probe",
      payload: {
        customer_tenure_days: 418,
        request_source: "control-plane-probe",
        amount: 128.45,
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "Record snapshot" }));
    expect(
      await screen.findByText("Recorded 300s snapshot for 1200 predictions."),
    ).toBeInTheDocument();
    const snapshotCall = findFetchCall(
      fetchMock,
      `/api/v1/inference-endpoints/${endpointId}/metric-snapshots`,
      "POST",
    );
    expect(JSON.parse(String(snapshotCall[1]?.body))).toMatchObject({
      window_seconds: 300,
      prediction_count: 1200,
      error_count: 3,
      p50_latency_ms: 42,
      p95_latency_ms: 138,
    });
  });
});

function mockInferenceWorkflow() {
  let endpoints: Array<Record<string, unknown>> = [];
  let requestLogs: Array<Record<string, unknown>> = [];
  let snapshots: Array<Record<string, unknown>> = [];
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/deployments"
      ) {
        return jsonResponse({
          items: [
            {
              id: deploymentId,
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

      if (
        method === "GET" &&
        path === `/api/v1/deployments/${deploymentId}/revisions`
      ) {
        return jsonResponse({
          items: [
            {
              id: revisionId,
              deployment_id: deploymentId,
              model_version_id: "model-version-1",
              revision: 7,
              serving_image: "ghcr.io/forgeml/serving-runtime:latest",
              runtime_config: {},
              traffic_percentage: 100,
              status: "healthy",
              orchestrator_deployment_id: "local-serving-7",
              created_by: "user-1",
            },
          ],
          next_cursor: null,
        });
      }

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/inference-endpoints"
      ) {
        return jsonResponse({ items: endpoints, next_cursor: null });
      }

      if (
        method === "GET" &&
        path === `/api/v1/inference-endpoints/${endpointId}/requests`
      ) {
        return jsonResponse({ items: requestLogs, next_cursor: null });
      }

      if (
        method === "GET" &&
        path === `/api/v1/inference-endpoints/${endpointId}/metric-snapshots`
      ) {
        return jsonResponse({ items: snapshots, next_cursor: null });
      }

      if (
        method === "POST" &&
        path === "/api/v1/projects/project-1/inference-endpoints"
      ) {
        const endpoint = {
          id: endpointId,
          organization_id: "org-1",
          project_id: "project-1",
          deployment_id: deploymentId,
          deployment_revision_id: revisionId,
          name: "Fraud Scoring Endpoint",
          slug: "fraud-scoring-endpoint",
          route_path: "/inference/fraud-scoring",
          description: "Payment risk online scoring",
          status: "active",
          created_by: "user-1",
        };
        endpoints = [endpoint];
        return jsonResponse(endpoint);
      }

      if (
        method === "POST" &&
        path === `/api/v1/inference-endpoints/${endpointId}/predict`
      ) {
        const response = {
          log_id: "request-log-1",
          endpoint_id: endpointId,
          deployment_revision_id: revisionId,
          request_id: "control-plane-probe",
          status: "succeeded",
          latency_ms: 17.5,
          output_payload: {
            prediction: 0.82,
            model_version_id: "model-version-1",
          },
        };
        requestLogs = [
          {
            id: "request-log-1",
            endpoint_id: endpointId,
            deployment_revision_id: revisionId,
            request_id: "control-plane-probe",
            status: "succeeded",
            latency_ms: 17.5,
            input_payload: {},
            output_payload: response.output_payload,
            error_message: null,
          },
        ];
        return jsonResponse(response);
      }

      if (
        method === "POST" &&
        path === `/api/v1/inference-endpoints/${endpointId}/metric-snapshots`
      ) {
        const snapshot = {
          id: "snapshot-1",
          endpoint_id: endpointId,
          window_seconds: 300,
          prediction_count: 1200,
          error_count: 3,
          p50_latency_ms: 42,
          p95_latency_ms: 138,
        };
        snapshots = [snapshot];
        return jsonResponse(snapshot);
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
