import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FeatureStorePage } from "./FeatureStorePage";

type FetchCall = [string, RequestInit | undefined];

const initialFeatureSetId = "feature-set-1";
const createdFeatureSetId = "feature-set-2";
const pipelineId = "pipeline-1";

describe("FeatureStorePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates feature sets, registers definitions and pipelines, and triggers materialization", async () => {
    const fetchMock = mockFeatureStoreWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <FeatureStorePage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Merchant Signals")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Feature Set" }));
    fireEvent.change(screen.getByLabelText("Feature Set Name"), {
      target: { value: "Merchant Risk Signals" },
    });
    fireEvent.change(screen.getByLabelText("Entity Key"), {
      target: { value: "merchant_id" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Merchant risk features for authorization decisions." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create feature set" }));

    expect(
      await screen.findByText("Created feature set Merchant Risk Signals."),
    ).toBeInTheDocument();
    const featureSetCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/feature-sets",
      "POST",
    );
    expect(JSON.parse(String(featureSetCall[1]?.body))).toMatchObject({
      name: "Merchant Risk Signals",
      description: "Merchant risk features for authorization decisions.",
      entity_key: "merchant_id",
    });

    fireEvent.click(screen.getByRole("button", { name: "Definitions" }));
    fireEvent.change(screen.getByLabelText("Feature Definitions"), {
      target: {
        value: JSON.stringify([
          {
            name: "chargeback_rate_30d",
            dtype: "float",
            description: "Rolling chargeback rate.",
            nullable: false,
            constraints: { min: 0, max: 1 },
          },
          {
            name: "avg_ticket_7d",
            dtype: "float",
            description: "Seven day average ticket.",
            nullable: false,
            constraints: { min: 0 },
          },
        ]),
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Register definitions" }));

    expect(await screen.findByText("Registered 2 feature definitions.")).toBeInTheDocument();
    const definitionsCall = findFetchCall(
      fetchMock,
      `/api/v1/feature-sets/${createdFeatureSetId}/features`,
      "POST",
    );
    expect(JSON.parse(String(definitionsCall[1]?.body))).toMatchObject({
      definitions: [
        {
          name: "chargeback_rate_30d",
          dtype: "float",
          nullable: false,
          constraints: { min: 0, max: 1 },
        },
        {
          name: "avg_ticket_7d",
          dtype: "float",
          nullable: false,
          constraints: { min: 0 },
        },
      ],
    });

    fireEvent.click(screen.getByRole("button", { name: "Pipeline" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Register pipeline" })).not.toBeDisabled(),
    );
    fireEvent.change(screen.getByLabelText("Pipeline Name"), {
      target: { value: "daily merchant materialization" },
    });
    fireEvent.change(screen.getByLabelText("Code Reference"), {
      target: { value: "git://feature-pipelines/merchant_risk.py" },
    });
    fireEvent.change(screen.getByLabelText("Schedule Cron"), {
      target: { value: "0 2 * * *" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Register pipeline" }));

    expect(
      await screen.findByText("Registered pipeline daily merchant materialization."),
    ).toBeInTheDocument();
    const pipelineCall = findFetchCall(
      fetchMock,
      `/api/v1/feature-sets/${createdFeatureSetId}/pipelines`,
      "POST",
    );
    expect(JSON.parse(String(pipelineCall[1]?.body))).toMatchObject({
      name: "daily merchant materialization",
      source_dataset_id: "dataset-1",
      code_ref: "git://feature-pipelines/merchant_risk.py",
      schedule_cron: "0 2 * * *",
    });
    expect((await screen.findAllByText("dataset")).length).toBeGreaterThan(0);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Materialize daily merchant materialization",
      }),
    );

    expect(await screen.findByText("Requested materialization v1.")).toBeInTheDocument();
    expect(
      findFetchCall(fetchMock, `/api/v1/feature-pipelines/${pipelineId}/materialize`, "POST"),
    ).toBeTruthy();
    expect(await screen.findByText("Materialization v1")).toBeInTheDocument();
  });
});

function mockFeatureStoreWorkflow() {
  let featureSets = [
    featureSet(initialFeatureSetId, "Merchant Signals", "merchant-signals"),
  ];
  const definitionsByFeatureSet: Record<string, Array<Record<string, unknown>>> = {
    [initialFeatureSetId]: [
      featureDefinition("definition-1", initialFeatureSetId, "chargeback_rate_30d"),
    ],
  };
  const pipelinesByFeatureSet: Record<string, Array<Record<string, unknown>>> = {
    [initialFeatureSetId]: [],
  };
  const materializationsByFeatureSet: Record<string, Array<Record<string, unknown>>> = {
    [initialFeatureSetId]: [],
  };
  const lineageByFeatureSet: Record<string, Array<Record<string, unknown>>> = {
    [initialFeatureSetId]: [],
  };
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (method === "GET" && path === "/api/v1/projects/project-1/feature-sets") {
        return jsonResponse({ items: featureSets, next_cursor: null });
      }

      if (method === "POST" && path === "/api/v1/projects/project-1/feature-sets") {
        const created = featureSet(
          createdFeatureSetId,
          "Merchant Risk Signals",
          "merchant-risk-signals",
          "Merchant risk features for authorization decisions.",
        );
        featureSets = [created, ...featureSets];
        definitionsByFeatureSet[createdFeatureSetId] = [];
        pipelinesByFeatureSet[createdFeatureSetId] = [];
        materializationsByFeatureSet[createdFeatureSetId] = [];
        lineageByFeatureSet[createdFeatureSetId] = [];
        return jsonResponse(created);
      }

      if (method === "GET" && path.endsWith("/features")) {
        const featureSetId = path.split("/api/v1/feature-sets/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: definitionsByFeatureSet[featureSetId] ?? [],
          next_cursor: null,
        });
      }

      if (
        method === "POST" &&
        path === `/api/v1/feature-sets/${createdFeatureSetId}/features`
      ) {
        const definitions = [
          featureDefinition("definition-2", createdFeatureSetId, "chargeback_rate_30d"),
          featureDefinition("definition-3", createdFeatureSetId, "avg_ticket_7d"),
        ];
        definitionsByFeatureSet[createdFeatureSetId] = definitions;
        return jsonResponse({ items: definitions, next_cursor: null });
      }

      if (method === "GET" && path.endsWith("/pipelines")) {
        const featureSetId = path.split("/api/v1/feature-sets/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: pipelinesByFeatureSet[featureSetId] ?? [],
          next_cursor: null,
        });
      }

      if (
        method === "POST" &&
        path === `/api/v1/feature-sets/${createdFeatureSetId}/pipelines`
      ) {
        const pipeline = {
          id: pipelineId,
          feature_set_id: createdFeatureSetId,
          name: "daily merchant materialization",
          source_dataset_id: "dataset-1",
          code_ref: "git://feature-pipelines/merchant_risk.py",
          schedule_cron: "0 2 * * *",
          status: "active",
        };
        pipelinesByFeatureSet[createdFeatureSetId] = [
          pipeline,
          ...(pipelinesByFeatureSet[createdFeatureSetId] ?? []),
        ];
        lineageByFeatureSet[createdFeatureSetId] = [
          {
            id: "lineage-1",
            feature_set_id: createdFeatureSetId,
            upstream_type: "dataset",
            upstream_id: "dataset-1",
          },
        ];
        return jsonResponse(pipeline);
      }

      if (method === "POST" && path === `/api/v1/feature-pipelines/${pipelineId}/materialize`) {
        const materialization = {
          id: "materialization-1",
          feature_set_id: createdFeatureSetId,
          pipeline_id: pipelineId,
          version: 1,
          offline_uri: "s3://forgeml/features/merchant-risk-signals/materialization-1",
          online_ref: "feature-set:merchant-risk-signals:v1",
          orchestrator_run_id: "local-feature-materialization:pipeline-1:materialization-1",
          status: "requested",
        };
        materializationsByFeatureSet[createdFeatureSetId] = [
          materialization,
          ...(materializationsByFeatureSet[createdFeatureSetId] ?? []),
        ];
        return jsonResponse(materialization);
      }

      if (method === "GET" && path.endsWith("/materializations")) {
        const featureSetId = path.split("/api/v1/feature-sets/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: materializationsByFeatureSet[featureSetId] ?? [],
          next_cursor: null,
        });
      }

      if (method === "GET" && path.endsWith("/lineage")) {
        const featureSetId = path.split("/api/v1/feature-sets/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: lineageByFeatureSet[featureSetId] ?? [],
          next_cursor: null,
        });
      }

      if (method === "GET" && path === "/api/v1/projects/project-1/datasets") {
        return jsonResponse({
          items: [
            {
              id: "dataset-1",
              organization_id: "org-1",
              project_id: "project-1",
              name: "Fraud Transactions",
              slug: "fraud-transactions",
              description: "Payment events.",
              source_type: "upload",
              status: "active",
            },
          ],
          next_cursor: null,
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

function featureSet(
  id: string,
  name: string,
  slug: string,
  description = "Merchant behavior features.",
): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    name,
    slug,
    description,
    entity_key: "merchant_id",
    status: "active",
  };
}

function featureDefinition(
  id: string,
  featureSetId: string,
  name: string,
): Record<string, unknown> {
  return {
    id,
    feature_set_id: featureSetId,
    name,
    dtype: "float",
    description: name === "avg_ticket_7d" ? "Seven day average ticket." : "Rolling chargeback rate.",
    nullable: false,
    constraints: name === "avg_ticket_7d" ? { min: 0 } : { min: 0, max: 1 },
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
    return String(input).includes(fragment) && (init?.method ?? "GET") === method;
  });
  if (!call) {
    throw new Error(`Expected ${method} fetch call containing ${fragment}`);
  }
  return call as FetchCall;
}
