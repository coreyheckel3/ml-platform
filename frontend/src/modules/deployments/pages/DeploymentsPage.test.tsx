import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DeploymentsPage } from "./DeploymentsPage";

type FetchCall = [string, RequestInit | undefined];

const deploymentId = "deployment-1";
const modelId = "model-1";
const approvedVersionId = "model-version-2";

describe("DeploymentsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates a release revision, records health, and promotes traffic", async () => {
    const fetchMock = mockDeploymentWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DeploymentsPage />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("form", { name: "Create deployment revision" }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Create revision" }),
      ).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Create revision" }));

    expect(await screen.findByText("Created revision 2.")).toBeInTheDocument();
    const revisionCall = findFetchCall(
      fetchMock,
      `/api/v1/deployments/${deploymentId}/revisions`,
      "POST",
    );
    expect(JSON.parse(String(revisionCall[1]?.body))).toMatchObject({
      model_version_id: approvedVersionId,
      serving_image: "ghcr.io/forgeml/serving-runtime:latest",
      traffic_percentage: 10,
      runtime_config: {
        resources: {
          cpu: "500m",
          memory: "1Gi",
        },
      },
    });

    fireEvent.click(
      await screen.findByRole("button", { name: "Mark revision 2 healthy" }),
    );
    expect(
      await screen.findByText("Revision 2 health recorded."),
    ).toBeInTheDocument();
    const healthCall = findFetchCall(
      fetchMock,
      "/deployment-revisions/revision-2/health-checks",
      "POST",
    );
    expect(JSON.parse(String(healthCall[1]?.body))).toMatchObject({
      status: "healthy",
      latency_ms: 85,
      error_rate: 0.01,
    });

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Promote revision 2 to full traffic",
      }),
    );
    expect(
      await screen.findByText("Revision 2 traffic is 100%."),
    ).toBeInTheDocument();
    const trafficCall = findFetchCall(
      fetchMock,
      "/deployment-revisions/revision-2/traffic",
      "POST",
    );
    expect(JSON.parse(String(trafficCall[1]?.body))).toMatchObject({
      traffic_percentage: 100,
    });
  });
});

function mockDeploymentWorkflow() {
  let revisions = [
    deploymentRevision({
      id: "revision-1",
      revision: 1,
      status: "healthy",
      traffic: 100,
    }),
  ];
  let events = [
    deploymentEvent(
      "event-1",
      "created",
      "Deployment target was created.",
      null,
    ),
  ];
  const healthChecksByRevision: Record<
    string,
    Array<Record<string, unknown>>
  > = {
    "revision-1": [healthCheck("health-1", "revision-1", "healthy")],
  };
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
        return jsonResponse({ items: revisions, next_cursor: null });
      }

      if (
        method === "GET" &&
        path === `/api/v1/deployments/${deploymentId}/events`
      ) {
        return jsonResponse({ items: events, next_cursor: null });
      }

      if (method === "GET" && path === "/api/v1/projects/project-1/models") {
        return jsonResponse({
          items: [
            {
              id: modelId,
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud Risk XGB",
              slug: "fraud-risk-xgb",
              description: "Payment risk scoring",
              task_type: "classification",
              owner_user_id: "user-1",
              status: "active",
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === `/api/v1/models/${modelId}/versions`) {
        return jsonResponse({
          items: [
            {
              id: approvedVersionId,
              registered_model_id: modelId,
              version: 2,
              training_run_id: "training-run-2",
              experiment_run_id: "experiment-run-2",
              artifact_uri: "s3://forgeml/models/fraud-risk-xgb/2/model.json",
              model_format: "xgboost-booster",
              signature: { inputs: [], outputs: [] },
              metrics: { auc: 0.947 },
              status: "approved",
              created_by: "user-1",
            },
          ],
          next_cursor: null,
        });
      }

      if (method === "GET" && path.includes("/health-checks")) {
        const revisionId =
          path.split("/deployment-revisions/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: healthChecksByRevision[revisionId] ?? [],
          next_cursor: null,
        });
      }

      if (
        method === "POST" &&
        path === `/api/v1/deployments/${deploymentId}/revisions`
      ) {
        const created = deploymentRevision({
          id: "revision-2",
          revision: 2,
          status: "deploying",
          traffic: 10,
        });
        revisions = [created, ...revisions];
        events = [
          deploymentEvent(
            "event-2",
            "revision_created",
            "Deployment revision was submitted.",
            "revision-2",
          ),
          ...events,
        ];
        return jsonResponse(created);
      }

      if (
        method === "POST" &&
        path === "/api/v1/deployment-revisions/revision-2/health-checks"
      ) {
        const recorded = healthCheck("health-2", "revision-2", "healthy");
        healthChecksByRevision["revision-2"] = [recorded];
        revisions = revisions.map((revision) =>
          revision.id === "revision-2"
            ? { ...revision, status: "healthy" }
            : revision,
        );
        events = [
          deploymentEvent(
            "event-3",
            "health_checked",
            "Deployment revision health is healthy.",
            "revision-2",
          ),
          ...events,
        ];
        return jsonResponse(recorded);
      }

      if (
        method === "POST" &&
        path === "/api/v1/deployment-revisions/revision-2/traffic"
      ) {
        revisions = revisions.map((revision) =>
          revision.id === "revision-2"
            ? { ...revision, traffic_percentage: 100, status: "healthy" }
            : { ...revision, traffic_percentage: 0 },
        );
        const promoted = revisions.find(
          (revision) => revision.id === "revision-2",
        );
        if (!promoted) {
          return jsonResponse({ detail: "revision missing" }, false);
        }
        events = [
          deploymentEvent(
            "event-4",
            "traffic_updated",
            "Deployment traffic allocation was updated.",
            "revision-2",
          ),
          ...events,
        ];
        return jsonResponse(promoted);
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

function deploymentRevision({
  id,
  revision,
  status,
  traffic,
}: {
  id: string;
  revision: number;
  status: string;
  traffic: number;
}): Record<string, unknown> {
  return {
    id,
    deployment_id: deploymentId,
    model_version_id: approvedVersionId,
    revision,
    serving_image: "ghcr.io/forgeml/serving-runtime:latest",
    runtime_config: {},
    traffic_percentage: traffic,
    status,
    orchestrator_deployment_id: `local-${revision}`,
    created_by: "user-1",
  };
}

function deploymentEvent(
  id: string,
  eventType: string,
  message: string,
  revisionId: string | null,
): Record<string, unknown> {
  return {
    id,
    deployment_id: deploymentId,
    deployment_revision_id: revisionId,
    event_type: eventType,
    message,
    metadata: {},
  };
}

function healthCheck(
  id: string,
  revisionId: string,
  status: string,
): Record<string, unknown> {
  return {
    id,
    deployment_revision_id: revisionId,
    status,
    latency_ms: 85,
    error_rate: 0.01,
    details: {},
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
