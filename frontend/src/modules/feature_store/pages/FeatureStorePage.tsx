import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Database,
  GitBranch,
  ListChecks,
  PackageCheck,
  Play,
  Plus,
  Route,
  X,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import { listDatasets, type Dataset } from "../../datasets/api/datasets";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import {
  createFeatureSet,
  listFeatureDefinitions,
  listFeatureLineage,
  listFeatureMaterializations,
  listFeaturePipelines,
  listFeatureSets,
  materializeFeaturePipeline,
  registerFeatureDefinitions,
  registerFeaturePipeline,
  type FeatureDefinition,
  type FeatureLineage,
  type FeatureMaterialization,
  type FeaturePipeline,
  type FeatureSet,
} from "../api/featureStore";

export function FeatureStorePage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const projectId = readLocalStorage("forgeml_project_id");
  const canLoadFeatureSets = Boolean(token && projectId);
  const [selectedFeatureSetId, setSelectedFeatureSetId] = useState("");
  const [selectedPipelineId, setSelectedPipelineId] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [isCreateFeatureSetOpen, setIsCreateFeatureSetOpen] = useState(false);
  const [isDefinitionFormOpen, setIsDefinitionFormOpen] = useState(false);
  const [isPipelineFormOpen, setIsPipelineFormOpen] = useState(false);
  const [featureSetName, setFeatureSetName] = useState("merchant-signals");
  const [featureSetDescription, setFeatureSetDescription] = useState(
    "Merchant behavior features for fraud scoring.",
  );
  const [entityKey, setEntityKey] = useState("merchant_id");
  const [definitionsText, setDefinitionsText] = useState(defaultDefinitionsText);
  const [pipelineName, setPipelineName] = useState("daily materialization");
  const [codeRef, setCodeRef] = useState("git://feature-pipelines/merchant_signals.py");
  const [scheduleCron, setScheduleCron] = useState("0 3 * * *");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);

  const featureSetsQuery = useQuery({
    queryKey: ["feature-sets", projectId],
    queryFn: () => listFeatureSets(projectId ?? "", token ?? ""),
    enabled: canLoadFeatureSets,
  });
  const featureSets = useMemo(
    () => featureSetsQuery.data?.items ?? [],
    [featureSetsQuery.data?.items],
  );
  const selectedFeatureSet =
    featureSets.find((featureSet) => featureSet.id === selectedFeatureSetId) ??
    featureSets[0];
  const activeFeatureSetId = selectedFeatureSet?.id ?? "";
  const definitionsQuery = useQuery({
    queryKey: ["feature-definitions", activeFeatureSetId],
    queryFn: () => listFeatureDefinitions(activeFeatureSetId, token ?? ""),
    enabled: Boolean(token && activeFeatureSetId),
  });
  const definitions = useMemo(
    () => definitionsQuery.data?.items ?? [],
    [definitionsQuery.data?.items],
  );
  const pipelinesQuery = useQuery({
    queryKey: ["feature-pipelines", activeFeatureSetId],
    queryFn: () => listFeaturePipelines(activeFeatureSetId, token ?? ""),
    enabled: Boolean(token && activeFeatureSetId),
  });
  const pipelines = useMemo(
    () => pipelinesQuery.data?.items ?? [],
    [pipelinesQuery.data?.items],
  );
  const selectedPipeline =
    pipelines.find((pipeline) => pipeline.id === selectedPipelineId) ?? pipelines[0];
  const materializationsQuery = useQuery({
    queryKey: ["feature-materializations", activeFeatureSetId],
    queryFn: () => listFeatureMaterializations(activeFeatureSetId, token ?? ""),
    enabled: Boolean(token && activeFeatureSetId),
  });
  const materializations = useMemo(
    () =>
      [...(materializationsQuery.data?.items ?? [])].sort(
        (left, right) => right.version - left.version,
      ),
    [materializationsQuery.data?.items],
  );
  const lineageQuery = useQuery({
    queryKey: ["feature-lineage", activeFeatureSetId],
    queryFn: () => listFeatureLineage(activeFeatureSetId, token ?? ""),
    enabled: Boolean(token && activeFeatureSetId),
  });
  const lineage = useMemo(
    () => lineageQuery.data?.items ?? [],
    [lineageQuery.data?.items],
  );
  const datasetsQuery = useQuery({
    queryKey: ["datasets", projectId],
    queryFn: () => listDatasets(projectId ?? "", token ?? ""),
    enabled: canLoadFeatureSets,
  });
  const datasets = useMemo(
    () => datasetsQuery.data?.items ?? [],
    [datasetsQuery.data?.items],
  );
  const selectedDataset =
    datasets.find((dataset) => dataset.id === selectedDatasetId) ?? datasets[0];
  const activePipelines = pipelines.filter((pipeline) => pipeline.status === "active");
  const requestedMaterializations = materializations.filter(
    (materialization) => materialization.status === "requested",
  );

  const createFeatureSetMutation = useMutation({
    mutationFn: () => {
      if (!projectId || !token) {
        throw new Error("Feature set creation requires project context.");
      }
      return createFeatureSet(
        projectId,
        {
          name: featureSetName.trim(),
          description: featureSetDescription.trim(),
          entity_key: entityKey.trim(),
        },
        token,
      );
    },
    onSuccess: (featureSet) => {
      queryClient.setQueryData<{ items: FeatureSet[]; next_cursor: string | null }>(
        ["feature-sets", projectId],
        (current) => ({
          items: [
            featureSet,
            ...(current?.items.filter((item) => item.id !== featureSet.id) ?? []),
          ],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Created feature set ${featureSet.name}.`);
      setSelectedFeatureSetId(featureSet.id);
      setSelectedPipelineId("");
      closeCreateFeatureSetForm();
      queryClient.invalidateQueries({ queryKey: ["feature-sets", projectId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Feature set creation failed.",
      );
    },
  });
  const registerDefinitionsMutation = useMutation({
    mutationFn: () => {
      if (!selectedFeatureSet || !token) {
        throw new Error("Feature definition registration requires a selected feature set.");
      }
      return registerFeatureDefinitions(
        selectedFeatureSet.id,
        {
          definitions: parseFeatureDefinitions(definitionsText),
        },
        token,
      );
    },
    onSuccess: (result) => {
      const featureSetId = result.items[0]?.feature_set_id ?? selectedFeatureSet?.id ?? "";
      queryClient.setQueryData<{ items: FeatureDefinition[]; next_cursor: string | null }>(
        ["feature-definitions", featureSetId],
        () => ({
          items: result.items,
          next_cursor: null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Registered ${result.items.length} feature definitions.`);
      setIsDefinitionFormOpen(false);
      queryClient.invalidateQueries({ queryKey: ["feature-definitions", featureSetId] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error
          ? error.message
          : "Feature definition registration failed.",
      );
    },
  });
  const registerPipelineMutation = useMutation({
    mutationFn: () => {
      if (!selectedFeatureSet || !token) {
        throw new Error("Pipeline registration requires a selected feature set.");
      }
      return registerFeaturePipeline(
        selectedFeatureSet.id,
        {
          name: pipelineName.trim(),
          source_dataset_id: selectedDataset?.id ?? null,
          code_ref: codeRef.trim(),
          schedule_cron: optionalString(scheduleCron),
        },
        token,
      );
    },
    onSuccess: (pipeline) => {
      queryClient.setQueryData<{ items: FeaturePipeline[]; next_cursor: string | null }>(
        ["feature-pipelines", pipeline.feature_set_id],
        (current) => ({
          items: [
            pipeline,
            ...(current?.items.filter((item) => item.id !== pipeline.id) ?? []),
          ],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Registered pipeline ${pipeline.name}.`);
      setSelectedPipelineId(pipeline.id);
      closePipelineForm();
      invalidateFeatureSetState(pipeline.feature_set_id);
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Feature pipeline registration failed.",
      );
    },
  });
  const materializeMutation = useMutation({
    mutationFn: (pipeline: FeaturePipeline) => {
      if (!token) {
        throw new Error("Materialization requires API access.");
      }
      return materializeFeaturePipeline(pipeline.id, token);
    },
    onSuccess: (materialization) => {
      queryClient.setQueryData<{
        items: FeatureMaterialization[];
        next_cursor: string | null;
      }>(["feature-materializations", materialization.feature_set_id], (current) => ({
        items: [
          materialization,
          ...(current?.items.filter((item) => item.id !== materialization.id) ?? []),
        ],
        next_cursor: current?.next_cursor ?? null,
      }));
      setOperationError(null);
      setOperationMessage(`Requested materialization v${materialization.version}.`);
      queryClient.invalidateQueries({
        queryKey: ["feature-materializations", materialization.feature_set_id],
      });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(
        error instanceof Error ? error.message : "Feature materialization failed.",
      );
    },
  });

  useEffect(() => {
    if (!selectedFeatureSetId && featureSets[0]) {
      setSelectedFeatureSetId(featureSets[0].id);
      return;
    }
    if (
      selectedFeatureSetId &&
      !featureSets.some((featureSet) => featureSet.id === selectedFeatureSetId)
    ) {
      setSelectedFeatureSetId(featureSets[0]?.id ?? "");
      setSelectedPipelineId("");
    }
  }, [featureSets, selectedFeatureSetId]);

  useEffect(() => {
    if (!selectedPipelineId && pipelines[0]) {
      setSelectedPipelineId(pipelines[0].id);
      return;
    }
    if (selectedPipelineId && !pipelines.some((pipeline) => pipeline.id === selectedPipelineId)) {
      setSelectedPipelineId(pipelines[0]?.id ?? "");
    }
  }, [pipelines, selectedPipelineId]);

  useEffect(() => {
    if (!selectedDatasetId && datasets[0]) {
      setSelectedDatasetId(datasets[0].id);
      return;
    }
    if (selectedDatasetId && !datasets.some((dataset) => dataset.id === selectedDatasetId)) {
      setSelectedDatasetId(datasets[0]?.id ?? "");
    }
  }, [datasets, selectedDatasetId]);

  function invalidateFeatureSetState(featureSetId: string) {
    queryClient.invalidateQueries({ queryKey: ["feature-pipelines", featureSetId] });
    queryClient.invalidateQueries({ queryKey: ["feature-lineage", featureSetId] });
    queryClient.invalidateQueries({ queryKey: ["feature-materializations", featureSetId] });
  }

  function closeCreateFeatureSetForm() {
    setIsCreateFeatureSetOpen(false);
    setFeatureSetName("merchant-signals");
    setFeatureSetDescription("Merchant behavior features for fraud scoring.");
    setEntityKey("merchant_id");
  }

  function closePipelineForm() {
    setIsPipelineFormOpen(false);
    setPipelineName("daily materialization");
    setCodeRef("git://feature-pipelines/merchant_signals.py");
    setScheduleCron("0 3 * * *");
  }

  function handleCreateFeatureSet(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (featureSetName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Feature set name must be at least 3 characters.");
      return;
    }
    if (!entityKey.trim()) {
      setOperationMessage(null);
      setOperationError("Entity key is required.");
      return;
    }
    createFeatureSetMutation.mutate();
  }

  function handleRegisterDefinitions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    registerDefinitionsMutation.mutate();
  }

  function handleRegisterPipeline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pipelineName.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Pipeline name must be at least 3 characters.");
      return;
    }
    if (codeRef.trim().length < 3) {
      setOperationMessage(null);
      setOperationError("Pipeline code reference is required.");
      return;
    }
    registerPipelineMutation.mutate();
  }

  return (
    <>
      <PageHeader
        eyebrow="Feature Platform"
        title="Feature Store"
        description="Feature sets, feature definitions, lineage, pipeline registration, and materialization lifecycle."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Feature Sets" value={String(featureSets.length)} detail="registered groups" />
        <MetricCard
          label="Features"
          value={String(definitions.length)}
          detail="selected set"
          tone="success"
        />
        <MetricCard
          label="Pipelines"
          value={String(activePipelines.length)}
          detail="active transforms"
        />
        <MetricCard
          label="Materializations"
          value={String(materializations.length)}
          detail={`${requestedMaterializations.length} requested`}
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
          title="Feature Set Inventory"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateFeatureSetOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Feature Set
            </button>
          }
        >
          {isCreateFeatureSetOpen ? (
            <CreateFeatureSetForm
              name={featureSetName}
              description={featureSetDescription}
              entityKey={entityKey}
              isPending={createFeatureSetMutation.isPending}
              onSubmit={handleCreateFeatureSet}
              onCancel={closeCreateFeatureSetForm}
              onNameChange={setFeatureSetName}
              onDescriptionChange={setFeatureSetDescription}
              onEntityKeyChange={setEntityKey}
            />
          ) : null}
          {!canLoadFeatureSets ? (
            <StateMessage message="No project context is selected." />
          ) : featureSetsQuery.error ? (
            <StateMessage message="Feature store request failed." tone="danger" />
          ) : featureSets.length === 0 ? (
            <StateMessage
              message={
                featureSetsQuery.isFetching
                  ? "Loading feature sets."
                  : "No feature sets registered for this project."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Feature Set</th>
                    <th>Entity Key</th>
                    <th>Status</th>
                    <th>Slug</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {featureSets.map((featureSet) => (
                    <FeatureSetRow
                      key={featureSet.id}
                      featureSet={featureSet}
                      selected={featureSet.id === selectedFeatureSet?.id}
                      onSelect={() => {
                        setSelectedFeatureSetId(featureSet.id);
                        setSelectedPipelineId("");
                      }}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel
          title="Feature Definitions"
          action={
            <button
              type="button"
              onClick={() => {
                setIsDefinitionFormOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <ListChecks className="h-4 w-4" />
              Definitions
            </button>
          }
        >
          {isDefinitionFormOpen ? (
            <DefinitionsForm
              definitionsText={definitionsText}
              isPending={registerDefinitionsMutation.isPending}
              hasFeatureSet={Boolean(selectedFeatureSet)}
              onSubmit={handleRegisterDefinitions}
              onCancel={() => setIsDefinitionFormOpen(false)}
              onDefinitionsTextChange={setDefinitionsText}
            />
          ) : null}
          {!selectedFeatureSet ? (
            <StateMessage message="Select a feature set before registering definitions." />
          ) : definitionsQuery.error ? (
            <StateMessage message="Feature definition request failed." tone="danger" />
          ) : definitions.length === 0 ? (
            <StateMessage
              message={
                definitionsQuery.isFetching
                  ? "Loading feature definitions."
                  : "No feature definitions are registered for this set."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Feature</th>
                    <th>Type</th>
                    <th>Nullable</th>
                    <th>Constraints</th>
                  </tr>
                </thead>
                <tbody>
                  {definitions.map((definition) => (
                    <DefinitionRow key={definition.id} definition={definition} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <DataPanel
          title="Pipelines"
          action={
            <button
              type="button"
              onClick={() => {
                setIsPipelineFormOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              Pipeline
            </button>
          }
        >
          {isPipelineFormOpen ? (
            <PipelineForm
              datasets={datasets}
              selectedDataset={selectedDataset}
              pipelineName={pipelineName}
              codeRef={codeRef}
              scheduleCron={scheduleCron}
              isPending={registerPipelineMutation.isPending}
              dependenciesLoading={datasetsQuery.isFetching}
              dependenciesError={Boolean(datasetsQuery.error)}
              hasFeatureSet={Boolean(selectedFeatureSet)}
              onSubmit={handleRegisterPipeline}
              onCancel={closePipelineForm}
              onDatasetChange={setSelectedDatasetId}
              onPipelineNameChange={setPipelineName}
              onCodeRefChange={setCodeRef}
              onScheduleCronChange={setScheduleCron}
            />
          ) : null}
          {!selectedFeatureSet ? (
            <StateMessage message="Select a feature set before registering pipelines." />
          ) : pipelinesQuery.error ? (
            <StateMessage message="Feature pipeline request failed." tone="danger" />
          ) : pipelines.length === 0 ? (
            <StateMessage
              message={
                pipelinesQuery.isFetching
                  ? "Loading feature pipelines."
                  : "No pipelines registered for this feature set."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Pipeline</th>
                    <th>Schedule</th>
                    <th>Status</th>
                    <th>Lineage</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pipelines.map((pipeline) => (
                    <PipelineRow
                      key={pipeline.id}
                      pipeline={pipeline}
                      selected={pipeline.id === selectedPipeline?.id}
                      isMaterializing={materializeMutation.isPending}
                      onSelect={() => setSelectedPipelineId(pipeline.id)}
                      onMaterialize={() => materializeMutation.mutate(pipeline)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Pipeline Detail">
          {!selectedPipeline ? (
            <StateMessage message="No feature pipeline is selected." />
          ) : (
            <PipelineDetail pipeline={selectedPipeline} />
          )}
        </DataPanel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="Materializations">
          {!selectedFeatureSet ? (
            <StateMessage message="Select a feature set before reviewing materializations." />
          ) : materializationsQuery.error ? (
            <StateMessage message="Feature materialization request failed." tone="danger" />
          ) : materializations.length === 0 ? (
            <StateMessage
              message={
                materializationsQuery.isFetching
                  ? "Loading feature materializations."
                  : "No materializations have been requested for this set."
              }
            />
          ) : (
            <div className="space-y-3">
              {materializations.map((materialization) => (
                <MaterializationCard key={materialization.id} materialization={materialization} />
              ))}
            </div>
          )}
        </DataPanel>

        <DataPanel title="Lineage">
          {!selectedFeatureSet ? (
            <StateMessage message="Select a feature set before reviewing lineage." />
          ) : lineageQuery.error ? (
            <StateMessage message="Feature lineage request failed." tone="danger" />
          ) : lineage.length === 0 ? (
            <StateMessage
              message={
                lineageQuery.isFetching
                  ? "Loading feature lineage."
                  : "No lineage links are recorded for this feature set."
              }
            />
          ) : (
            <div className="space-y-3">
              {lineage.map((link) => (
                <LineageCard key={link.id} link={link} />
              ))}
            </div>
          )}
        </DataPanel>
      </div>
    </>
  );
}

const defaultDefinitionsText = `[
  {
    "name": "chargeback_rate_30d",
    "dtype": "float",
    "description": "Rolling chargeback rate.",
    "nullable": false,
    "constraints": {
      "min": 0,
      "max": 1
    }
  },
  {
    "name": "avg_ticket_7d",
    "dtype": "float",
    "description": "Seven day average transaction value.",
    "nullable": false,
    "constraints": {
      "min": 0
    }
  }
]`;

type CreateFeatureSetFormProps = {
  name: string;
  description: string;
  entityKey: string;
  isPending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onEntityKeyChange: (value: string) => void;
};

function CreateFeatureSetForm({
  name,
  description,
  entityKey,
  isPending,
  onSubmit,
  onCancel,
  onNameChange,
  onDescriptionChange,
  onEntityKeyChange,
}: CreateFeatureSetFormProps) {
  return (
    <form
      aria-label="Create feature set"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(180px,1fr)_minmax(140px,0.7fr)]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Feature Set Name
          <input
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Entity Key
          <input
            value={entityKey}
            onChange={(event) => onEntityKeyChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
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
          Create feature set
        </button>
        <button
          type="button"
          aria-label="Cancel feature set creation"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

type DefinitionsFormProps = {
  definitionsText: string;
  isPending: boolean;
  hasFeatureSet: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onDefinitionsTextChange: (value: string) => void;
};

function DefinitionsForm({
  definitionsText,
  isPending,
  hasFeatureSet,
  onSubmit,
  onCancel,
  onDefinitionsTextChange,
}: DefinitionsFormProps) {
  return (
    <form
      aria-label="Register feature definitions"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
        Feature Definitions
        <textarea
          value={definitionsText}
          onChange={(event) => onDefinitionsTextChange(event.target.value)}
          rows={10}
          className="rounded border border-slate-200 bg-white px-3 py-2 font-mono text-xs font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      {!hasFeatureSet ? (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Select a feature set before registering definitions.
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={isPending || !hasFeatureSet}
          className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <ListChecks className="h-4 w-4" />
          Register definitions
        </button>
        <button
          type="button"
          aria-label="Cancel feature definition registration"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

type PipelineFormProps = {
  datasets: Dataset[];
  selectedDataset: Dataset | undefined;
  pipelineName: string;
  codeRef: string;
  scheduleCron: string;
  isPending: boolean;
  dependenciesLoading: boolean;
  dependenciesError: boolean;
  hasFeatureSet: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onDatasetChange: (value: string) => void;
  onPipelineNameChange: (value: string) => void;
  onCodeRefChange: (value: string) => void;
  onScheduleCronChange: (value: string) => void;
};

function PipelineForm({
  datasets,
  selectedDataset,
  pipelineName,
  codeRef,
  scheduleCron,
  isPending,
  dependenciesLoading,
  dependenciesError,
  hasFeatureSet,
  onSubmit,
  onCancel,
  onDatasetChange,
  onPipelineNameChange,
  onCodeRefChange,
  onScheduleCronChange,
}: PipelineFormProps) {
  const canSubmit = !isPending && !dependenciesLoading && !dependenciesError && hasFeatureSet;
  return (
    <form
      aria-label="Register feature pipeline"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(180px,1fr)_minmax(180px,1fr)]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Pipeline Name
          <input
            value={pipelineName}
            onChange={(event) => onPipelineNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Source Dataset
          <select
            value={selectedDataset?.id ?? ""}
            onChange={(event) => onDatasetChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          >
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
        Code Reference
        <input
          value={codeRef}
          onChange={(event) => onCodeRefChange(event.target.value)}
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      <label className="mt-3 grid gap-1 text-xs font-semibold uppercase text-steel">
        Schedule Cron
        <input
          value={scheduleCron}
          onChange={(event) => onScheduleCronChange(event.target.value)}
          className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
        />
      </label>
      {dependenciesError ? (
        <div className="mt-3 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-risk">
          Pipeline dependencies failed to load.
        </div>
      ) : datasets.length === 0 ? (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Pipeline lineage can be registered after a dataset is available.
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <GitBranch className="h-4 w-4" />
          Register pipeline
        </button>
        <button
          type="button"
          aria-label="Cancel feature pipeline registration"
          onClick={onCancel}
          className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}

function FeatureSetRow({
  featureSet,
  selected,
  onSelect,
}: {
  featureSet: FeatureSet;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{featureSet.name}</div>
        <div className="text-xs text-steel">{featureSet.description || "No description"}</div>
      </td>
      <td>{featureSet.entity_key}</td>
      <td>
        <span className={statusClassName(featureSet.status)}>{featureSet.status}</span>
      </td>
      <td>{featureSet.slug}</td>
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

function DefinitionRow({ definition }: { definition: FeatureDefinition }) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{definition.name}</div>
        <div className="text-xs text-steel">{definition.description || "No description"}</div>
      </td>
      <td>{definition.dtype}</td>
      <td>{definition.nullable ? "yes" : "no"}</td>
      <td className="max-w-[240px] truncate">{formatObject(definition.constraints)}</td>
    </tr>
  );
}

function PipelineRow({
  pipeline,
  selected,
  isMaterializing,
  onSelect,
  onMaterialize,
}: {
  pipeline: FeaturePipeline;
  selected: boolean;
  isMaterializing: boolean;
  onSelect: () => void;
  onMaterialize: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{pipeline.name}</div>
        <div className="max-w-[280px] truncate text-xs text-steel">{pipeline.code_ref}</div>
      </td>
      <td>{pipeline.schedule_cron || "manual"}</td>
      <td>
        <span className={statusClassName(pipeline.status)}>{pipeline.status}</span>
      </td>
      <td>{pipeline.source_dataset_id ? "dataset" : "none"}</td>
      <td>
        <div className="flex items-center gap-2">
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
          <button
            type="button"
            aria-label={`Materialize ${pipeline.name}`}
            onClick={onMaterialize}
            disabled={isMaterializing}
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-emerald-200 bg-emerald-50 text-signal transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Play className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

function PipelineDetail({ pipeline }: { pipeline: FeaturePipeline }) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{pipeline.name}</div>
          <div className="mt-1 break-all text-xs text-steel">{pipeline.code_ref}</div>
        </div>
        <span className={statusClassName(pipeline.status)}>{pipeline.status}</span>
      </div>
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-3">
        <SignalTile
          icon={<GitBranch className="h-4 w-4" />}
          label="Pipeline"
          value={pipeline.id.slice(0, 8)}
          detail={pipeline.schedule_cron || "manual"}
        />
        <SignalTile
          icon={<Database className="h-4 w-4" />}
          label="Source"
          value={pipeline.source_dataset_id ? "dataset" : "none"}
          detail={(pipeline.source_dataset_id ?? "no upstream").slice(0, 12)}
        />
        <SignalTile
          icon={<Route className="h-4 w-4" />}
          label="Feature Set"
          value={pipeline.feature_set_id.slice(0, 8)}
          detail="materialization target"
        />
      </div>
    </div>
  );
}

function MaterializationCard({
  materialization,
}: {
  materialization: FeatureMaterialization;
}) {
  return (
    <article className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">Materialization v{materialization.version}</div>
          <div className="mt-1 break-all text-xs text-steel">
            {materialization.offline_uri}
          </div>
        </div>
        <span className={statusClassName(materialization.status)}>
          {materialization.status}
        </span>
      </div>
      <div className="mt-3 grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-2">
        <SignalTile
          icon={<Activity className="h-4 w-4" />}
          label="Workflow"
          value={materialization.orchestrator_run_id}
          detail={materialization.id.slice(0, 8)}
        />
        <SignalTile
          icon={<PackageCheck className="h-4 w-4" />}
          label="Online Ref"
          value={materialization.online_ref ?? "offline only"}
          detail={materialization.pipeline_id.slice(0, 8)}
        />
      </div>
    </article>
  );
}

function LineageCard({ link }: { link: FeatureLineage }) {
  return (
    <article className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{link.upstream_type}</div>
          <div className="mt-1 break-all text-xs text-steel">{link.upstream_id}</div>
        </div>
        <span className="rounded bg-field px-2 py-1 text-xs font-medium">
          {link.feature_set_id.slice(0, 8)}
        </span>
      </div>
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
  if (status === "active" || status === "completed") {
    return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
  }
  if (status === "requested" || status === "running") {
    return "rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700";
  }
  if (status === "failed") {
    return "rounded bg-rose-50 px-2 py-1 text-xs font-medium text-risk";
  }
  return "rounded bg-field px-2 py-1 text-xs font-medium";
}

function parseFeatureDefinitions(value: string) {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error("Feature definitions must be valid JSON.");
  }
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("Feature definitions must be a non-empty JSON array.");
  }
  return parsed.map((definition) => {
    if (!isFeatureDefinitionPayload(definition)) {
      throw new Error(
        "Each feature definition must include name, dtype, description, nullable, and constraints.",
      );
    }
    return definition;
  });
}

function isFeatureDefinitionPayload(value: unknown): value is {
  name: string;
  dtype: string;
  description: string;
  nullable: boolean;
  constraints: Record<string, unknown>;
} {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const definition = value as Record<string, unknown>;
  return (
    typeof definition.name === "string" &&
    definition.name.trim().length > 0 &&
    typeof definition.dtype === "string" &&
    definition.dtype.trim().length > 0 &&
    typeof definition.description === "string" &&
    typeof definition.nullable === "boolean" &&
    Boolean(definition.constraints) &&
    typeof definition.constraints === "object" &&
    !Array.isArray(definition.constraints)
  );
}

function optionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formatObject(value: Record<string, unknown>): string {
  if (Object.keys(value).length === 0) {
    return "{}";
  }
  return JSON.stringify(value);
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}
