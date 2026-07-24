import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACCESS_TOKEN_KEY,
  PROJECT_CONTEXT_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_EXPIRES_AT_KEY,
  TOKEN_TYPE_KEY,
} from "../../modules/auth/session/sessionStore";
import { Shell } from "./Shell";

type FetchCall = [string, RequestInit | undefined];

describe("Shell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("loads the current principal and clears auth state on sign out", async () => {
    const fetchMock = mockAuthWorkflow();
    seedSession();

    render(
      <QueryClientProvider client={createQueryClient()}>
        <MemoryRouter>
          <Shell>
            <h1>Workspace</h1>
          </Shell>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("ml.engineer@example.com")).toBeInTheDocument();
    const currentUserCall = findFetchCall(fetchMock, "/api/v1/auth/me");
    expect(currentUserCall[1]?.headers).toMatchObject({
      authorization: "Bearer access-token",
    });

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(window.localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    });
    const logoutCall = findFetchCall(fetchMock, "/api/v1/auth/logout", "POST");
    expect(JSON.parse(String(logoutCall[1]?.body))).toMatchObject({
      refresh_token: "refresh-token",
    });
    expect(window.localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
    expect(window.localStorage.getItem(PROJECT_CONTEXT_KEY)).toBeNull();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("rotates an expired access token through the refresh endpoint", async () => {
    const fetchMock = mockAuthWorkflow();
    seedSession(new Date(Date.now() - 1_000).toISOString());

    render(
      <QueryClientProvider client={createQueryClient()}>
        <MemoryRouter>
          <Shell>
            <h1>Workspace</h1>
          </Shell>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(window.localStorage.getItem(ACCESS_TOKEN_KEY)).toBe("rotated-access-token");
    });
    const refreshCall = findFetchCall(fetchMock, "/api/v1/auth/refresh", "POST");
    expect(JSON.parse(String(refreshCall[1]?.body))).toMatchObject({
      refresh_token: "refresh-token",
    });
  });
});

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function seedSession(expiresAt = new Date(Date.now() + 900_000).toISOString()) {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, "access-token");
  window.localStorage.setItem(REFRESH_TOKEN_KEY, "refresh-token");
  window.localStorage.setItem(TOKEN_TYPE_KEY, "bearer");
  window.localStorage.setItem(TOKEN_EXPIRES_AT_KEY, expiresAt);
  window.localStorage.setItem(PROJECT_CONTEXT_KEY, "project-1");
}

function mockAuthWorkflow() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    const method = init?.method ?? "GET";

    if (method === "GET" && path === "/api/v1/auth/me") {
      return jsonResponse({
        id: "user-1",
        email: "ml.engineer@example.com",
        organization_id: "org-1",
        permissions: ["projects:read"],
      });
    }

    if (method === "POST" && path === "/api/v1/auth/refresh") {
      return jsonResponse({
        access_token: "rotated-access-token",
        refresh_token: "rotated-refresh-token",
        token_type: "bearer",
        expires_in: 900,
      });
    }

    if (method === "POST" && path === "/api/v1/auth/logout") {
      return jsonResponse({ revoked: true });
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
