import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DatasetsPage } from "./DatasetsPage";

type FetchCall = [string, RequestInit | undefined];

const initialDatasetId = "dataset-1";
const createdDatasetId = "dataset-2";
const initialVersionId = "dataset-version-1";
const createdVersionId = "dataset-version-2";

describe("DatasetsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("creates datasets, prepares upload versions, finalizes metadata, and validates schema", async () => {
    const fetchMock = mockDatasetWorkflow();
    window.localStorage.setItem("forgeml_access_token", "token-123");
    window.localStorage.setItem("forgeml_project_id", "project-1");
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DatasetsPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Fraud Transactions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Dataset" }));
    fireEvent.change(screen.getByLabelText("Dataset Name"), {
      target: { value: "Fraud Feature Snapshot" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Daily feature snapshot for fraud scoring." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create dataset" }));

    expect(
      await screen.findByText("Created dataset Fraud Feature Snapshot."),
    ).toBeInTheDocument();
    const datasetCall = findFetchCall(
      fetchMock,
      "/api/v1/projects/project-1/datasets",
      "POST",
    );
    expect(JSON.parse(String(datasetCall[1]?.body))).toMatchObject({
      name: "Fraud Feature Snapshot",
      description: "Daily feature snapshot for fraud scoring.",
      source_type: "upload",
    });

    fireEvent.click(screen.getByRole("button", { name: "Version" }));
    fireEvent.change(screen.getByLabelText("Filename"), {
      target: { value: "fraud_features.csv" },
    });
    fireEvent.change(screen.getByLabelText("Content Type"), {
      target: { value: "text/csv" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create version" }));

    expect(await screen.findByText("Created upload plan for v1.")).toBeInTheDocument();
    expect(await screen.findByText("signed upload")).toBeInTheDocument();
    const versionCall = findFetchCall(
      fetchMock,
      `/api/v1/datasets/${createdDatasetId}/versions`,
      "POST",
    );
    expect(JSON.parse(String(versionCall[1]?.body))).toMatchObject({
      filename: "fraud_features.csv",
      content_type: "text/csv",
    });

    fireEvent.change(screen.getByLabelText("Content Hash"), {
      target: { value: "sha256:def456" },
    });
    fireEvent.change(screen.getByLabelText("Size Bytes"), {
      target: { value: "2048" },
    });
    fireEvent.change(screen.getByLabelText("CSV Sample"), {
      target: {
        value: "account_id,amount,is_fraud\nacct-1,42.5,false\nacct-2,500,true",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Finalize version" }));

    expect(await screen.findByText("Finalized dataset v1.")).toBeInTheDocument();
    const finalizeCall = findFetchCall(
      fetchMock,
      `/api/v1/dataset-versions/${createdVersionId}/finalize`,
      "POST",
    );
    expect(JSON.parse(String(finalizeCall[1]?.body))).toMatchObject({
      object_uri: "s3://forgeml/datasets/fraud-feature-snapshot/v1/fraud_features.csv",
      content_hash: "sha256:def456",
      size_bytes: 2048,
      row_count: null,
      schema_fields: null,
      sample_csv: "account_id,amount,is_fraud\nacct-1,42.5,false\nacct-2,500,true",
    });
    expect(await screen.findByText("account_id")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Validate" }));
    expect(await screen.findByText("Validation completed for validati.")).toBeInTheDocument();
    expect(
      findFetchCall(fetchMock, `/api/v1/dataset-versions/${createdVersionId}/validate`, "POST"),
    ).toBeTruthy();
  });
});

function mockDatasetWorkflow() {
  let datasets = [
    dataset(initialDatasetId, "Fraud Transactions", "fraud-transactions"),
  ];
  const versionsByDataset: Record<string, Array<Record<string, unknown>>> = {
    [initialDatasetId]: [
      datasetVersion(initialVersionId, initialDatasetId, 3, "validated", {
        content_hash: "sha256:abc123",
        row_count: 12000,
        size_bytes: 8192,
      }),
    ],
  };
  const schemaByVersion: Record<string, Record<string, unknown>> = {
    [initialVersionId]: datasetSchema(initialVersionId),
  };
  const validationRunsByVersion: Record<string, Array<Record<string, unknown>>> = {
    [initialVersionId]: [validationRun("validation-1", initialVersionId, "completed")],
  };
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const method = init?.method ?? "GET";

      if (method === "GET" && path === "/api/v1/projects/project-1/datasets") {
        return jsonResponse({ items: datasets, next_cursor: null });
      }

      if (method === "POST" && path === "/api/v1/projects/project-1/datasets") {
        const created = dataset(
          createdDatasetId,
          "Fraud Feature Snapshot",
          "fraud-feature-snapshot",
          "Daily feature snapshot for fraud scoring.",
        );
        datasets = [created, ...datasets];
        versionsByDataset[createdDatasetId] = [];
        return jsonResponse(created);
      }

      if (method === "GET" && path.startsWith("/api/v1/datasets/")) {
        const datasetId = path.split("/api/v1/datasets/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: versionsByDataset[datasetId] ?? [],
          next_cursor: null,
        });
      }

      if (method === "POST" && path === `/api/v1/datasets/${createdDatasetId}/versions`) {
        const version = datasetVersion(createdVersionId, createdDatasetId, 1, "pending_upload");
        versionsByDataset[createdDatasetId] = [
          version,
          ...(versionsByDataset[createdDatasetId] ?? []),
        ];
        validationRunsByVersion[createdVersionId] = [];
        return jsonResponse({
          version,
          upload: {
            upload_url: "https://storage.local/upload/fraud_features.csv",
            object_uri:
              "s3://forgeml/datasets/fraud-feature-snapshot/v1/fraud_features.csv",
            expires_at: "2026-07-23T23:59:00+00:00",
            required_headers: { "content-type": "text/csv" },
          },
        });
      }

      if (
        method === "POST" &&
        path === `/api/v1/dataset-versions/${createdVersionId}/finalize`
      ) {
        const finalized = datasetVersion(createdVersionId, createdDatasetId, 1, "validated", {
          object_uri:
            "s3://forgeml/datasets/fraud-feature-snapshot/v1/fraud_features.csv",
          content_hash: "sha256:def456",
          row_count: 2,
          size_bytes: 2048,
        });
        versionsByDataset[createdDatasetId] = versionsByDataset[createdDatasetId].map(
          (version) => (version.id === createdVersionId ? finalized : version),
        );
        schemaByVersion[createdVersionId] = datasetSchema(createdVersionId);
        validationRunsByVersion[createdVersionId] = [
          validationRun("validation-finalize", createdVersionId, "completed"),
        ];
        return jsonResponse(finalized);
      }

      if (method === "GET" && path.endsWith("/schema")) {
        const versionId = path.split("/api/v1/dataset-versions/")[1]?.split("/")[0] ?? "";
        return jsonResponse(schemaByVersion[versionId] ?? { detail: "not found" });
      }

      if (method === "GET" && path.endsWith("/validation-runs")) {
        const versionId = path.split("/api/v1/dataset-versions/")[1]?.split("/")[0] ?? "";
        return jsonResponse({
          items: validationRunsByVersion[versionId] ?? [],
          next_cursor: null,
        });
      }

      if (method === "POST" && path === `/api/v1/dataset-versions/${createdVersionId}/validate`) {
        const run = validationRun("validation-2", createdVersionId, "completed", {
          field_count: 3,
          row_count: 2,
          checks: ["schema_present", "metadata_valid"],
        });
        validationRunsByVersion[createdVersionId] = [
          run,
          ...(validationRunsByVersion[createdVersionId] ?? []),
        ];
        return jsonResponse(run);
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

function dataset(
  id: string,
  name: string,
  slug: string,
  description = "Payment events.",
): Record<string, unknown> {
  return {
    id,
    organization_id: "org-1",
    project_id: "project-1",
    name,
    slug,
    description,
    source_type: "upload",
    status: "active",
  };
}

function datasetVersion(
  id: string,
  datasetId: string,
  version: number,
  status: string,
  overrides: Partial<Record<string, unknown>> = {},
): Record<string, unknown> {
  return {
    id,
    dataset_id: datasetId,
    version,
    object_uri: `s3://forgeml/datasets/${datasetId}/v${version}.csv`,
    content_hash: status === "validated" ? "sha256:abc123" : "",
    row_count: status === "validated" ? 12000 : 0,
    size_bytes: status === "validated" ? 8192 : 0,
    status,
    created_by: "user-1",
    ...overrides,
  };
}

function datasetSchema(versionId: string): Record<string, unknown> {
  return {
    dataset_version_id: versionId,
    fields: [
      { name: "account_id", dtype: "string", nullable: false },
      { name: "amount", dtype: "float", nullable: false },
      { name: "is_fraud", dtype: "boolean", nullable: false },
    ],
    inferred: true,
    schema_hash: "schema-hash-1",
  };
}

function validationRun(
  id: string,
  versionId: string,
  status: string,
  report: Record<string, unknown> = {
    field_count: 3,
    row_count: 12000,
    checks: ["schema_present", "metadata_valid"],
  },
): Record<string, unknown> {
  return {
    id,
    dataset_version_id: versionId,
    status,
    report,
    error_message: null,
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
