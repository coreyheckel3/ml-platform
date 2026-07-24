import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_EXPIRES_AT_KEY,
  TOKEN_TYPE_KEY,
} from "../session/sessionStore";
import { LoginPage } from "./LoginPage";

type FetchCall = [string, RequestInit | undefined];

describe("LoginPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("exchanges credentials, stores the session, and follows the redirect", async () => {
    const fetchMock = mockLoginResponse(true);

    renderLoginPage("/login?redirect=/projects");

    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "forgeml-local-admin" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Projects Landing" })).toBeInTheDocument();
    expect(window.localStorage.getItem(ACCESS_TOKEN_KEY)).toBe("access-token");
    expect(window.localStorage.getItem(REFRESH_TOKEN_KEY)).toBe("refresh-token");
    expect(window.localStorage.getItem(TOKEN_TYPE_KEY)).toBe("bearer");
    expect(window.localStorage.getItem(TOKEN_EXPIRES_AT_KEY)).toBeTruthy();
    const loginCall = findFetchCall(fetchMock, "/api/v1/auth/login", "POST");
    expect(JSON.parse(String(loginCall[1]?.body))).toMatchObject({
      email: "admin@forgeml.dev",
      password: "forgeml-local-admin",
    });
  });

  it("surfaces login failures without writing tokens", async () => {
    mockLoginResponse(false);

    renderLoginPage("/login");

    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "incorrect-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("ForgeML API request failed with 401")).toBeInTheDocument();
    expect(window.localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    expect(window.localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
  });
});

function renderLoginPage(initialEntry: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/projects" element={<h1>Projects Landing</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockLoginResponse(ok: boolean) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    const method = init?.method ?? "GET";

    if (method === "POST" && path === "/api/v1/auth/login") {
      return jsonResponse(
        {
          access_token: "access-token",
          refresh_token: "refresh-token",
          token_type: "bearer",
          expires_in: 900,
        },
        ok,
        ok ? 200 : 401,
      );
    }

    return jsonResponse({ detail: `unexpected request: ${method} ${path}` }, false, 500);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
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
