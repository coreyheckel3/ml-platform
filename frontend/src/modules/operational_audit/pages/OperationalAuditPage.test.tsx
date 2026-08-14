import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_EXPIRES_AT_KEY,
  TOKEN_TYPE_KEY,
} from "../../auth/session/sessionStore";
import { MemoryRouter } from "../../../shared/routing/router";
import { OperationalAuditPage } from "./OperationalAuditPage";

type FetchCall = [string, RequestInit | undefined];

describe("OperationalAuditPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("renders release evidence and live audit events as one filterable timeline", async () => {
    const fetchMock = mockAuditApi();
    seedSession();

    renderPage();

    expect(
      screen.getByRole("heading", { name: "Operational Audit" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Release manifest published").length).toBeGreaterThan(0);
    expect(await screen.findByText("Deployments - Rollback")).toBeInTheDocument();
    expect(screen.getByText("Retraining Runs - Trigger")).toBeInTheDocument();
    expect(screen.getByText("Auth - Login")).toBeInTheDocument();
    expect(screen.getByText("Live Audit Events")).toBeInTheDocument();

    const auditCall = findFetchCall(fetchMock, "/api/v1/admin/audit-log");
    expect(auditCall[1]?.headers).toMatchObject({
      authorization: "Bearer token-123",
    });

    fireEvent.click(screen.getByRole("button", { name: "Deployment 1" }));

    expect(screen.getAllByText("Deployments - Rollback").length).toBeGreaterThan(0);
    expect(screen.queryByText("Retraining Runs - Trigger")).not.toBeInTheDocument();
    expect(screen.getAllByText("deployment-1").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute(
      "href",
      "/deployments",
    );
  });

  it("keeps release evidence visible when the user is signed out", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    expect(screen.getAllByText("Release manifest published").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Sign in to load organization audit events/),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces an API failure without hiding release annotations", async () => {
    seedSession();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "audit unavailable" }, false)),
    );

    renderPage();

    expect(await screen.findByText(/Audit API request failed/)).toBeInTheDocument();
    expect(screen.getByText("Manifest verifier enforced")).toBeInTheDocument();
  });
});

function renderPage() {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter>
        <OperationalAuditPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function seedSession() {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, "token-123");
  window.localStorage.setItem(REFRESH_TOKEN_KEY, "refresh-token");
  window.localStorage.setItem(TOKEN_TYPE_KEY, "bearer");
  window.localStorage.setItem(
    TOKEN_EXPIRES_AT_KEY,
    new Date(Date.now() + 900_000).toISOString(),
  );
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function mockAuditApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (method === "GET" && path.startsWith("/api/v1/admin/audit-log")) {
      return jsonResponse({
        items: [
          auditEntry({
            id: "audit-deployment",
            action: "deployments.rollback",
            resourceType: "deployment",
            resourceId: "deployment-1",
            metadata: { project_id: "project-fraud", revision: 2 },
            createdAt: "2026-08-13T18:00:00Z",
          }),
          auditEntry({
            id: "audit-retraining",
            action: "retraining_runs.trigger",
            resourceType: "retraining_run",
            resourceId: "retraining-run-1",
            metadata: {
              project_id: "project-fraud",
              orchestrator_run_id: "workflow:fraud-retrain",
            },
            createdAt: "2026-08-13T17:55:00Z",
          }),
          auditEntry({
            id: "audit-login",
            action: "auth.login",
            resourceType: "user",
            resourceId: "user-1",
            metadata: { email: "corey@example.com" },
            createdAt: "2026-08-13T17:50:00Z",
          }),
        ],
        next_cursor: null,
      });
    }
    return jsonResponse({ detail: `unexpected request: ${method} ${path}` }, false);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function auditEntry({
  id,
  action,
  resourceType,
  resourceId,
  metadata,
  createdAt,
}: {
  id: string;
  action: string;
  resourceType: string;
  resourceId: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}) {
  return {
    id,
    organization_id: "org-1",
    actor_type: "user",
    actor_id: "user-1",
    action,
    resource_type: resourceType,
    resource_id: resourceId,
    metadata,
    created_at: createdAt,
  };
}

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    json: async () => body,
  } as Response;
}

function findFetchCall(
  fetchMock: ReturnType<typeof vi.fn>,
  fragment: string,
  method = "GET",
): FetchCall {
  const call = fetchMock.mock.calls.find(([input, init]) => {
    const requestMethod = init?.method ?? "GET";
    return String(input).includes(fragment) && requestMethod === method;
  });
  if (!call) {
    throw new Error(`Expected ${method} fetch call containing ${fragment}`);
  }
  return call as FetchCall;
}
