import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACCESS_TOKEN_KEY,
  PROJECT_CONTEXT_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_EXPIRES_AT_KEY,
  TOKEN_TYPE_KEY,
} from "../../auth/session/sessionStore";
import { SettingsPage } from "./SettingsPage";

type FetchCall = [string, RequestInit | undefined];

describe("SettingsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads authenticated account context and clears project context", async () => {
    const fetchMock = mockCurrentUser();
    seedSession();

    render(
      <QueryClientProvider client={createQueryClient()}>
        <SettingsPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("corey@example.com")).toBeInTheDocument();
    expect(screen.getAllByText("org-1").length).toBeGreaterThan(0);
    expect(screen.getByText("projects:read")).toBeInTheDocument();
    expect(screen.getByText("model_versions:approve")).toBeInTheDocument();
    expect(screen.getByText("admin:audit_log:read")).toBeInTheDocument();
    expect(await screen.findByText("model_versions.review")).toBeInTheDocument();
    expect(screen.getByText("decision: approved")).toBeInTheDocument();
    expect(screen.getAllByText("project-1").length).toBeGreaterThan(0);
    const authCall = findFetchCall(fetchMock, "/api/v1/auth/me");
    expect(authCall[1]?.headers).toMatchObject({
      authorization: "Bearer token-123",
    });
    const auditCall = findFetchCall(fetchMock, "/api/v1/admin/audit-log");
    expect(auditCall[1]?.headers).toMatchObject({
      authorization: "Bearer token-123",
    });

    fireEvent.change(screen.getByLabelText("Action"), {
      target: { value: "deployments.rollback" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(await screen.findByText("deployments.rollback")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes("action=deployments.rollback"),
        ),
      ).toBe(true);
    });

    fireEvent.click(screen.getByRole("button", { name: "Clear project context" }));

    expect(screen.getByText("Cleared active project context for this browser.")).toBeInTheDocument();
    expect(window.localStorage.getItem(PROJECT_CONTEXT_KEY)).toBeNull();
  });

  it("does not request account context without an API token", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={createQueryClient()}>
        <SettingsPage />
      </QueryClientProvider>,
    );

    expect(screen.getByText("No API token is configured for this browser.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function seedSession() {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, "token-123");
  window.localStorage.setItem(REFRESH_TOKEN_KEY, "refresh-token");
  window.localStorage.setItem(TOKEN_TYPE_KEY, "bearer");
  window.localStorage.setItem(
    TOKEN_EXPIRES_AT_KEY,
    new Date(Date.now() + 900_000).toISOString(),
  );
  window.localStorage.setItem(PROJECT_CONTEXT_KEY, "project-1");
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function mockCurrentUser() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    const method = init?.method ?? "GET";

    if (method === "GET" && path === "/api/v1/auth/me") {
      return jsonResponse({
        id: "user-1",
        email: "corey@example.com",
        organization_id: "org-1",
        permissions: [
          "projects:read",
          "projects:create",
          "model_versions:approve",
          "deployments:release",
          "admin:audit_log:read",
        ],
      });
    }

    if (method === "GET" && path.startsWith("/api/v1/admin/audit-log")) {
      const query = new URL(`http://forgeml.local${path}`).searchParams;
      const action = query.get("action") || "model_versions.review";
      return jsonResponse({
        items: [
          {
            id: `audit-${action}`,
            organization_id: "org-1",
            actor_type: "user",
            actor_id: "user-1",
            action,
            resource_type: action === "deployments.rollback" ? "deployment" : "model_version",
            resource_id: action === "deployments.rollback" ? "deployment-1" : "model-version-1",
            metadata: action === "deployments.rollback" ? { revision: 2 } : { decision: "approved" },
            created_at: "2026-07-26T12:30:00+00:00",
          },
        ],
        next_cursor: null,
      });
    }

    return jsonResponse({ detail: `unexpected request: ${method} ${path}` }, false);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
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
