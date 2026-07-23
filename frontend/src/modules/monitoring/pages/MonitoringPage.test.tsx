import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MonitoringPage } from "./MonitoringPage";

type FetchCall = [string, RequestInit | undefined];

const endpointId = "endpoint-1";
const p95RuleId = "rule-p95";

describe("MonitoringPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("evaluates an alert rule against the selected endpoint", async () => {
    const fetchMock = mockMonitoringWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MonitoringPage />
      </QueryClientProvider>,
    );

    expect((await screen.findAllByText("Fraud Online")).length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("critical").length).toBeGreaterThan(0);
    expect(screen.getByText("Fraud p95 latency breach")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Evaluate rule" }));

    expect(
      await screen.findByText("Triggered Fraud p95 latency breach at 720.0ms."),
    ).toBeInTheDocument();
    const evaluateCall = findFetchCall(
      fetchMock,
      `/api/v1/alert-rules/${p95RuleId}/evaluate`,
      "POST",
    );
    expect(JSON.parse(String(evaluateCall[1]?.body))).toMatchObject({
      endpoint_id: endpointId,
    });
  });
});

function mockMonitoringWorkflow() {
  let events = [alertEvent("event-1", "open")];
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/monitoring/summary"
      ) {
        return jsonResponse({
          project_id: "project-1",
          inference_endpoint_count: 2,
          prediction_count: 2500,
          error_count: 140,
          request_count: 2500,
          active_alert_count: events.filter((event) => event.status === "open")
            .length,
          error_rate: 0.056,
          max_p95_latency_ms: 720,
        });
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
              error_count: 126,
              request_count: 1800,
              error_rate: 0.07,
              p50_latency_ms: 84,
              p95_latency_ms: 720,
            },
            {
              endpoint_id: "endpoint-2",
              endpoint_name: "Search Online",
              route_path: "/inference/search-online",
              status: "active",
              deployment_id: "deployment-2",
              deployment_revision_id: "revision-2",
              latest_window_seconds: 300,
              prediction_count: 700,
              error_count: 2,
              request_count: 700,
              error_rate: 0.0028,
              p50_latency_ms: 32,
              p95_latency_ms: 110,
            },
          ],
          next_cursor: null,
        });
      }

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/alert-rules"
      ) {
        return jsonResponse({
          items: [
            {
              id: p95RuleId,
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud p95 latency breach",
              slug: "fraud-p95-latency-breach",
              description: "Serving latency guardrail",
              severity: "critical",
              metric: "inference_p95_latency_ms",
              operator: "gt",
              threshold: 500,
              window_seconds: 300,
              enabled: true,
              created_by: "user-1",
            },
            {
              id: "rule-error-rate",
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud error rate breach",
              slug: "fraud-error-rate-breach",
              description: "Serving error guardrail",
              severity: "warning",
              metric: "inference_error_rate",
              operator: "gt",
              threshold: 0.05,
              window_seconds: 300,
              enabled: true,
              created_by: "user-1",
            },
          ],
          next_cursor: null,
        });
      }

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/alert-events"
      ) {
        return jsonResponse({ items: events, next_cursor: null });
      }

      if (
        method === "POST" &&
        path === `/api/v1/alert-rules/${p95RuleId}/evaluate`
      ) {
        const event = alertEvent("event-2", "open");
        events = [event];
        return jsonResponse({
          rule_id: p95RuleId,
          endpoint_id: endpointId,
          triggered: true,
          observed_value: 720,
          event,
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

function alertEvent(id: string, status: string): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    alert_rule_id: p95RuleId,
    endpoint_id: endpointId,
    severity: "critical",
    status,
    message: "Fraud p95 latency breach triggered for Fraud Online.",
    observed_value: 720,
    threshold: 500,
    metadata: {
      metric: "inference_p95_latency_ms",
      route_path: "/inference/fraud-online",
    },
    acknowledged_by: null,
    resolved_by: null,
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
