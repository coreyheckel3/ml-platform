import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./SettingsPage";

type FetchCall = [string, RequestInit | undefined];

describe("SettingsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads authenticated account context and clears project context", async () => {
    const fetchMock = mockCurrentUser();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");

    render(
      <QueryClientProvider client={createQueryClient()}>
        <SettingsPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("corey@example.com")).toBeInTheDocument();
    expect(screen.getAllByText("org-1").length).toBeGreaterThan(0);
    expect(screen.getByText("projects:read")).toBeInTheDocument();
    expect(screen.getByText("model_versions:approve")).toBeInTheDocument();
    expect(screen.getAllByText("project-1").length).toBeGreaterThan(0);
    const authCall = findFetchCall(fetchMock, "/api/v1/auth/me");
    expect(authCall[1]?.headers).toMatchObject({
      authorization: "Bearer token-123",
    });

    fireEvent.click(screen.getByRole("button", { name: "Clear project context" }));

    expect(screen.getByText("Cleared active project context for this browser.")).toBeInTheDocument();
    expect(window.localStorage.getItem("forgeml_project_id")).toBeNull();
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
        ],
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
