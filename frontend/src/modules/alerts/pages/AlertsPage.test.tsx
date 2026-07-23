import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AlertsPage } from "./AlertsPage";

type FetchCall = [string, RequestInit | undefined];

const eventId = "event-1";

describe("AlertsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates an alert rule and handles alert event lifecycle actions", async () => {
    const fetchMock = mockAlertWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AlertsPage />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText("Fraud p95 latency breach triggered."),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Rule" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Fraud error budget" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Error-rate guardrail" },
    });
    fireEvent.change(screen.getByLabelText("Metric"), {
      target: { value: "inference_error_rate" },
    });
    fireEvent.change(screen.getByLabelText("Threshold"), {
      target: { value: "0.04" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create rule" }));

    expect(
      await screen.findByText("Created alert rule Fraud error budget."),
    ).toBeInTheDocument();
    const createCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/alert-rules",
      "POST",
    );
    expect(JSON.parse(String(createCall[1]?.body))).toMatchObject({
      name: "Fraud error budget",
      description: "Error-rate guardrail",
      metric: "inference_error_rate",
      operator: "gt",
      threshold: 0.04,
      window_seconds: 300,
      enabled: true,
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Acknowledge alert event-1" }),
    );
    expect(
      await screen.findByText("Acknowledged alert event-1."),
    ).toBeInTheDocument();
    expect(
      findFetchCall(
        fetchMock,
        `/api/v1/alert-events/${eventId}/acknowledge`,
        "POST",
      ),
    ).toBeTruthy();
    expect(await screen.findByText("acknowledged")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Resolve alert event-1" }),
    );
    expect(
      await screen.findByText("Resolved alert event-1."),
    ).toBeInTheDocument();
    expect(
      findFetchCall(
        fetchMock,
        `/api/v1/alert-events/${eventId}/resolve`,
        "POST",
      ),
    ).toBeTruthy();
    expect(await screen.findByText("resolved")).toBeInTheDocument();
  });
});

function mockAlertWorkflow() {
  let rules: Array<Record<string, unknown>> = [];
  let events = [alertEvent("open")];
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/alert-rules"
      ) {
        return jsonResponse({ items: rules, next_cursor: null });
      }

      if (
        method === "GET" &&
        path === "/api/v1/projects/project-1/alert-events"
      ) {
        return jsonResponse({ items: events, next_cursor: null });
      }

      if (
        method === "POST" &&
        path === "/api/v1/projects/project-1/alert-rules"
      ) {
        const rule = {
          id: "rule-1",
          organization_id: "org-1",
          project_id: "project-1",
          name: "Fraud error budget",
          slug: "fraud-error-budget",
          description: "Error-rate guardrail",
          severity: "warning",
          metric: "inference_error_rate",
          operator: "gt",
          threshold: 0.04,
          window_seconds: 300,
          enabled: true,
          created_by: "user-1",
        };
        rules = [rule];
        return jsonResponse(rule);
      }

      if (
        method === "POST" &&
        path === `/api/v1/alert-events/${eventId}/acknowledge`
      ) {
        const event = alertEvent("acknowledged");
        events = [event];
        return jsonResponse(event);
      }

      if (
        method === "POST" &&
        path === `/api/v1/alert-events/${eventId}/resolve`
      ) {
        const event = alertEvent("resolved");
        events = [event];
        return jsonResponse(event);
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

function alertEvent(status: string): Record<string, unknown> {
  return {
    id: eventId,
    organization_id: "org-1",
    project_id: "project-1",
    alert_rule_id: "rule-p95",
    endpoint_id: "endpoint-1",
    severity: "critical",
    status,
    message: "Fraud p95 latency breach triggered.",
    observed_value: 720,
    threshold: 500,
    metadata: {
      metric: "inference_p95_latency_ms",
      route_path: "/inference/fraud-online",
    },
    acknowledged_by: status === "acknowledged" ? "user-1" : null,
    resolved_by: status === "resolved" ? "user-1" : null,
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
