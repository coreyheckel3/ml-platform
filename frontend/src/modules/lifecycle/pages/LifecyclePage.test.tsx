import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACCESS_TOKEN_KEY,
  PROJECT_CONTEXT_KEY,
} from "../../auth/session/sessionStore";
import { MemoryRouter } from "../../../shared/routing/router";
import { LifecyclePage } from "./LifecyclePage";

describe("LifecyclePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("renders project lifecycle readiness from the API", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      expect(String(input)).toBe("/api/v1/projects/project-1/lifecycle/summary");
      return jsonResponse({
        schema_version: "forgeml.project_lifecycle.v1",
        project_id: "project-1",
        project_name: "Fraud Detection",
        project_slug: "fraud-detection",
        project_status: "active",
        readiness_score: 80,
        ready_stage_count: 8,
        total_stage_count: 10,
        generated_at: "2026-08-14T18:00:00Z",
        stages: [
          lifecycleStage({
            key: "datasets",
            title: "Datasets",
            status: "ready",
            primarySignal: "2 versions, 2 validation runs",
            routePath: "/datasets",
          }),
          lifecycleStage({
            key: "model_registry",
            title: "Model Registry",
            status: "needs_attention",
            primarySignal: "1 versions, 0 approved",
            routePath: "/models",
          }),
        ],
        dependencies: [
          {
            source_stage: "datasets",
            target_stage: "model_registry",
            status: "connected",
            detail: "Datasets feeds Model Registry.",
          },
        ],
        metrics: [
          {
            label: "Predictions",
            value: "1200",
            detail: "0.33% error rate",
            tone: "success",
          },
          {
            label: "Drift Breaches",
            value: "1",
            detail: "2 reports",
            tone: "warning",
          },
        ],
        recommended_actions: ["Request or complete approval for a model version."],
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.setItem(ACCESS_TOKEN_KEY, "token-123");
    window.localStorage.setItem(PROJECT_CONTEXT_KEY, "project-1");

    renderPage();

    expect(screen.getByRole("heading", { name: "Lifecycle" })).toBeInTheDocument();
    expect(await screen.findByText("80%")).toBeInTheDocument();
    expect(screen.getByText("Fraud Detection")).toBeInTheDocument();
    expect(screen.getByText("Stage Readiness")).toBeInTheDocument();
    expect(screen.getAllByText("Model Registry").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Request or complete approval for a model version."),
    ).toBeInTheDocument();
    expect(screen.getByText("Dependency Map")).toBeInTheDocument();
    expect(screen.getByText("Project Signals")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open" })[0]).toHaveAttribute(
      "href",
      "/datasets",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/projects/project-1/lifecycle/summary",
      expect.objectContaining({
        headers: expect.objectContaining({
          authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("does not call the API without signed-in project context", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    expect(screen.getByRole("heading", { name: "Lifecycle" })).toBeInTheDocument();
    expect(
      screen.getByText(/Sign in to load lifecycle readiness/),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LifecyclePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function lifecycleStage({
  key,
  title,
  status,
  primarySignal,
  routePath,
}: {
  key: string;
  title: string;
  status: string;
  primarySignal: string;
  routePath: string;
}) {
  return {
    key,
    title,
    status,
    description: `${title} description.`,
    primary_signal: primarySignal,
    count: 1,
    last_updated_at: "2026-08-14T18:00:00Z",
    route_path: routePath,
    recommended_action: `${title} action.`,
  };
}

function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    json: async () => body,
  } as Response;
}
