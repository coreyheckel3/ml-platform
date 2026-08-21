import type { Page, Route } from "@playwright/test";

const organizationId = "org-e2e";
const userId = "user-e2e";
const baseProjectId = "project-fraud-detection-e2e";

type Entity = Record<string, unknown>;

type Project = Entity & {
  id: string;
  name: string;
  slug: string;
  description: string;
};

type Dataset = Entity & {
  id: string;
  project_id: string;
  name: string;
  slug: string;
};

type DatasetVersion = Entity & {
  id: string;
  dataset_id: string;
  version: number;
  object_uri: string;
  content_hash: string;
  row_count: number;
  size_bytes: number;
  status: string;
};

type TrainingRun = Entity & {
  id: string;
  project_id: string;
  experiment_id: string;
  experiment_run_id: string;
  artifact_uri: string;
  metrics: Record<string, number>;
  status: string;
};

type ModelVersion = Entity & {
  id: string;
  registered_model_id: string;
  version: number;
  training_run_id: string;
  experiment_run_id: string;
  artifact_uri: string;
  metrics: Record<string, number>;
  status: string;
};

type DeploymentRevision = Entity & {
  id: string;
  deployment_id: string;
  revision: number;
  traffic_percentage: number;
  status: string;
};

type InferenceEndpoint = Entity & {
  id: string;
  project_id: string;
  deployment_id: string;
  deployment_revision_id: string;
  name: string;
  route_path: string;
  status: string;
};

type AlertRule = Entity & {
  id: string;
  project_id: string;
  name: string;
  severity: string;
  metric: string;
  threshold: number;
  window_seconds: number;
};

type AlertEvent = Entity & {
  id: string;
  project_id: string;
  endpoint_id: string | null;
  status: string;
  observed_value: number;
  threshold: number;
};

type ForgeMLApiMockState = {
  projects: Project[];
  auditLog: Entity[];
  releaseEvidenceReports: Entity[];
  datasetsByProject: Map<string, Dataset[]>;
  versionsByDataset: Map<string, DatasetVersion[]>;
  schemasByVersion: Map<string, Entity>;
  validationRunsByVersion: Map<string, Entity[]>;
  experimentsByProject: Map<string, Entity[]>;
  featureSetsByProject: Map<string, Entity[]>;
  trainingRunsByProject: Map<string, TrainingRun[]>;
  trainingEventsByRun: Map<string, Entity[]>;
  trainingLogsByRun: Map<string, Entity[]>;
  modelsByProject: Map<string, Entity[]>;
  versionsByModel: Map<string, ModelVersion[]>;
  deploymentsByProject: Map<string, Entity[]>;
  revisionsByDeployment: Map<string, DeploymentRevision[]>;
  healthChecksByRevision: Map<string, Entity[]>;
  deploymentEventsByDeployment: Map<string, Entity[]>;
  endpointsByProject: Map<string, InferenceEndpoint[]>;
  requestLogsByEndpoint: Map<string, Entity[]>;
  snapshotsByEndpoint: Map<string, Entity[]>;
  alertRulesByProject: Map<string, AlertRule[]>;
  alertEventsByProject: Map<string, AlertEvent[]>;
};

export async function installForgeMLApiMock(page: Page): Promise<void> {
  const state = createMockState();
  await page.route("**/health/ready", (route) =>
    fulfillJson(route, {
      status: "ready",
      service: "forgeml-api",
    }),
  );
  await page.route("**/api/v1/**", async (route) => {
    await handleApiRoute(route, state);
  });
}

async function handleApiRoute(
  route: Route,
  state: ForgeMLApiMockState,
): Promise<void> {
  const method = route.request().method();
  const path = new URL(route.request().url()).pathname;

  if (method === "POST" && path === "/api/v1/auth/login") {
    return fulfillJson(route, {
      access_token: "e2e-access-token",
      refresh_token: "e2e-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    });
  }

  if (method === "GET" && path === "/api/v1/auth/me") {
    return fulfillJson(route, {
      id: userId,
      email: "admin@forgeml.dev",
      organization_id: organizationId,
      permissions: [
        "projects:create",
        "training_runs:create",
        "model_versions:review",
        "deployments:rollback",
        "inference:predict",
        "admin:audit_log:read",
        "admin:release_evidence:read",
        "admin:release_evidence:retrieve",
      ],
    });
  }

  if (method === "POST" && path === "/api/v1/auth/refresh") {
    return fulfillJson(route, {
      access_token: "e2e-access-token-rotated",
      refresh_token: "e2e-refresh-token-rotated",
      token_type: "bearer",
      expires_in: 3600,
    });
  }

  if (method === "POST" && path === "/api/v1/auth/logout") {
    return fulfillJson(route, { revoked: true });
  }

  if (method === "GET" && path === "/api/v1/training-runner-profiles") {
    return fulfillJson(route, {
      items: [trainingRunnerProfile()],
      next_cursor: null,
    });
  }

  if (method === "GET" && path === "/api/v1/admin/audit-log") {
    const query = new URL(route.request().url()).searchParams;
    const actorType = query.get("actor_type");
    const action = query.get("action");
    const resourceType = query.get("resource_type");
    const items = state.auditLog.filter(
      (entry) =>
        (!actorType || entry.actor_type === actorType) &&
        (!action || entry.action === action) &&
        (!resourceType || entry.resource_type === resourceType),
    );
    return fulfillJson(route, listResponse(items));
  }

  if (method === "GET" && path === "/api/v1/admin/release-evidence/refresh/status") {
    return fulfillJson(route, releaseEvidenceRefreshStatus(state.releaseEvidenceReports));
  }

  if (method === "GET" && path === "/api/v1/admin/release-evidence/reports") {
    const query = new URL(route.request().url()).searchParams;
    const status = query.get("status");
    const limit = Number(query.get("limit") ?? "20");
    const reports = state.releaseEvidenceReports
      .filter((report) => !status || report.status === status)
      .slice(0, Number.isFinite(limit) ? limit : 20);
    return fulfillJson(route, listResponse(reports));
  }

  if (method === "POST" && path === "/api/v1/admin/release-evidence/reports/retrieve") {
    const report = releaseEvidenceReport(
      `release-evidence-report-${state.releaseEvidenceReports.length + 1}`,
      "passed",
      "2026-08-17T16:30:00Z",
    );
    const auditAction =
      report.status === "passed"
        ? "release_evidence.retrieve"
        : "release_evidence.retrieve_failed";
    state.releaseEvidenceReports = [report, ...state.releaseEvidenceReports];
    state.auditLog = [
      auditLogEntry({
        id: `audit-${report.id}`,
        action: auditAction,
        resourceType: "release_evidence_report",
        resourceId: stringValue(report.id, "release-evidence-report"),
        metadata: {
          status: "passed",
          provider: "github_actions",
          repository: "coreyheckel3/ml-platform",
          branch: "main",
        },
        createdAt: stringValue(report.created_at, "2026-08-17T16:30:00Z"),
      }),
      ...state.auditLog,
    ];
    return fulfillJson(route, report, 201);
  }

  const releaseEvidenceReportMatch = path.match(
    /^\/api\/v1\/admin\/release-evidence\/reports\/([^/]+)$/,
  );
  if (method === "GET" && releaseEvidenceReportMatch) {
    const [, reportId] = releaseEvidenceReportMatch;
    const report = state.releaseEvidenceReports.find((item) => item.id === reportId);
    if (!report) {
      return fulfillJson(route, { detail: "Release evidence report not found" }, 404);
    }
    return fulfillJson(route, report);
  }

  if (method === "GET" && path === "/api/v1/projects") {
    return fulfillJson(route, listResponse(state.projects));
  }

  if (method === "POST" && path === "/api/v1/projects") {
    const body = await readJsonBody(route);
    const name = stringValue(body.name, "Untitled ML Platform");
    const project = projectRecord(
      `project-${slugify(name)}`,
      name,
      stringValue(body.description, "ML platform workspace"),
    );
    state.projects = [project, ...state.projects];
    seedProjectDependencies(state, project.id, name, false);
    return fulfillJson(route, project);
  }

  const monitoringSummaryMatch = path.match(
    /^\/api\/v1\/projects\/([^/]+)\/monitoring\/summary$/,
  );
  if (method === "GET" && monitoringSummaryMatch) {
    const [, projectId] = monitoringSummaryMatch;
    return fulfillJson(route, buildMonitoringSummary(state, projectId));
  }

  const monitoringEndpointsMatch = path.match(
    /^\/api\/v1\/projects\/([^/]+)\/monitoring\/inference-endpoints$/,
  );
  if (method === "GET" && monitoringEndpointsMatch) {
    const [, projectId] = monitoringEndpointsMatch;
    return fulfillJson(route, listResponse(buildEndpointMonitoring(state, projectId)));
  }

  const projectResourceMatch = path.match(/^\/api\/v1\/projects\/([^/]+)\/([^/]+)$/);
  if (projectResourceMatch) {
    const [, projectId, resource] = projectResourceMatch;
    ensureProjectDependencies(state, projectId);
    return handleProjectResource(route, state, projectId, resource, method);
  }

  const datasetVersionsMatch = path.match(/^\/api\/v1\/datasets\/([^/]+)\/versions$/);
  if (datasetVersionsMatch) {
    const [, datasetId] = datasetVersionsMatch;
    if (method === "GET") {
      return fulfillJson(route, listResponse(state.versionsByDataset.get(datasetId) ?? []));
    }
    if (method === "POST") {
      return createDatasetVersion(route, state, datasetId);
    }
  }

  const datasetVersionActionMatch = path.match(
    /^\/api\/v1\/dataset-versions\/([^/]+)\/([^/]+)$/,
  );
  if (datasetVersionActionMatch) {
    const [, versionId, action] = datasetVersionActionMatch;
    return handleDatasetVersionAction(route, state, method, versionId, action);
  }

  const trainingRunMatch = path.match(/^\/api\/v1\/training-runs\/([^/]+)(?:\/([^/]+))?$/);
  if (trainingRunMatch) {
    const [, runId, action] = trainingRunMatch;
    return handleTrainingRunAction(route, state, method, runId, action);
  }

  const modelVersionsMatch = path.match(/^\/api\/v1\/models\/([^/]+)\/versions$/);
  if (method === "GET" && modelVersionsMatch) {
    const [, modelId] = modelVersionsMatch;
    return fulfillJson(route, listResponse(state.versionsByModel.get(modelId) ?? []));
  }

  const promoteModelMatch = path.match(
    /^\/api\/v1\/models\/([^/]+)\/versions\/promote-training-run$/,
  );
  if (method === "POST" && promoteModelMatch) {
    const [, modelId] = promoteModelMatch;
    return promoteTrainingRun(route, state, modelId);
  }

  const modelVersionActionMatch = path.match(
    /^\/api\/v1\/model-versions\/([^/]+)\/([^/]+)$/,
  );
  if (method === "POST" && modelVersionActionMatch) {
    const [, versionId, action] = modelVersionActionMatch;
    return handleModelVersionAction(route, state, versionId, action);
  }

  const deploymentRevisionsMatch = path.match(
    /^\/api\/v1\/deployments\/([^/]+)\/revisions$/,
  );
  if (deploymentRevisionsMatch) {
    const [, deploymentId] = deploymentRevisionsMatch;
    if (method === "GET") {
      return fulfillJson(
        route,
        listResponse(state.revisionsByDeployment.get(deploymentId) ?? []),
      );
    }
    if (method === "POST") {
      return createDeploymentRevision(route, state, deploymentId);
    }
  }

  const deploymentEventsMatch = path.match(/^\/api\/v1\/deployments\/([^/]+)\/events$/);
  if (method === "GET" && deploymentEventsMatch) {
    const [, deploymentId] = deploymentEventsMatch;
    return fulfillJson(
      route,
      listResponse(state.deploymentEventsByDeployment.get(deploymentId) ?? []),
    );
  }

  const deploymentRevisionActionMatch = path.match(
    /^\/api\/v1\/deployment-revisions\/([^/]+)\/([^/]+)$/,
  );
  if (deploymentRevisionActionMatch) {
    const [, revisionId, action] = deploymentRevisionActionMatch;
    return handleDeploymentRevisionAction(route, state, method, revisionId, action);
  }

  const inferenceEndpointActionMatch = path.match(
    /^\/api\/v1\/inference-endpoints\/([^/]+)\/([^/]+)$/,
  );
  if (inferenceEndpointActionMatch) {
    const [, endpointId, action] = inferenceEndpointActionMatch;
    return handleInferenceEndpointAction(route, state, method, endpointId, action);
  }

  const alertRuleEvaluateMatch = path.match(/^\/api\/v1\/alert-rules\/([^/]+)\/evaluate$/);
  if (method === "POST" && alertRuleEvaluateMatch) {
    const [, ruleId] = alertRuleEvaluateMatch;
    return evaluateAlertRule(route, state, ruleId);
  }

  return fulfillJson(route, { detail: `Unhandled E2E API route: ${method} ${path}` }, 500);
}

async function handleProjectResource(
  route: Route,
  state: ForgeMLApiMockState,
  projectId: string,
  resource: string,
  method: string,
): Promise<void> {
  if (resource === "datasets") {
    if (method === "GET") {
      return fulfillJson(route, listResponse(state.datasetsByProject.get(projectId) ?? []));
    }
    if (method === "POST") {
      return createDataset(route, state, projectId);
    }
  }

  if (resource === "experiments" && method === "GET") {
    return fulfillJson(route, listResponse(state.experimentsByProject.get(projectId) ?? []));
  }

  if (resource === "feature-sets" && method === "GET") {
    return fulfillJson(route, listResponse(state.featureSetsByProject.get(projectId) ?? []));
  }

  if (resource === "training-runs") {
    if (method === "GET") {
      return fulfillJson(route, listResponse(state.trainingRunsByProject.get(projectId) ?? []));
    }
    if (method === "POST") {
      return startTrainingRun(route, state, projectId);
    }
  }

  if (resource === "models" && method === "GET") {
    return fulfillJson(route, listResponse(state.modelsByProject.get(projectId) ?? []));
  }

  if (resource === "deployments") {
    if (method === "GET") {
      return fulfillJson(route, listResponse(state.deploymentsByProject.get(projectId) ?? []));
    }
    if (method === "POST") {
      return createDeployment(route, state, projectId);
    }
  }

  if (resource === "inference-endpoints") {
    if (method === "GET") {
      return fulfillJson(route, listResponse(state.endpointsByProject.get(projectId) ?? []));
    }
    if (method === "POST") {
      return createInferenceEndpoint(route, state, projectId);
    }
  }

  if (resource === "alert-rules" && method === "GET") {
    return fulfillJson(route, listResponse(state.alertRulesByProject.get(projectId) ?? []));
  }

  if (resource === "alert-events" && method === "GET") {
    return fulfillJson(route, listResponse(state.alertEventsByProject.get(projectId) ?? []));
  }

  return fulfillJson(
    route,
    { detail: `Unhandled E2E project route: ${method} ${resource}` },
    500,
  );
}

async function createDataset(
  route: Route,
  state: ForgeMLApiMockState,
  projectId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const name = stringValue(body.name, "Feature Snapshot");
  const dataset: Dataset = {
    id: `dataset-${slugify(name)}`,
    organization_id: organizationId,
    project_id: projectId,
    name,
    slug: slugify(name),
    description: stringValue(body.description, "Dataset created from the control plane."),
    source_type: stringValue(body.source_type, "upload"),
    status: "active",
  };
  state.datasetsByProject.set(projectId, [
    dataset,
    ...(state.datasetsByProject.get(projectId) ?? []).filter((item) => item.id !== dataset.id),
  ]);
  state.versionsByDataset.set(dataset.id, []);
  return fulfillJson(route, dataset);
}

async function createDatasetVersion(
  route: Route,
  state: ForgeMLApiMockState,
  datasetId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const dataset = findDataset(state, datasetId);
  if (!dataset) {
    return fulfillJson(route, { detail: "Dataset not found" }, 404);
  }
  const nextVersion = (state.versionsByDataset.get(datasetId) ?? []).length + 1;
  const filename = stringValue(body.filename, "features.csv");
  const version: DatasetVersion = {
    id: `dataset-version-${dataset.slug}-${nextVersion}`,
    dataset_id: datasetId,
    version: nextVersion,
    object_uri: `s3://forgeml/datasets/${dataset.slug}/v${nextVersion}/${filename}`,
    content_hash: "",
    row_count: 0,
    size_bytes: 0,
    status: "pending_upload",
    created_by: userId,
  };
  state.versionsByDataset.set(datasetId, [
    version,
    ...(state.versionsByDataset.get(datasetId) ?? []),
  ]);
  state.validationRunsByVersion.set(version.id, []);
  return fulfillJson(route, {
    version,
    upload: {
      upload_url: `https://storage.local/${dataset.slug}/${filename}`,
      object_uri: version.object_uri,
      expires_at: "2026-08-04T23:59:00.000Z",
      required_headers: { "content-type": stringValue(body.content_type, "text/csv") },
    },
  });
}

async function handleDatasetVersionAction(
  route: Route,
  state: ForgeMLApiMockState,
  method: string,
  versionId: string,
  action: string,
): Promise<void> {
  if (method === "GET" && action === "schema") {
    return fulfillJson(route, state.schemasByVersion.get(versionId) ?? datasetSchema(versionId));
  }

  if (method === "GET" && action === "validation-runs") {
    return fulfillJson(route, listResponse(state.validationRunsByVersion.get(versionId) ?? []));
  }

  if (method === "POST" && action === "finalize") {
    const body = await readJsonBody(route);
    const version = findDatasetVersion(state, versionId);
    if (!version) {
      return fulfillJson(route, { detail: "Dataset version not found" }, 404);
    }
    const finalized: DatasetVersion = {
      ...version,
      object_uri: stringValue(body.object_uri, version.object_uri),
      content_hash: stringValue(body.content_hash, "sha256:e2e"),
      row_count: numberValue(body.row_count, 2),
      size_bytes: numberValue(body.size_bytes, 2048),
      status: "validated",
    };
    replaceDatasetVersion(state, finalized);
    state.schemasByVersion.set(versionId, datasetSchema(versionId));
    state.validationRunsByVersion.set(versionId, [
      validationRun(`validation-finalize-${versionId}`, versionId),
    ]);
    return fulfillJson(route, finalized);
  }

  if (method === "POST" && action === "validate") {
    const run = validationRun(`validation-manual-${versionId}`, versionId);
    state.validationRunsByVersion.set(versionId, [
      run,
      ...(state.validationRunsByVersion.get(versionId) ?? []),
    ]);
    return fulfillJson(route, run);
  }

  return fulfillJson(
    route,
    { detail: `Unhandled E2E dataset version route: ${method} ${action}` },
    500,
  );
}

async function startTrainingRun(
  route: Route,
  state: ForgeMLApiMockState,
  projectId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const nextIndex = (state.trainingRunsByProject.get(projectId) ?? []).length + 1;
  const runId = `training-run-${slugify(stringValue(body.run_name, "manual-run"))}-${nextIndex}`;
  const run: TrainingRun = {
    id: runId,
    organization_id: organizationId,
    project_id: projectId,
    experiment_id: stringValue(body.experiment_id, `experiment-${projectId}`),
    experiment_run_id: `experiment-run-${runId}`,
    dataset_version_id: nullableString(body.dataset_version_id),
    feature_set_id: nullableString(body.feature_set_id),
    algorithm: stringValue(body.algorithm, "xgboost"),
    model_type: stringValue(body.model_type, "xgboost"),
    objective_metric_name: stringValue(body.objective_metric_name, "auc"),
    hyperparameters: recordValue(body.hyperparameters),
    status: "queued",
    requested_by: userId,
    artifact_uri: `s3://forgeml/training-runs/${runId}`,
    orchestrator_run_id: `airflow-${runId}`,
    metrics: {},
    error_message: null,
    attempt_count: 0,
    max_attempts: 3,
    worker_id: null,
    lease_expires_at: null,
    last_heartbeat_at: null,
    queued_at: "2026-08-05T20:00:00Z",
    started_at: null,
    completed_at: null,
    next_retry_at: null,
  };
  state.trainingRunsByProject.set(projectId, [
    run,
    ...(state.trainingRunsByProject.get(projectId) ?? []),
  ]);
  state.trainingEventsByRun.set(runId, [
    trainingEvent(runId, "queued", "Started from the training UI."),
  ]);
  state.trainingLogsByRun.set(runId, [
    trainingLog(runId, 1, "info", "Training run was queued for execution."),
  ]);
  return fulfillJson(route, run);
}

async function handleTrainingRunAction(
  route: Route,
  state: ForgeMLApiMockState,
  method: string,
  runId: string,
  action: string | undefined,
): Promise<void> {
  if (method === "GET" && action === "orchestration-status") {
    const run = findTrainingRun(state, runId);
    return run
      ? fulfillJson(route, trainingOrchestrationStatus(run))
      : fulfillJson(route, { detail: "Training run not found" }, 404);
  }
  if (method === "GET" && action === "events") {
    return fulfillJson(route, listResponse(state.trainingEventsByRun.get(runId) ?? []));
  }
  if (method === "GET" && action === "logs") {
    return fulfillJson(route, listResponse(state.trainingLogsByRun.get(runId) ?? []));
  }
  if (method === "GET" && !action) {
    const run = findTrainingRun(state, runId);
    return run
      ? fulfillJson(route, run)
      : fulfillJson(route, { detail: "Training run not found" }, 404);
  }
  if (method === "POST" && action === "result") {
    const body = await readJsonBody(route);
    const run = findTrainingRun(state, runId);
    if (!run) {
      return fulfillJson(route, { detail: "Training run not found" }, 404);
    }
    const succeeded: TrainingRun = {
      ...run,
      status: stringValue(body.status, "succeeded"),
      metrics: numericRecordValue(body.metrics, { auc: 0.94 }),
      error_message: nullableString(body.error_message),
      attempt_count: Number(run.attempt_count ?? 1) || 1,
      worker_id: null,
      lease_expires_at: null,
      completed_at: "2026-08-05T20:10:00Z",
      next_retry_at: null,
    };
    replaceTrainingRun(state, succeeded);
    state.trainingEventsByRun.set(runId, [
      trainingEvent(runId, "succeeded", "Training run finished with status succeeded."),
      ...(state.trainingEventsByRun.get(runId) ?? []),
    ]);
    state.trainingLogsByRun.set(runId, [
      trainingLog(runId, 2, "info", "Training artifact metadata uploaded."),
      ...(state.trainingLogsByRun.get(runId) ?? []),
    ]);
    return fulfillJson(route, succeeded);
  }
  return fulfillJson(
    route,
    { detail: `Unhandled E2E training route: ${method} ${action ?? "detail"}` },
    500,
  );
}

async function promoteTrainingRun(
  route: Route,
  state: ForgeMLApiMockState,
  modelId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const trainingRunId = stringValue(body.training_run_id, "");
  const run = findTrainingRun(state, trainingRunId);
  if (!run) {
    return fulfillJson(route, { detail: "Training run not found" }, 404);
  }
  const nextVersion = (state.versionsByModel.get(modelId) ?? []).length + 1;
  const version: ModelVersion = {
    id: `model-version-${modelId}-${nextVersion}`,
    registered_model_id: modelId,
    version: nextVersion,
    training_run_id: trainingRunId,
    experiment_run_id: run.experiment_run_id,
    artifact_uri: `${run.artifact_uri}/model.json`,
    model_format: stringValue(body.model_format, "mlflow"),
    signature: recordValue(body.signature),
    metrics: run.metrics,
    status: "candidate",
    created_by: userId,
  };
  state.versionsByModel.set(modelId, [version, ...(state.versionsByModel.get(modelId) ?? [])]);
  return fulfillJson(route, version);
}

async function handleModelVersionAction(
  route: Route,
  state: ForgeMLApiMockState,
  versionId: string,
  action: string,
): Promise<void> {
  const version = findModelVersion(state, versionId);
  if (!version) {
    return fulfillJson(route, { detail: "Model version not found" }, 404);
  }

  if (action === "approval-request") {
    replaceModelVersion(state, { ...version, status: "pending_approval" });
    return fulfillJson(route, {
      id: `approval-${versionId}`,
      model_version_id: versionId,
      status: "requested",
      requested_by: userId,
      reviewer_id: null,
      comment: "Requesting approval",
      policy_snapshot: { source: "playwright-e2e" },
    });
  }

  if (action === "review") {
    const body = await readJsonBody(route);
    const status = stringValue(body.status, "approved");
    replaceModelVersion(state, { ...version, status });
    return fulfillJson(route, {
      id: `approval-review-${versionId}`,
      model_version_id: versionId,
      status,
      requested_by: userId,
      reviewer_id: userId,
      comment: stringValue(body.comment, "Approved"),
      policy_snapshot: { source: "playwright-e2e" },
    });
  }

  return fulfillJson(route, { detail: `Unhandled model version action: ${action}` }, 500);
}

async function createDeployment(
  route: Route,
  state: ForgeMLApiMockState,
  projectId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const name = stringValue(body.name, "Production API");
  const deployment: Entity = {
    id: `deployment-${slugify(name)}`,
    organization_id: organizationId,
    project_id: projectId,
    name,
    slug: slugify(name),
    description: stringValue(body.description, "Deployment target"),
    environment: stringValue(body.environment, "production"),
    status: "active",
    created_by: userId,
  };
  state.deploymentsByProject.set(projectId, [
    deployment,
    ...(state.deploymentsByProject.get(projectId) ?? []),
  ]);
  state.revisionsByDeployment.set(stringValue(deployment.id, ""), []);
  state.deploymentEventsByDeployment.set(stringValue(deployment.id, ""), [
    deploymentEvent(stringValue(deployment.id, ""), null, "created", "Deployment target was created."),
  ]);
  return fulfillJson(route, deployment);
}

async function createDeploymentRevision(
  route: Route,
  state: ForgeMLApiMockState,
  deploymentId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const nextRevision = (state.revisionsByDeployment.get(deploymentId) ?? []).length + 1;
  const revision: DeploymentRevision = {
    id: `deployment-revision-${deploymentId}-${nextRevision}`,
    deployment_id: deploymentId,
    model_version_id: stringValue(body.model_version_id, ""),
    revision: nextRevision,
    serving_image: stringValue(body.serving_image, "ghcr.io/forgeml/serving-runtime:latest"),
    runtime_config: recordValue(body.runtime_config),
    traffic_percentage: numberValue(body.traffic_percentage, 10),
    status: "deploying",
    orchestrator_deployment_id: `local-serving-${nextRevision}`,
    created_by: userId,
  };
  state.revisionsByDeployment.set(deploymentId, [
    revision,
    ...(state.revisionsByDeployment.get(deploymentId) ?? []),
  ]);
  prependDeploymentEvent(
    state,
    deploymentId,
    revision.id,
    "revision_created",
    "Deployment revision was submitted.",
  );
  return fulfillJson(route, revision);
}

async function handleDeploymentRevisionAction(
  route: Route,
  state: ForgeMLApiMockState,
  method: string,
  revisionId: string,
  action: string,
): Promise<void> {
  if (method === "GET" && action === "health-checks") {
    return fulfillJson(route, listResponse(state.healthChecksByRevision.get(revisionId) ?? []));
  }

  if (method === "POST" && action === "health-checks") {
    const body = await readJsonBody(route);
    const revision = findDeploymentRevision(state, revisionId);
    if (!revision) {
      return fulfillJson(route, { detail: "Deployment revision not found" }, 404);
    }
    const status = stringValue(body.status, "healthy");
    const check: Entity = {
      id: `health-${revisionId}-${status}`,
      deployment_revision_id: revisionId,
      status,
      latency_ms: numberValue(body.latency_ms, 85),
      error_rate: numberValue(body.error_rate, 0.01),
      details: recordValue(body.details),
    };
    replaceDeploymentRevision(state, { ...revision, status });
    state.healthChecksByRevision.set(revisionId, [
      check,
      ...(state.healthChecksByRevision.get(revisionId) ?? []),
    ]);
    prependDeploymentEvent(
      state,
      revision.deployment_id,
      revisionId,
      "health_checked",
      `Deployment revision health is ${status}.`,
    );
    return fulfillJson(route, check);
  }

  if (method === "POST" && action === "traffic") {
    const body = await readJsonBody(route);
    const revision = findDeploymentRevision(state, revisionId);
    if (!revision) {
      return fulfillJson(route, { detail: "Deployment revision not found" }, 404);
    }
    const updated = {
      ...revision,
      traffic_percentage: numberValue(body.traffic_percentage, 100),
      status: revision.status === "deploying" ? "healthy" : revision.status,
    };
    const allRevisions = state.revisionsByDeployment.get(revision.deployment_id) ?? [];
    state.revisionsByDeployment.set(
      revision.deployment_id,
      allRevisions.map((item) =>
        item.id === revisionId
          ? updated
          : { ...item, traffic_percentage: updated.traffic_percentage === 100 ? 0 : item.traffic_percentage },
      ),
    );
    prependDeploymentEvent(
      state,
      revision.deployment_id,
      revisionId,
      "traffic_updated",
      "Deployment traffic allocation was updated.",
    );
    return fulfillJson(route, updated);
  }

  return fulfillJson(route, { detail: `Unhandled deployment revision action: ${action}` }, 500);
}

async function createInferenceEndpoint(
  route: Route,
  state: ForgeMLApiMockState,
  projectId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const name = stringValue(body.name, "Fraud Scoring Endpoint");
  const endpoint: InferenceEndpoint = {
    id: `endpoint-${slugify(name)}`,
    organization_id: organizationId,
    project_id: projectId,
    deployment_id: stringValue(body.deployment_id, ""),
    deployment_revision_id: stringValue(body.deployment_revision_id, ""),
    name,
    slug: slugify(name),
    route_path: stringValue(body.route_path, `/inference/${slugify(name)}`),
    description: stringValue(body.description, "Online scoring endpoint"),
    status: "active",
    created_by: userId,
  };
  state.endpointsByProject.set(projectId, [
    endpoint,
    ...(state.endpointsByProject.get(projectId) ?? []),
  ]);
  state.requestLogsByEndpoint.set(endpoint.id, []);
  state.snapshotsByEndpoint.set(endpoint.id, []);
  return fulfillJson(route, endpoint);
}

async function handleInferenceEndpointAction(
  route: Route,
  state: ForgeMLApiMockState,
  method: string,
  endpointId: string,
  action: string,
): Promise<void> {
  if (method === "GET" && action === "requests") {
    return fulfillJson(route, listResponse(state.requestLogsByEndpoint.get(endpointId) ?? []));
  }

  if (method === "GET" && action === "metric-snapshots") {
    return fulfillJson(route, listResponse(state.snapshotsByEndpoint.get(endpointId) ?? []));
  }

  if (method === "POST" && action === "predict") {
    const body = await readJsonBody(route);
    const endpoint = findInferenceEndpoint(state, endpointId);
    if (!endpoint) {
      return fulfillJson(route, { detail: "Inference endpoint not found" }, 404);
    }
    const requestId = stringValue(body.request_id, `probe-${Date.now()}`);
    const log: Entity = {
      id: `request-log-${requestId}`,
      endpoint_id: endpointId,
      deployment_revision_id: endpoint.deployment_revision_id,
      request_id: requestId,
      status: "succeeded",
      latency_ms: 17.5,
      input_payload: recordValue(body.payload),
      output_payload: {
        prediction: 0.82,
        risk_band: "high",
        model_version_id: endpoint.deployment_revision_id,
      },
      error_message: null,
    };
    state.requestLogsByEndpoint.set(endpointId, [
      log,
      ...(state.requestLogsByEndpoint.get(endpointId) ?? []),
    ]);
    return fulfillJson(route, {
      log_id: log.id,
      endpoint_id: endpointId,
      deployment_revision_id: endpoint.deployment_revision_id,
      request_id: requestId,
      status: log.status,
      latency_ms: log.latency_ms,
      output_payload: log.output_payload,
    });
  }

  if (method === "POST" && action === "metric-snapshots") {
    const body = await readJsonBody(route);
    const snapshot: Entity = {
      id: `snapshot-${endpointId}-${(state.snapshotsByEndpoint.get(endpointId) ?? []).length + 1}`,
      endpoint_id: endpointId,
      window_seconds: numberValue(body.window_seconds, 300),
      prediction_count: numberValue(body.prediction_count, 1200),
      error_count: numberValue(body.error_count, 3),
      p50_latency_ms: numberValue(body.p50_latency_ms, 42),
      p95_latency_ms: numberValue(body.p95_latency_ms, 138),
    };
    state.snapshotsByEndpoint.set(endpointId, [
      snapshot,
      ...(state.snapshotsByEndpoint.get(endpointId) ?? []),
    ]);
    return fulfillJson(route, snapshot);
  }

  return fulfillJson(route, { detail: `Unhandled inference endpoint action: ${action}` }, 500);
}

async function evaluateAlertRule(
  route: Route,
  state: ForgeMLApiMockState,
  ruleId: string,
): Promise<void> {
  const body = await readJsonBody(route);
  const endpointId = stringValue(body.endpoint_id, "");
  const endpoint = findInferenceEndpoint(state, endpointId);
  const rule = findAlertRule(state, ruleId);
  if (!endpoint || !rule) {
    return fulfillJson(route, { detail: "Alert evaluation context not found" }, 404);
  }
  const summary = buildEndpointMonitoring(state, endpoint.project_id).find(
    (item) => item.endpoint_id === endpointId,
  );
  const observedValue =
    rule.metric === "inference_error_rate"
      ? summary?.error_rate ?? 0
      : summary?.p95_latency_ms ?? 0;
  const triggered = observedValue > rule.threshold;
  const event = triggered
    ? alertEvent(
        `alert-event-${ruleId}-${endpointId}`,
        rule,
        endpoint,
        observedValue,
        "open",
      )
    : null;
  if (event) {
    state.alertEventsByProject.set(endpoint.project_id, [
      event,
      ...(state.alertEventsByProject.get(endpoint.project_id) ?? []),
    ]);
  }
  return fulfillJson(route, {
    rule_id: ruleId,
    endpoint_id: endpointId,
    triggered,
    observed_value: observedValue,
    event,
  });
}

function createMockState(): ForgeMLApiMockState {
  const state: ForgeMLApiMockState = {
    projects: [
      projectRecord(
        baseProjectId,
        "Fraud Detection",
        "Payment risk scoring and chargeback prevention.",
      ),
    ],
    auditLog: seedAuditLogEntries(),
    releaseEvidenceReports: [
      releaseEvidenceReport(
        "release-evidence-report-main-1",
        "passed",
        "2026-08-17T15:00:00Z",
      ),
    ],
    datasetsByProject: new Map(),
    versionsByDataset: new Map(),
    schemasByVersion: new Map(),
    validationRunsByVersion: new Map(),
    experimentsByProject: new Map(),
    featureSetsByProject: new Map(),
    trainingRunsByProject: new Map(),
    trainingEventsByRun: new Map(),
    trainingLogsByRun: new Map(),
    modelsByProject: new Map(),
    versionsByModel: new Map(),
    deploymentsByProject: new Map(),
    revisionsByDeployment: new Map(),
    healthChecksByRevision: new Map(),
    deploymentEventsByDeployment: new Map(),
    endpointsByProject: new Map(),
    requestLogsByEndpoint: new Map(),
    snapshotsByEndpoint: new Map(),
    alertRulesByProject: new Map(),
    alertEventsByProject: new Map(),
  };
  seedProjectDependencies(state, baseProjectId, "Fraud Detection", true);
  return state;
}

function ensureProjectDependencies(state: ForgeMLApiMockState, projectId: string): void {
  if (!state.experimentsByProject.has(projectId)) {
    seedProjectDependencies(state, projectId, "ML Project", false);
  }
}

function seedProjectDependencies(
  state: ForgeMLApiMockState,
  projectId: string,
  label: string,
  includeDataset: boolean,
): void {
  const slug = slugify(label);
  const modelId = `model-${projectId}`;
  const deploymentId = `deployment-${projectId}`;
  state.experimentsByProject.set(projectId, [
    {
      id: `experiment-${projectId}`,
      organization_id: organizationId,
      project_id: projectId,
      name: `${label} Experiment`,
      slug: `${slug}-experiment`,
      description: `${label} model training.`,
      owner_user_id: userId,
      status: "active",
    },
  ]);
  state.featureSetsByProject.set(projectId, [
    {
      id: `feature-set-${projectId}`,
      organization_id: organizationId,
      project_id: projectId,
      name: `${label} Features`,
      slug: `${slug}-features`,
      description: `${label} online and offline features.`,
      entity_key: "account_id",
      status: "active",
    },
  ]);
  state.modelsByProject.set(projectId, [
    {
      id: modelId,
      organization_id: organizationId,
      project_id: projectId,
      name: `${label} XGB`,
      slug: `${slug}-xgb`,
      description: `${label} model registry entry.`,
      task_type: "classification",
      owner_user_id: userId,
      status: "active",
    },
  ]);
  state.versionsByModel.set(modelId, []);
  state.deploymentsByProject.set(projectId, [
    {
      id: deploymentId,
      organization_id: organizationId,
      project_id: projectId,
      name: `${label} API`,
      slug: `${slug}-api`,
      description: `${label} online serving target.`,
      environment: "production",
      status: "active",
      created_by: userId,
    },
  ]);
  state.revisionsByDeployment.set(deploymentId, []);
  state.deploymentEventsByDeployment.set(deploymentId, [
    deploymentEvent(deploymentId, null, "created", "Deployment target was created."),
  ]);
  state.trainingRunsByProject.set(projectId, []);
  state.endpointsByProject.set(projectId, []);
  state.alertRulesByProject.set(projectId, [alertRule(projectId, label)]);
  state.alertEventsByProject.set(projectId, []);

  if (!includeDataset) {
    state.datasetsByProject.set(projectId, []);
    return;
  }

  const dataset = datasetRecord(
    projectId,
    "Fraud Labels",
    "Validated payment labels.",
  );
  const version = datasetVersionRecord(dataset, 1, "validated");
  state.datasetsByProject.set(projectId, [dataset]);
  state.versionsByDataset.set(dataset.id, [version]);
  state.schemasByVersion.set(version.id, datasetSchema(version.id));
  state.validationRunsByVersion.set(version.id, [
    validationRun(`validation-${version.id}`, version.id),
  ]);
}

function projectRecord(id: string, name: string, description: string): Project {
  return {
    id,
    organization_id: organizationId,
    name,
    slug: slugify(name),
    status: "active",
    description,
    owner_user_id: userId,
  };
}

function seedAuditLogEntries(): Entity[] {
  return [
    auditLogEntry({
      id: "audit-deployment-rollback",
      action: "deployments.rollback",
      resourceType: "deployment",
      resourceId: `deployment-${baseProjectId}`,
      metadata: { project_id: baseProjectId, from_revision: 2, to_revision: 1 },
      createdAt: "2026-08-13T18:30:00Z",
    }),
    auditLogEntry({
      id: "audit-retraining-trigger",
      action: "retraining_runs.trigger",
      resourceType: "retraining_run",
      resourceId: "retraining-run-fraud-daily",
      metadata: {
        project_id: baseProjectId,
        training_run_id: "training-run-fraud-daily",
        orchestrator_run_id: "workflow:fraud-retrain",
      },
      createdAt: "2026-08-13T18:10:00Z",
    }),
    auditLogEntry({
      id: "audit-model-review",
      action: "model_versions.review",
      resourceType: "model_version",
      resourceId: "model-version-fraud-xgb-1",
      metadata: { project_id: baseProjectId, decision: "approved" },
      createdAt: "2026-08-13T17:50:00Z",
    }),
    auditLogEntry({
      id: "audit-auth-login",
      action: "auth.login",
      resourceType: "user",
      resourceId: userId,
      metadata: { email: "admin@forgeml.dev" },
      createdAt: "2026-08-13T17:30:00Z",
    }),
  ];
}

function auditLogEntry({
  id,
  action,
  resourceType,
  resourceId,
  metadata,
  createdAt,
}: {
  id: string;
  action: string;
  resourceType: string;
  resourceId: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}): Entity {
  return {
    id,
    organization_id: organizationId,
    actor_type: "user",
    actor_id: userId,
    action,
    resource_type: resourceType,
    resource_id: resourceId,
    metadata,
    created_at: createdAt,
  };
}

function releaseEvidenceReport(id: string, status: string, createdAt: string): Entity {
  return {
    id,
    organization_id: organizationId,
    requested_by_user_id: userId,
    provider: "github_actions",
    status,
    repository: "coreyheckel3/ml-platform",
    branch: "main",
    workflow: "ci.yml",
    artifact_name: "forgeml-release-manifest",
    run_id: "31826993476",
    run_url: "https://github.com/coreyheckel3/ml-platform/actions/runs/31826993476",
    manifest_git_sha: "e4cd6aa4f9ce0000000000000000000000000000",
    manifest_git_branch: "main",
    ci_run_url: "https://github.com/coreyheckel3/ml-platform/actions/runs/31826993476",
    artifact_count: 39,
    quality_gate_count: 28,
    missing_artifacts: [],
    missing_quality_gates: [],
    comparison: {
      passed: status === "passed",
      required_artifacts_present: true,
      required_quality_gates_present: true,
      ci_evidence_present: true,
    },
    manifest_summary: {
      git_sha: "e4cd6aa4f9ce0000000000000000000000000000",
      git_branch: "main",
      artifact_names: [
        "external_training_package_contract",
        "release_evidence_drilldown_api_contract",
        "release_evidence_scheduled_refresh_contract",
        "release_evidence_notifications_contract",
      ],
      quality_gate_names: [
        "external_training_package_contract",
        "release_evidence_drilldown_api_contract",
        "release_evidence_scheduled_refresh_contract",
        "release_evidence_notifications_contract",
      ],
      ci_run_url: "https://github.com/coreyheckel3/ml-platform/actions/runs/31826993476",
    },
    report: {
      schema_version: "forgeml.release_evidence_retrieval.v1",
      status,
    },
    error_message: null,
    created_at: createdAt,
  };
}

function releaseEvidenceRefreshStatus(reports: Entity[]): Entity {
  const latestReport = reports[0] ?? null;
  const lastSuccessfulReport =
    reports.find((report) => report.status === "passed") ?? null;
  const staleReasons: string[] = [];
  if (!latestReport) {
    staleReasons.push("no_reports");
  }
  if (!lastSuccessfulReport) {
    staleReasons.push("no_successful_report");
  }
  if (latestReport && latestReport.status !== "passed") {
    staleReasons.push("latest_report_failed");
  }
  const stale = staleReasons.includes("no_successful_report");
  const status = !latestReport
    ? "missing"
    : stale
      ? "stale"
      : latestReport.status !== "passed"
        ? "attention"
        : "fresh";
  return {
    schema_version: "forgeml.release_evidence_refresh_status.v1",
    organization_id: organizationId,
    provider: "github_actions",
    repository: "coreyheckel3/ml-platform",
    branch: "main",
    workflow: "ci.yml",
    artifact_name: "forgeml-release-manifest",
    status,
    stale,
    stale_after_seconds: 86_400,
    refresh_interval_seconds: 3_600,
    latest_report: latestReport,
    last_successful_report: lastSuccessfulReport,
    latest_report_age_seconds: latestReport ? 1_800 : null,
    last_success_age_seconds: lastSuccessfulReport ? 1_800 : null,
    next_refresh_at: "2026-08-17T17:00:00Z",
    checked_at: "2026-08-17T16:30:00Z",
    stale_reasons: staleReasons,
    recommended_action: status === "fresh" ? "wait_until_next_refresh" : "retrieve_now",
    operator_command:
      "PYTHONPATH=backend/src:. python scripts/ops/refresh_release_evidence.py --base-url http://127.0.0.1:8001 --once --stale-after-seconds 86400",
    notification_policy: {
      enabled: false,
      channel_type: "noop",
      target: "audit-log only",
      failure_statuses: ["failed"],
      escalation_window_seconds: 1_800,
      escalation_command:
        "PYTHONPATH=backend/src:. python scripts/ops/refresh_release_evidence.py --base-url http://127.0.0.1:8001 --once --force",
      delivery_audit_actions: [
        "release_evidence.notification_delivered",
        "release_evidence.notification_failed",
        "release_evidence.notification_skipped",
      ],
    },
  };
}

function datasetRecord(projectId: string, name: string, description: string): Dataset {
  return {
    id: `dataset-${slugify(name)}`,
    organization_id: organizationId,
    project_id: projectId,
    name,
    slug: slugify(name),
    description,
    source_type: "upload",
    status: "active",
  };
}

function datasetVersionRecord(
  dataset: Dataset,
  version: number,
  status: string,
): DatasetVersion {
  return {
    id: `dataset-version-${dataset.slug}-${version}`,
    dataset_id: dataset.id,
    version,
    object_uri: `s3://forgeml/datasets/${dataset.slug}/v${version}/features.csv`,
    content_hash: "sha256:e2e",
    row_count: 12000,
    size_bytes: 4096,
    status,
    created_by: userId,
  };
}

function datasetSchema(versionId: string): Entity {
  return {
    dataset_version_id: versionId,
    fields: [
      { name: "account_id", dtype: "string", nullable: false },
      { name: "amount", dtype: "float", nullable: false },
      { name: "is_fraud", dtype: "boolean", nullable: false },
    ],
    inferred: true,
    schema_hash: "schema-hash-e2e",
  };
}

function validationRun(id: string, versionId: string): Entity {
  return {
    id,
    dataset_version_id: versionId,
    status: "completed",
    report: {
      field_count: 3,
      row_count: 2,
      checks: ["schema_present", "metadata_valid"],
    },
    error_message: null,
  };
}

function trainingEvent(runId: string, eventType: string, message: string): Entity {
  return {
    id: `${runId}-${eventType}`,
    training_run_id: runId,
    event_type: eventType,
    message,
    metadata: { orchestrator_run_id: `airflow-${runId}` },
  };
}

function trainingLog(
  runId: string,
  sequence: number,
  level: string,
  message: string,
): Entity {
  return {
    id: `${runId}-log-${sequence}`,
    training_run_id: runId,
    sequence,
    level,
    logger: "training.scheduler",
    message,
    metadata: { orchestrator_run_id: `airflow-${runId}` },
    created_at: null,
  };
}

function trainingOrchestrationStatus(run: TrainingRun): Entity {
  const status = stringValue(run.status, "queued");
  const orchestratorRunId = stringValue(
    run.orchestrator_run_id,
    `airflow-${run.id}`,
  );
  return {
    training_run_id: run.id,
    orchestrator_run_id: orchestratorRunId,
    orchestrator: "airflow",
    external_status: status,
    mapped_training_status: status,
    is_terminal: ["succeeded", "failed", "canceled", "dead_lettered"].includes(
      status,
    ),
    external_url: `http://airflow.local/dags/forgeml_training_pipeline/grid?dag_run_id=${orchestratorRunId}`,
    metadata: {
      dag_id: "forgeml_training_pipeline",
      project_id: run.project_id,
      training_run_id: run.id,
    },
    observed_at: "2026-08-05T20:00:00Z",
  };
}

function trainingRunnerProfile(): Entity {
  return {
    slug: "conversational-movie-recommender",
    display_name: "Conversational Movie Recommender",
    runner_kind: "external_package",
    package_name: "conversational-movie-recommender",
    description: "Runs the external recommender package build CLI.",
    supported_algorithms: ["movie-rec-svd", "movie-rec-two-tower"],
    default_algorithm: "movie-rec-svd",
    default_model_type: "hybrid-recommender",
    objective_metric_name: "ndcg_at_k",
    default_hyperparameters: {
      "forgeml.external_training_profile": "conversational-movie-recommender",
      data_dir: "data/sample",
      write_metrics: true,
      eval_k: 5,
      eval_max_users: 20,
      quiet: true,
    },
    availability: {
      available: true,
      repo_root: "/Users/posh/Documents/GitHub/conversational-movie-recommender",
      executable_path:
        "/Users/posh/Documents/GitHub/conversational-movie-recommender/.venv/bin/movie-rec-build",
      data_dir: "/Users/posh/Documents/GitHub/conversational-movie-recommender/data/sample",
      missing: [],
    },
    command_preview: [
      "/repo/.venv/bin/movie-rec-build",
      "--data-dir",
      "/repo/data/sample",
      "--model-dir",
      "<artifact-root>/<training-run-id>/conversational-movie-recommender/model",
    ],
  };
}

function deploymentEvent(
  deploymentId: string,
  revisionId: string | null,
  eventType: string,
  message: string,
): Entity {
  return {
    id: `deployment-event-${deploymentId}-${eventType}-${revisionId ?? "target"}`,
    deployment_id: deploymentId,
    deployment_revision_id: revisionId,
    event_type: eventType,
    message,
    metadata: { source: "playwright-e2e" },
  };
}

function alertRule(projectId: string, label: string): AlertRule {
  return {
    id: `alert-rule-p95-${projectId}`,
    organization_id: organizationId,
    project_id: projectId,
    name: `${label} p95 latency breach`,
    slug: `${slugify(label)}-p95-latency-breach`,
    description: "Serving latency guardrail",
    severity: "critical",
    metric: "inference_p95_latency_ms",
    operator: "gt",
    threshold: 120,
    window_seconds: 300,
    enabled: true,
    created_by: userId,
  };
}

function alertEvent(
  id: string,
  rule: AlertRule,
  endpoint: InferenceEndpoint,
  observedValue: number,
  status: string,
): AlertEvent {
  return {
    id,
    organization_id: organizationId,
    project_id: endpoint.project_id,
    alert_rule_id: rule.id,
    endpoint_id: endpoint.id,
    severity: rule.severity,
    status,
    message: `${rule.name} triggered for ${endpoint.name}.`,
    observed_value: observedValue,
    threshold: rule.threshold,
    metadata: {
      metric: rule.metric,
      route_path: endpoint.route_path,
    },
    acknowledged_by: null,
    resolved_by: null,
  };
}

function buildMonitoringSummary(state: ForgeMLApiMockState, projectId: string): Entity {
  const endpoints = buildEndpointMonitoring(state, projectId);
  const predictionCount = endpoints.reduce(
    (total, endpoint) => total + endpoint.prediction_count,
    0,
  );
  const errorCount = endpoints.reduce((total, endpoint) => total + endpoint.error_count, 0);
  const requestCount = endpoints.reduce((total, endpoint) => total + endpoint.request_count, 0);
  const activeAlertCount = (state.alertEventsByProject.get(projectId) ?? []).filter(
    (event) => event.status === "open",
  ).length;
  return {
    project_id: projectId,
    inference_endpoint_count: endpoints.length,
    prediction_count: predictionCount,
    error_count: errorCount,
    request_count: requestCount,
    active_alert_count: activeAlertCount,
    error_rate: predictionCount === 0 ? 0 : errorCount / predictionCount,
    max_p95_latency_ms: Math.max(0, ...endpoints.map((endpoint) => endpoint.p95_latency_ms)),
  };
}

function buildEndpointMonitoring(
  state: ForgeMLApiMockState,
  projectId: string,
): Array<{
  endpoint_id: string;
  endpoint_name: string;
  route_path: string;
  status: string;
  deployment_id: string;
  deployment_revision_id: string;
  latest_window_seconds: number;
  prediction_count: number;
  error_count: number;
  request_count: number;
  error_rate: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
}> {
  return (state.endpointsByProject.get(projectId) ?? []).map((endpoint) => {
    const logs = state.requestLogsByEndpoint.get(endpoint.id) ?? [];
    const latestSnapshot = (state.snapshotsByEndpoint.get(endpoint.id) ?? [])[0];
    const predictionCount = numberValue(latestSnapshot?.prediction_count, logs.length);
    const errorCount = numberValue(
      latestSnapshot?.error_count,
      logs.filter((log) => log.status !== "succeeded").length,
    );
    return {
      endpoint_id: endpoint.id,
      endpoint_name: endpoint.name,
      route_path: endpoint.route_path,
      status: endpoint.status,
      deployment_id: endpoint.deployment_id,
      deployment_revision_id: endpoint.deployment_revision_id,
      latest_window_seconds: numberValue(latestSnapshot?.window_seconds, 300),
      prediction_count: predictionCount,
      error_count: errorCount,
      request_count: logs.length,
      error_rate: predictionCount === 0 ? 0 : errorCount / predictionCount,
      p50_latency_ms: numberValue(latestSnapshot?.p50_latency_ms, 17.5),
      p95_latency_ms: numberValue(latestSnapshot?.p95_latency_ms, 17.5),
    };
  });
}

function prependDeploymentEvent(
  state: ForgeMLApiMockState,
  deploymentId: string,
  revisionId: string | null,
  eventType: string,
  message: string,
): void {
  state.deploymentEventsByDeployment.set(deploymentId, [
    deploymentEvent(deploymentId, revisionId, eventType, message),
    ...(state.deploymentEventsByDeployment.get(deploymentId) ?? []),
  ]);
}

function findDataset(state: ForgeMLApiMockState, datasetId: string): Dataset | undefined {
  for (const datasets of state.datasetsByProject.values()) {
    const dataset = datasets.find((item) => item.id === datasetId);
    if (dataset) {
      return dataset;
    }
  }
  return undefined;
}

function findDatasetVersion(
  state: ForgeMLApiMockState,
  versionId: string,
): DatasetVersion | undefined {
  for (const versions of state.versionsByDataset.values()) {
    const version = versions.find((item) => item.id === versionId);
    if (version) {
      return version;
    }
  }
  return undefined;
}

function replaceDatasetVersion(
  state: ForgeMLApiMockState,
  replacement: DatasetVersion,
): void {
  const versions = state.versionsByDataset.get(replacement.dataset_id) ?? [];
  state.versionsByDataset.set(
    replacement.dataset_id,
    versions.map((version) => (version.id === replacement.id ? replacement : version)),
  );
}

function findTrainingRun(
  state: ForgeMLApiMockState,
  runId: string,
): TrainingRun | undefined {
  for (const runs of state.trainingRunsByProject.values()) {
    const run = runs.find((item) => item.id === runId);
    if (run) {
      return run;
    }
  }
  return undefined;
}

function replaceTrainingRun(state: ForgeMLApiMockState, replacement: TrainingRun): void {
  const runs = state.trainingRunsByProject.get(replacement.project_id) ?? [];
  state.trainingRunsByProject.set(
    replacement.project_id,
    runs.map((run) => (run.id === replacement.id ? replacement : run)),
  );
}

function findModelVersion(
  state: ForgeMLApiMockState,
  versionId: string,
): ModelVersion | undefined {
  for (const versions of state.versionsByModel.values()) {
    const version = versions.find((item) => item.id === versionId);
    if (version) {
      return version;
    }
  }
  return undefined;
}

function replaceModelVersion(state: ForgeMLApiMockState, replacement: ModelVersion): void {
  const versions = state.versionsByModel.get(replacement.registered_model_id) ?? [];
  state.versionsByModel.set(
    replacement.registered_model_id,
    versions.map((version) => (version.id === replacement.id ? replacement : version)),
  );
}

function findDeploymentRevision(
  state: ForgeMLApiMockState,
  revisionId: string,
): DeploymentRevision | undefined {
  for (const revisions of state.revisionsByDeployment.values()) {
    const revision = revisions.find((item) => item.id === revisionId);
    if (revision) {
      return revision;
    }
  }
  return undefined;
}

function replaceDeploymentRevision(
  state: ForgeMLApiMockState,
  replacement: DeploymentRevision,
): void {
  const revisions = state.revisionsByDeployment.get(replacement.deployment_id) ?? [];
  state.revisionsByDeployment.set(
    replacement.deployment_id,
    revisions.map((revision) => (revision.id === replacement.id ? replacement : revision)),
  );
}

function findInferenceEndpoint(
  state: ForgeMLApiMockState,
  endpointId: string,
): InferenceEndpoint | undefined {
  for (const endpoints of state.endpointsByProject.values()) {
    const endpoint = endpoints.find((item) => item.id === endpointId);
    if (endpoint) {
      return endpoint;
    }
  }
  return undefined;
}

function findAlertRule(state: ForgeMLApiMockState, ruleId: string): AlertRule | undefined {
  for (const rules of state.alertRulesByProject.values()) {
    const rule = rules.find((item) => item.id === ruleId);
    if (rule) {
      return rule;
    }
  }
  return undefined;
}

function listResponse<T>(items: T[]): { items: T[]; next_cursor: null } {
  return { items, next_cursor: null };
}

async function readJsonBody(route: Route): Promise<Entity> {
  const rawBody = route.request().postData();
  if (!rawBody) {
    return {};
  }
  const parsed = JSON.parse(rawBody) as unknown;
  return recordValue(parsed);
}

function fulfillJson(route: Route, payload: unknown, status = 200): Promise<void> {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function nullableString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function recordValue(value: unknown): Entity {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value as Entity;
}

function numericRecordValue(
  value: unknown,
  fallback: Record<string, number>,
): Record<string, number> {
  const record = recordValue(value);
  const entries = Object.entries(record).filter((entry): entry is [string, number] => {
    const [, entryValue] = entry;
    return typeof entryValue === "number" && Number.isFinite(entryValue);
  });
  return entries.length > 0 ? Object.fromEntries(entries) : fallback;
}
