import { lazy, type ReactNode } from "react";

import { Navigate } from "../shared/routing/router";

const loadAlertsPage = () => import("../modules/alerts/pages/AlertsPage");
const AlertsPage = lazy(() =>
  loadAlertsPage().then(({ AlertsPage }) => ({ default: AlertsPage })),
);

const loadLoginPage = () => import("../modules/auth/pages/LoginPage");
const LoginPage = lazy(() =>
  loadLoginPage().then(({ LoginPage }) => ({ default: LoginPage })),
);

const loadDashboardPage = () =>
  import("../modules/dashboard/pages/DashboardPage");
const DashboardPage = lazy(() =>
  loadDashboardPage().then(({ DashboardPage }) => ({ default: DashboardPage })),
);

const loadDatasetsPage = () => import("../modules/datasets/pages/DatasetsPage");
const DatasetsPage = lazy(() =>
  loadDatasetsPage().then(({ DatasetsPage }) => ({ default: DatasetsPage })),
);

const loadDeploymentsPage = () =>
  import("../modules/deployments/pages/DeploymentsPage");
const DeploymentsPage = lazy(() =>
  loadDeploymentsPage().then(({ DeploymentsPage }) => ({
    default: DeploymentsPage,
  })),
);

const loadDriftDetectionPage = () =>
  import("../modules/drift_detection/pages/DriftDetectionPage");
const DriftDetectionPage = lazy(() =>
  loadDriftDetectionPage().then(({ DriftDetectionPage }) => ({
    default: DriftDetectionPage,
  })),
);

const loadExampleProjectsPage = () =>
  import("../modules/example_projects/pages/ExampleProjectsPage");
const ExampleProjectsPage = lazy(() =>
  loadExampleProjectsPage().then(({ ExampleProjectsPage }) => ({
    default: ExampleProjectsPage,
  })),
);

const loadExperimentsPage = () =>
  import("../modules/experiments/pages/ExperimentsPage");
const ExperimentsPage = lazy(() =>
  loadExperimentsPage().then(({ ExperimentsPage }) => ({
    default: ExperimentsPage,
  })),
);

const loadFeatureStorePage = () =>
  import("../modules/feature_store/pages/FeatureStorePage");
const FeatureStorePage = lazy(() =>
  loadFeatureStorePage().then(({ FeatureStorePage }) => ({
    default: FeatureStorePage,
  })),
);

const loadInferencePage = () =>
  import("../modules/inference/pages/InferencePage");
const InferencePage = lazy(() =>
  loadInferencePage().then(({ InferencePage }) => ({ default: InferencePage })),
);

const loadModelsPage = () => import("../modules/models/pages/ModelsPage");
const ModelsPage = lazy(() =>
  loadModelsPage().then(({ ModelsPage }) => ({ default: ModelsPage })),
);

const loadMonitoringPage = () =>
  import("../modules/monitoring/pages/MonitoringPage");
const MonitoringPage = lazy(() =>
  loadMonitoringPage().then(({ MonitoringPage }) => ({
    default: MonitoringPage,
  })),
);

const loadOperationalAuditPage = () =>
  import("../modules/operational_audit/pages/OperationalAuditPage");
const OperationalAuditPage = lazy(() =>
  loadOperationalAuditPage().then(({ OperationalAuditPage }) => ({
    default: OperationalAuditPage,
  })),
);

const loadProjectsPage = () => import("../modules/projects/pages/ProjectsPage");
const ProjectsPage = lazy(() =>
  loadProjectsPage().then(({ ProjectsPage }) => ({ default: ProjectsPage })),
);

const loadRetrainingPage = () =>
  import("../modules/retraining/pages/RetrainingPage");
const RetrainingPage = lazy(() =>
  loadRetrainingPage().then(({ RetrainingPage }) => ({
    default: RetrainingPage,
  })),
);

const loadReleaseEvidencePage = () =>
  import("../modules/release_evidence/pages/ReleaseEvidencePage");
const ReleaseEvidencePage = lazy(() =>
  loadReleaseEvidencePage().then(({ ReleaseEvidencePage }) => ({
    default: ReleaseEvidencePage,
  })),
);

const loadSettingsPage = () => import("../modules/settings/pages/SettingsPage");
const SettingsPage = lazy(() =>
  loadSettingsPage().then(({ SettingsPage }) => ({ default: SettingsPage })),
);

const loadTrainingRunsPage = () =>
  import("../modules/training_runs/pages/TrainingRunsPage");
const TrainingRunsPage = lazy(() =>
  loadTrainingRunsPage().then(({ TrainingRunsPage }) => ({
    default: TrainingRunsPage,
  })),
);

type AppRoute = {
  path: string;
  element: ReactNode;
  preload?: () => Promise<unknown>;
};

export const appRoutes: readonly AppRoute[] = [
  { path: "/", element: <DashboardPage />, preload: loadDashboardPage },
  { path: "/login", element: <LoginPage />, preload: loadLoginPage },
  { path: "/projects", element: <ProjectsPage />, preload: loadProjectsPage },
  {
    path: "/examples",
    element: <ExampleProjectsPage />,
    preload: loadExampleProjectsPage,
  },
  { path: "/datasets", element: <DatasetsPage />, preload: loadDatasetsPage },
  {
    path: "/feature-store",
    element: <FeatureStorePage />,
    preload: loadFeatureStorePage,
  },
  {
    path: "/experiments",
    element: <ExperimentsPage />,
    preload: loadExperimentsPage,
  },
  {
    path: "/training-runs",
    element: <TrainingRunsPage />,
    preload: loadTrainingRunsPage,
  },
  { path: "/models", element: <ModelsPage />, preload: loadModelsPage },
  {
    path: "/deployments",
    element: <DeploymentsPage />,
    preload: loadDeploymentsPage,
  },
  {
    path: "/inference",
    element: <InferencePage />,
    preload: loadInferencePage,
  },
  {
    path: "/monitoring",
    element: <MonitoringPage />,
    preload: loadMonitoringPage,
  },
  {
    path: "/drift",
    element: <DriftDetectionPage />,
    preload: loadDriftDetectionPage,
  },
  {
    path: "/retraining",
    element: <RetrainingPage />,
    preload: loadRetrainingPage,
  },
  { path: "/alerts", element: <AlertsPage />, preload: loadAlertsPage },
  {
    path: "/release-evidence",
    element: <ReleaseEvidencePage />,
    preload: loadReleaseEvidencePage,
  },
  {
    path: "/operational-audit",
    element: <OperationalAuditPage />,
    preload: loadOperationalAuditPage,
  },
  { path: "/settings", element: <SettingsPage />, preload: loadSettingsPage },
  { path: "*", element: <Navigate to="/" replace /> },
] as const;

const preloadedRoutes = new Map<string, Promise<unknown>>();

export function preloadRoute(path: string): void {
  const loader = appRoutes.find((route) => route.path === path)?.preload;
  if (!loader || preloadedRoutes.has(path)) {
    return;
  }

  preloadedRoutes.set(
    path,
    loader().catch(() => {
      preloadedRoutes.delete(path);
    }),
  );
}
