import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ClipboardCheck,
  Database,
  FileCheck,
  FileText,
  Hash,
  ListChecks,
  Plus,
  UploadCloud,
  X,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import {
  createDataset,
  createDatasetVersion,
  finalizeDatasetVersion,
  getDatasetSchema,
  listDatasetValidationRuns,
  listDatasetVersions,
  listDatasets,
  validateDatasetVersion,
  type Dataset,
  type DatasetSchema,
  type DatasetValidationRun,
  type DatasetVersion,
  type SchemaField,
  type UploadInstructions,
} from "../api/datasets";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

type SourceType = "upload" | "s3" | "database" | "stream";
type SchemaMode = "sample_csv" | "schema_fields";

export function DatasetsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadDatasets = Boolean(token && projectId);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [isCreateDatasetOpen, setIsCreateDatasetOpen] = useState(false);
  const [isCreateVersionOpen, setIsCreateVersionOpen] = useState(false);
  const [datasetName, setDatasetName] = useState("fraud-transactions");
  const [datasetDescription, setDatasetDescription] = useState(
    "Payment events used for offline fraud model training.",
  );
  const [sourceType, setSourceType] = useState<SourceType>("upload");
  const [filename, setFilename] = useState("transactions.csv");
  const [contentType, setContentType] = useState("text/csv");
  const [uploadInstructions, setUploadInstructions] = useState<UploadInstructions | null>(
    null,
  );
  const [objectUri, setObjectUri] = useState("");
  const [contentHash, setContentHash] = useState("sha256:abc123");
  const [sizeBytes, setSizeBytes] = useState("4096");
  const [rowCount, setRowCount] = useState("");
  const [schemaMode, setSchemaMode] = useState<SchemaMode>("sample_csv");
  const [sampleCsv, setSampleCsv] = useState(defaultSampleCsv);
  const [schemaFieldsText, setSchemaFieldsText] = useState(defaultSchemaFieldsText);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);

  const datasetsQuery = useQuery({
    queryKey: ["datasets", projectId],
    queryFn: () => listDatasets(projectId ?? "", token ?? ""),
    enabled: canLoadDatasets,
  });
  const datasets = useMemo(
    () => datasetsQuery.data?.items ?? [],
    [datasetsQuery.data?.items],
  );
  const selectedDataset =
    datasets.find((dataset) => dataset.id === selectedDatasetId) ?? datasets[0];
  const activeDatasetId = selectedDataset?.id ?? "";
  const versionsQuery = useQuery({
    queryKey: ["dataset-versions", activeDatasetId],
    queryFn: () => listDatasetVersions(activeDatasetId, token ?? ""),
    enabled: Boolean(token && activeDatasetId),
  });
  const versions = useMemo(
    () =>
      [...(versionsQuery.data?.items ?? [])].sort(
        (left, right) => right.version - left.version,
      ),
    [versionsQuery.data?.items],
  );
  const selectedVersion =
    versions.find((version) => version.id === selectedVersionId) ?? versions[0];
  const activeVersionId = selectedVersion?.id ?? "";
  const schemaQuery = useQuery({
    queryKey: ["dataset-schema", activeVersionId],
    queryFn: () => getDatasetSchema(activeVersionId, token ?? ""),
    enabled: Boolean(token && activeVersionId && selectedVersion?.status !== "pending_upload"),
  });
  const validationRunsQuery = useQuery({
    queryKey: ["dataset-validation-runs", activeVersionId],
    queryFn: () => listDatasetValidationRuns(activeVersionId, token ?? ""),
    enabled: Boolean(token && activeVersionId),
  });
  const validationRuns = useMemo(
    () => validationRunsQuery.data?.items ?? [],
    [validationRunsQuery.data?.items],
  );
  const validatedVersions = versions.filter((version) => version.status === "validated");
  const failedValidations = validationRuns.filter((run) => run.status === "failed");

  const createDatasetMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Dataset creation requires project context.");
      }
      return createDataset(
        projectId,
        {
          name: datasetName.trim(),
          description: datasetDescription.trim(),
          source_type: sourceType,
        },
        token,
      );
    },
    onSuccess: (dataset) => {
      queryClient.setQueryData<{ items: Dataset[]; next_cursor: string | null }>(
        ["datasets", projectId],
        (current) => ({
          items: [dataset, ...(current?.items.filter((item) => item.id !== dataset.id) ?? [])],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Created dataset ${dataset.name}.`);
      setSelectedDatasetId(dataset.id);
      setSelectedVersionId("");
      setUploadInstructions(null);
      closeCreateDatasetForm();
      queryClient.invalidateQueries({ queryKey: ["datasets", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Dataset creation failed.",
      );
    },
  });
  const createVersionMutation = useMutation({
    mutationFn: () => {
      if (!selectedDataset || !token) {
        throw new Error("Dataset version creation requires a selected dataset.");
      }
      return createDatasetVersion(
        selectedDataset.id,
        {
          filename: filename.trim(),
          content_type: contentType.trim(),
        },
        token,
      );
    },
    onSuccess: (result) => {
      queryClient.setQueryData<{ items: DatasetVersion[]; next_cursor: string | null }>(
        ["dataset-versions", result.version.dataset_id],
        (current) => ({
          items: [
            result.version,
            ...(current?.items.filter((item) => item.id !== result.version.id) ?? []),
          ],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Created upload plan for v${result.version.version}.`);
      setSelectedVersionId(result.version.id);
      setUploadInstructions(result.upload);
      setObjectUri(result.upload.object_uri);
      closeCreateVersionForm();
      queryClient.invalidateQueries({
        queryKey: ["dataset-versions", result.version.dataset_id],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Dataset version creation failed.",
      );
    },
  });
  const finalizeVersionMutation = useMutation({
    mutationFn: () => {
      if (!selectedVersion || !token) {
        throw new Error("Dataset finalization requires a selected version.");
      }
      return finalizeDatasetVersion(
        selectedVersion.id,
        {
          object_uri: optionalString(objectUri),
          content_hash: contentHash.trim(),
          size_bytes: parsePositiveInteger(sizeBytes, "Size bytes"),
          row_count:
            schemaMode === "schema_fields"
              ? parseOptionalNonNegativeInteger(rowCount, "Row count")
              : null,
          schema_fields:
            schemaMode === "schema_fields" ? parseSchemaFields(schemaFieldsText) : null,
          sample_csv: schemaMode === "sample_csv" ? requireText(sampleCsv, "CSV sample") : null,
        },
        token,
      );
    },
    onSuccess: (version) => {
      queryClient.setQueryData<{ items: DatasetVersion[]; next_cursor: string | null }>(
        ["dataset-versions", version.dataset_id],
        (current) => ({
          items: (current?.items ?? []).map((item) => (item.id === version.id ? version : item)),
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Finalized dataset v${version.version}.`);
      setSelectedVersionId(version.id);
      invalidateVersionState(version.dataset_id, version.id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Dataset finalization failed.",
      );
    },
  });
  const validateVersionMutation = useMutation({
    mutationFn: () => {
      if (!selectedVersion || !token) {
        throw new Error("Validation requires a selected dataset version.");
      }
      return validateDatasetVersion(selectedVersion.id, token);
    },
    onSuccess: (run) => {
      queryClient.setQueryData<{
        items: DatasetValidationRun[];
        next_cursor: string | null;
      }>(["dataset-validation-runs", run.dataset_version_id], (current) => ({
        items: [run, ...(current?.items.filter((item) => item.id !== run.id) ?? [])],
        next_cursor: current?.next_cursor ?? null,
      }));
      setOperationError(null);
      setOperationMessage(`Validation ${run.status} for ${run.id.slice(0, 8)}.`);
      queryClient.invalidateQueries({
        queryKey: ["dataset-validation-runs", run.dataset_version_id],
      });
      queryClient.invalidateQueries({ queryKey: ["dataset-schema", run.dataset_version_id] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Dataset validation failed.",
      );
    },
  });

  useEffect(() => {
    if (!selectedDatasetId && datasets[0]) {
      setSelectedDatasetId(datasets[0].id);
      return;
    }
    if (selectedDatasetId && !datasets.some((dataset) => dataset.id === selectedDatasetId)) {
      setSelectedDatasetId(datasets[0]?.id ?? "");
      setSelectedVersionId("");
    }
  }, [datasets, selectedDatasetId]);

  useEffect(() => {
    if (!selectedVersionId && versions[0]) {
      setSelectedVersionId(versions[0].id);
      return;
    }
    if (selectedVersionId && !versions.some((version) => version.id === selectedVersionId)) {
      setSelectedVersionId(versions[0]?.id ?? "");
    }
  }, [versions, selectedVersionId]);

  function invalidateVersionState(datasetId: string, versionId: string) {
    queryClient.invalidateQueries({ queryKey: ["dataset-versions", datasetId] });
    queryClient.invalidateQueries({ queryKey: ["dataset-schema", versionId] });
    queryClient.invalidateQueries({ queryKey: ["dataset-validation-runs", versionId] });
  }

  function closeCreateDatasetForm() {
    setIsCreateDatasetOpen(false);
    setDatasetName("fraud-transactions");
    setDatasetDescription("Payment events used for offline fraud model training.");
    setSourceType("upload");
  }

  function closeCreateVersionForm() {
    setIsCreateVersionOpen(false);
    setFilename("transactions.csv");
    setContentType("text/csv");
  }

  function handleCreateDataset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (datasetName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Dataset name must be at least 3 characters.");
      return;
    }
    createDatasetMutation.mutate();
  }

  function handleCreateVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!filename.trim() || !contentType.trim()) {
      setOperationMessage(null);
      setOperationError("Filename and content type are required.");
      return;
    }
    createVersionMutation.mutate();
  }

  function handleFinalizeVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!contentHash.trim()) {
      setOperationMessage(null);
      setOperationError("Content hash is required.");
      return;
    }
    finalizeVersionMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Data"
        title="Datasets"
        description="Immutable dataset versions, schema validation, profiling, lineage, and upload lifecycle."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Registered" value={String(datasets.length)} detail="logical datasets" />
        <MetricCard label="Versions" value={String(versions.length)} detail="selected dataset" />
        <MetricCard
          label="Validated"
          value={String(validatedVersions.length)}
          detail="dataset versions"
          tone="success"
        />
        <MetricCard
          label="Failed Checks"
          value={String(failedValidations.length)}
          detail="selected version"
          tone={failedValidations.length > 0 ? "danger" : "neutral"}
        />
      </div>
      {operationMessage ? (
        <div className="mt-4 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-signal">
          {operationMessage}
        </div>
      ) : null}
      {operationError ? (
        <div className="mt-4 rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-risk">
          {operationError}
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel
          title="Dataset Registry"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateDatasetOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Dataset
            </button>
          }
        >
          {isCreateDatasetOpen ? (
            <CreateDatasetForm
              name={datasetName}
              description={datasetDescription}
              sourceType={sourceType}
              isPending={createDatasetMutation.isPending}
              onSubmit={handleCreateDataset}
              onCancel={closeCreateDatasetForm}
              onNameChange={setDatasetName}
              onDescriptionChange={setDatasetDescription}
              onSourceTypeChange={setSourceType}
            />
          ) : null}
          {!canLoadDatasets ? (
            <StateMessage message="No project context is selected." />
          ) : datasetsQuery.error ? (
            <StateMessage message="Dataset registry request failed." tone="danger" />
          ) : datasets.length === 0 ? (
            <StateMessage
              message={
                datasetsQuery.isFetching
                  ? "Loading datasets."
                  : "No datasets registered for this project."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Dataset</th>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Slug</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((dataset) => (
                    <DatasetRow
                      key={dataset.id}
                      dataset={dataset}
                      selected={dataset.id === selectedDataset?.id}
                      onSelect={() => {
                        setSelectedDatasetId(dataset.id);
                        setSelectedVersionId("");
                        setUploadInstructions(null);
                      }}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel
          title="Version Timeline"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateVersionOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <UploadCloud className="h-4 w-4" />
              Version
            </button>
          }
        >
          {isCreateVersionOpen ? (
            <CreateVersionForm
              filename={filename}
              contentType={contentType}
              isPending={createVersionMutation.isPending}
              hasDataset={Boolean(selectedDataset)}
              onSubmit={handleCreateVersion}
              onCancel={closeCreateVersionForm}
              onFilenameChange={setFilename}
              onContentTypeChange={setContentType}
            />
          ) : null}
          {!selectedDataset ? (
            <StateMessage message="Select a dataset before reviewing versions." />
          ) : versionsQuery.error ? (
            <StateMessage message="Dataset version request failed." tone="danger" />
          ) : versions.length === 0 ? (
            <StateMessage
              message={
                versionsQuery.isFetching
                  ? "Loading dataset versions."
                  : "No versions have been created for this dataset."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Version</th>
                    <th>Status</th>
                    <th>Rows</th>
                    <th>Size</th>
                    <th>Hash</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((version) => (
                    <VersionRow
                      key={version.id}
                      version={version}
                      selected={version.id === selectedVersion?.id}
                      onSelect={() => setSelectedVersionId(version.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel title="Upload Instructions">
          {uploadInstructions ? (
            <UploadInstructionsPanel upload={uploadInstructions} />
          ) : (
            <StateMessage message="Create a dataset version to receive signed object storage upload instructions." />
          )}
        </DataPanel>

        <DataPanel title="Finalize Version">
          {!selectedVersion ? (
            <StateMessage message="Select a dataset version before finalizing metadata." />
          ) : selectedVersion.status !== "pending_upload" ? (
            <VersionDetail version={selectedVersion} />
          ) : (
            <FinalizeVersionForm
              objectUri={objectUri || selectedVersion.object_uri}
              contentHash={contentHash}
              sizeBytes={sizeBytes}
              rowCount={rowCount}
              schemaMode={schemaMode}
              sampleCsv={sampleCsv}
              schemaFieldsText={schemaFieldsText}
              isPending={finalizeVersionMutation.isPending}
              onSubmit={handleFinalizeVersion}
              onObjectUriChange={setObjectUri}
              onContentHashChange={setContentHash}
              onSizeBytesChange={setSizeBytes}
              onRowCountChange={setRowCount}
              onSchemaModeChange={setSchemaMode}
              onSampleCsvChange={setSampleCsv}
              onSchemaFieldsTextChange={setSchemaFieldsText}
            />
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="Schema">
          {!selectedVersion ? (
            <StateMessage message="No dataset version is selected." />
          ) : selectedVersion.status === "pending_upload" ? (
            <StateMessage message="Finalize the selected version before inspecting schema." />
          ) : schemaQuery.error ? (
            <StateMessage message="Dataset schema request failed." tone="danger" />
          ) : schemaQuery.isFetching && !schemaQuery.data ? (
            <StateMessage message="Loading dataset schema." />
          ) : schemaQuery.data ? (
            <SchemaPanel schema={schemaQuery.data} />
          ) : (
            <StateMessage message="No schema is recorded for the selected version." />
          )}
        </DataPanel>

        <DataPanel
          title="Validation Runs"
          action={
            <button
              type="button"
              disabled={!selectedVersion || validateVersionMutation.isPending}
              onClick={() => validateVersionMutation.mutate()}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <ClipboardCheck className="h-4 w-4" />
              Validate
            </button>
          }
        >
          {!selectedVersion ? (
            <StateMessage message="No dataset version is selected." />
          ) : validationRunsQuery.error ? (
            <StateMessage message="Dataset validation history request failed." tone="danger" />
          ) : validationRuns.length === 0 ? (
            <StateMessage
              message={
                validationRunsQuery.isFetching
                  ? "Loading validation runs."
                  : "No validation runs are recorded for this version."
              }
            />
          ) : (
            <div className="space-y-3">
              {validationRuns.map((run) => (
                <ValidationRunCard key={run.id} run={run} />
              ))}
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

const defaultSampleCsv = `amount,merchant_category,is_fraud
12.5,grocery,false
481.2,electronics,true`;

const defaultSchemaFieldsText = `[
  {
    "name": "amount",
    "dtype": "float",
    "nullable": false
  },
  {
    "name": "merchant_category",
    "dtype": "string",
    "nullable": false
  },
  {
    "name": "is_fraud",
    "dtype": "boolean",
    "nullable": false
  }
]`;

type CreateDatasetFormProps = {
  name: string;
  description: string;
  sourceType: SourceType;
  isPending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onSourceTypeChange: (value: SourceType) => void;
};

function CreateDatasetForm({
  name,
  description,
  sourceType,
  isPending,
  onSubmit,
  onCancel,
  onNameChange,
  onDescriptionChange,
  onSourceTypeChange,
}: CreateDatasetFormProps) {
  return (
    <form
      aria-label="Create dataset"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(180px,1fr)_140px]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Dataset Name
          <input
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Source Type
          <select
            value={sourceType}
            onChange={(event) => onSourceTypeChange(event.target.value as SourceType)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          >
            <option value="upload">upload</option>
            <option value="s3">s3</option>
            <option value="database">database</option>
            <option value="stream">stream</option>
          </select>
        </label>
      </div>
      <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
        Description
        <input
          value={description}
          onChange={(event) => onDescriptionChange(event.target.value)}
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={isPending}
          className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Plus className="h-4 w-4" />
          Create dataset
        </button>
        <button
          type="button"
          aria-label="Cancel dataset creation"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

type CreateVersionFormProps = {
  filename: string;
  contentType: string;
  isPending: boolean;
  hasDataset: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onFilenameChange: (value: string) => void;
  onContentTypeChange: (value: string) => void;
};

function CreateVersionForm({
  filename,
  contentType,
  isPending,
  hasDataset,
  onSubmit,
  onCancel,
  onFilenameChange,
  onContentTypeChange,
}: CreateVersionFormProps) {
  return (
    <form
      aria-label="Create dataset version"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-2">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Filename
          <input
            value={filename}
            onChange={(event) => onFilenameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Content Type
          <input
            value={contentType}
            onChange={(event) => onContentTypeChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
      {!hasDataset ? (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Select a dataset before creating a version.
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={isPending || !hasDataset}
          className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <UploadCloud className="h-4 w-4" />
          Create version
        </button>
        <button
          type="button"
          aria-label="Cancel dataset version creation"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

type FinalizeVersionFormProps = {
  objectUri: string;
  contentHash: string;
  sizeBytes: string;
  rowCount: string;
  schemaMode: SchemaMode;
  sampleCsv: string;
  schemaFieldsText: string;
  isPending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onObjectUriChange: (value: string) => void;
  onContentHashChange: (value: string) => void;
  onSizeBytesChange: (value: string) => void;
  onRowCountChange: (value: string) => void;
  onSchemaModeChange: (value: SchemaMode) => void;
  onSampleCsvChange: (value: string) => void;
  onSchemaFieldsTextChange: (value: string) => void;
};

function FinalizeVersionForm({
  objectUri,
  contentHash,
  sizeBytes,
  rowCount,
  schemaMode,
  sampleCsv,
  schemaFieldsText,
  isPending,
  onSubmit,
  onObjectUriChange,
  onContentHashChange,
  onSizeBytesChange,
  onRowCountChange,
  onSchemaModeChange,
  onSampleCsvChange,
  onSchemaFieldsTextChange,
}: FinalizeVersionFormProps) {
  return (
    <form aria-label="Finalize dataset version" onSubmit={onSubmit} className="grid gap-4">
      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
        Object URI
        <input
          value={objectUri}
          onChange={(event) => onObjectUriChange(event.target.value)}
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      <div className="grid gap-3 lg:grid-cols-3">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Content Hash
          <input
            value={contentHash}
            onChange={(event) => onContentHashChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Size Bytes
          <input
            value={sizeBytes}
            onChange={(event) => onSizeBytesChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Row Count
          <input
            value={rowCount}
            onChange={(event) => onRowCountChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      </div>
      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
        Schema Source
        <select
          value={schemaMode}
          onChange={(event) => onSchemaModeChange(event.target.value as SchemaMode)}
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        >
          <option value="sample_csv">CSV sample</option>
          <option value="schema_fields">schema fields</option>
        </select>
      </label>
      {schemaMode === "sample_csv" ? (
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          CSV Sample
          <textarea
            value={sampleCsv}
            onChange={(event) => onSampleCsvChange(event.target.value)}
            rows={6}
            className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      ) : (
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Schema Fields
          <textarea
            value={schemaFieldsText}
            onChange={(event) => onSchemaFieldsTextChange(event.target.value)}
            rows={8}
            className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
      )}
      <button
        type="submit"
        disabled={isPending}
        className="inline-flex h-10 w-fit items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <FileCheck className="h-4 w-4" />
        Finalize version
      </button>
    </form>
  );
}

function DatasetRow({
  dataset,
  selected,
  onSelect,
}: {
  dataset: Dataset;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{dataset.name}</div>
        <div className="text-xs text-steel">{dataset.description || "No description"}</div>
      </td>
      <td>{dataset.source_type}</td>
      <td>
        <span className={statusClassName(dataset.status)}>{dataset.status}</span>
      </td>
      <td>{dataset.slug}</td>
      <td>
        <button
          type="button"
          onClick={onSelect}
          className={[
            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
            selected
              ? "border-ink bg-ink text-white"
              : "border-slate-200 bg-white text-steel hover:text-ink",
          ].join(" ")}
        >
          {selected ? "Active" : "Select"}
        </button>
      </td>
    </tr>
  );
}

function VersionRow({
  version,
  selected,
  onSelect,
}: {
  version: DatasetVersion;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">v{version.version}</div>
        <div className="max-w-[240px] truncate text-xs text-steel">{version.object_uri}</div>
      </td>
      <td>
        <span className={statusClassName(version.status)}>{version.status}</span>
      </td>
      <td>{formatInteger(version.row_count)}</td>
      <td>{formatBytes(version.size_bytes)}</td>
      <td className="max-w-[160px] truncate">{version.content_hash || "pending"}</td>
      <td>
        <button
          type="button"
          onClick={onSelect}
          className={[
            "inline-flex h-8 items-center rounded border px-3 text-xs font-semibold transition",
            selected
              ? "border-ink bg-ink text-white"
              : "border-slate-200 bg-white text-steel hover:text-ink",
          ].join(" ")}
        >
          {selected ? "Active" : "Select"}
        </button>
      </td>
    </tr>
  );
}

function UploadInstructionsPanel({ upload }: { upload: UploadInstructions }) {
  return (
    <div className="grid gap-4">
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<UploadCloud className="h-4 w-4" />}
          label="Method"
          value="signed upload"
          detail={upload.expires_at}
        />
        <SignalTile
          icon={<Database className="h-4 w-4" />}
          label="Object"
          value={upload.object_uri}
          detail="finalization target"
        />
        <SignalTile
          icon={<Hash className="h-4 w-4" />}
          label="Headers"
          value={String(Object.keys(upload.required_headers).length)}
          detail="required"
        />
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="font-medium">Upload URL</div>
        <div className="mt-2 break-all font-mono text-xs text-steel">{upload.upload_url}</div>
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="font-medium">Required Headers</div>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-steel">
          {formatObject(upload.required_headers)}
        </pre>
      </div>
    </div>
  );
}

function VersionDetail({ version }: { version: DatasetVersion }) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">Dataset v{version.version}</div>
          <div className="mt-1 break-all text-xs text-steel">{version.object_uri}</div>
        </div>
        <span className={statusClassName(version.status)}>{version.status}</span>
      </div>
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<Database className="h-4 w-4" />}
          label="Rows"
          value={formatInteger(version.row_count)}
          detail="validated records"
        />
        <SignalTile
          icon={<FileText className="h-4 w-4" />}
          label="Size"
          value={formatBytes(version.size_bytes)}
          detail="object payload"
        />
        <SignalTile
          icon={<Hash className="h-4 w-4" />}
          label="Hash"
          value={version.content_hash || "pending"}
          detail={version.id.slice(0, 8)}
        />
      </div>
    </div>
  );
}

function SchemaPanel({ schema }: { schema: DatasetSchema }) {
  return (
    <div className="grid gap-4">
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<FileText className="h-4 w-4" />}
          label="Fields"
          value={String(schema.fields.length)}
          detail={schema.inferred ? "inferred" : "provided"}
        />
        <SignalTile
          icon={<Hash className="h-4 w-4" />}
          label="Schema Hash"
          value={schema.schema_hash}
          detail={schema.dataset_version_id.slice(0, 8)}
        />
        <SignalTile
          icon={<ListChecks className="h-4 w-4" />}
          label="Nullable"
          value={String(schema.fields.filter((field) => field.nullable).length)}
          detail="field count"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead className="text-xs uppercase text-steel">
            <tr>
              <th className="py-2">Field</th>
              <th>Type</th>
              <th>Nullable</th>
            </tr>
          </thead>
          <tbody>
            {schema.fields.map((field) => (
              <tr key={field.name} className="border-t border-slate-100">
                <td className="py-3 font-medium">{field.name}</td>
                <td>{field.dtype}</td>
                <td>{field.nullable ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ValidationRunCard({ run }: { run: DatasetValidationRun }) {
  return (
    <article className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{run.id.slice(0, 8)}</div>
          <div className="mt-1 text-xs text-steel">{formatValidationSummary(run.report)}</div>
        </div>
        <span className={statusClassName(run.status)}>{run.status}</span>
      </div>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-steel">
        {formatObject(run.report)}
      </pre>
      {run.error_message ? (
        <div className="mt-3 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk">
          {run.error_message}
        </div>
      ) : null}
    </article>
  );
}

function SignalTile({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-steel">
        {icon}
        {label}
      </div>
      <div className="mt-2 truncate text-sm font-medium">{value}</div>
      <div className="mt-1 truncate text-xs text-steel">{detail}</div>
    </div>
  );
}

function StateMessage({
  message,
  tone = "neutral",
}: {
  message: string;
  tone?: "neutral" | "danger";
}) {
  const className =
    tone === "danger"
      ? "rounded border border-rose-200 bg-rose-50 p-4 text-sm text-risk"
      : "rounded border border-slate-200 bg-cloud p-4 text-sm text-steel";
  return <div className={className}>{message}</div>;
}

function statusClassName(status: string): string {
  if (status === "active" || status === "validated" || status === "completed") {
    return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
  }
  if (status === "pending_upload" || status === "running") {
    return "rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700";
  }
  if (status === "validation_failed" || status === "failed") {
    return "rounded bg-rose-50 px-2 py-1 text-xs font-medium text-risk";
  }
  return "rounded bg-field px-2 py-1 text-xs font-medium";
}

function parsePositiveInteger(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${label} must be a positive integer.`);
  }
  return parsed;
}

function parseOptionalNonNegativeInteger(value: string, label: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error(`${label} must be zero or greater.`);
  }
  return parsed;
}

function parseSchemaFields(value: string): SchemaField[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error("Schema fields must be valid JSON.");
  }
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("Schema fields must be a non-empty JSON array.");
  }
  return parsed.map((field) => {
    if (!isSchemaField(field)) {
      throw new Error("Each schema field must include name, dtype, and nullable.");
    }
    return field;
  });
}

function isSchemaField(value: unknown): value is SchemaField {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const field = value as Record<string, unknown>;
  return (
    typeof field.name === "string" &&
    field.name.trim().length > 0 &&
    typeof field.dtype === "string" &&
    field.dtype.trim().length > 0 &&
    typeof field.nullable === "boolean"
  );
}

function requireText(value: string, label: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(`${label} is required.`);
  }
  return trimmed;
}

function optionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatBytes(value: number): string {
  if (value <= 0) {
    return "0 B";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KiB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
}

function formatObject(value: Record<string, unknown>): string {
  if (Object.keys(value).length === 0) {
    return "{}";
  }
  return JSON.stringify(value, null, 2);
}

function formatValidationSummary(report: Record<string, unknown>): string {
  const checks = report.checks;
  if (Array.isArray(checks)) {
    return `${checks.length} checks`;
  }
  const fieldCount = report.field_count;
  if (typeof fieldCount === "number") {
    return `${fieldCount} fields`;
  }
  return "validation report recorded";
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
