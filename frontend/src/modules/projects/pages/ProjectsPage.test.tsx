import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectsPage } from "./ProjectsPage";

type FetchCall = [string, RequestInit | undefined];

describe("ProjectsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates a browser-scoped project from the New action", async () => {
    const queryClient = createQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ProjectsPage />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Audience Forecasting" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Demand planning models" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create project" }));

    expect(await screen.findByText("Created and selected Audience Forecasting.")).toBeInTheDocument();
    expect(screen.getAllByText("Audience Forecasting").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Demand planning models").length).toBeGreaterThan(0);
    expect(screen.queryByRole("form", { name: "Create project" })).not.toBeInTheDocument();
    expect(window.localStorage.getItem("forgeml_project_id")).toBeTruthy();
  });

  it("loads API projects, switches project context, and creates a project", async () => {
    const fetchMock = mockProjectWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    const queryClient = createQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ProjectsPage />
      </QueryClientProvider>,
    );

    expect((await screen.findAllByText("Fraud Detection")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Select project Fraud Detection" }));
    await waitFor(() => {
      expect(window.localStorage.getItem("forgeml_project_id")).toBe("project-1");
    });
    expect(screen.getByText("Selected Fraud Detection as the active project.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Churn Forecasting" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Retention models" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create project" }));

    expect(await screen.findByText("Created and selected Churn Forecasting.")).toBeInTheDocument();
    await waitFor(() => {
      expect(window.localStorage.getItem("forgeml_project_id")).toBe("project-2");
    });
    const createCall = findFetchCall(fetchMock, "/api/v1/projects", "POST");
    expect(createCall[1]?.headers).toMatchObject({
      authorization: "Bearer token-123",
    });
    expect(JSON.parse(String(createCall[1]?.body))).toMatchObject({
      name: "Churn Forecasting",
      description: "Retention models",
    });
  });
});

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function mockProjectWorkflow() {
  let projects = [
    project("project-1", "Fraud Detection", "fraud-detection", "Payment risk scoring"),
  ];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    const method = init?.method ?? "GET";

    if (method === "GET" && path === "/api/v1/projects") {
      return jsonResponse({ items: projects, next_cursor: null });
    }

    if (method === "POST" && path === "/api/v1/projects") {
      const created = project(
        "project-2",
        "Churn Forecasting",
        "churn-forecasting",
        "Retention models",
      );
      projects = [created, ...projects];
      return jsonResponse(created);
    }

    return jsonResponse({ detail: `unexpected request: ${method} ${path}` }, false);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function project(
  id: string,
  name: string,
  slug: string,
  description: string,
): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    name,
    slug,
    description,
    status: "active",
    owner_user_id: "user-1",
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
