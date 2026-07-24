import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AlertsPage } from "../modules/alerts/pages/AlertsPage";
import { LoginPage } from "../modules/auth/pages/LoginPage";
import { DashboardPage } from "../modules/dashboard/pages/DashboardPage";
import { DatasetsPage } from "../modules/datasets/pages/DatasetsPage";
import { DeploymentsPage } from "../modules/deployments/pages/DeploymentsPage";
import { DriftDetectionPage } from "../modules/drift_detection/pages/DriftDetectionPage";
import { ExampleProjectsPage } from "../modules/example_projects/pages/ExampleProjectsPage";
import { ExperimentsPage } from "../modules/experiments/pages/ExperimentsPage";
import { FeatureStorePage } from "../modules/feature_store/pages/FeatureStorePage";
import { InferencePage } from "../modules/inference/pages/InferencePage";
import { ModelsPage } from "../modules/models/pages/ModelsPage";
import { MonitoringPage } from "../modules/monitoring/pages/MonitoringPage";
import { ProjectsPage } from "../modules/projects/pages/ProjectsPage";
import { RetrainingPage } from "../modules/retraining/pages/RetrainingPage";
import { SettingsPage } from "../modules/settings/pages/SettingsPage";
import { TrainingRunsPage } from "../modules/training_runs/pages/TrainingRunsPage";
import { Shell } from "../shared/ui/Shell";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/examples" element={<ExampleProjectsPage />} />
            <Route path="/datasets" element={<DatasetsPage />} />
            <Route path="/feature-store" element={<FeatureStorePage />} />
            <Route path="/experiments" element={<ExperimentsPage />} />
            <Route path="/training-runs" element={<TrainingRunsPage />} />
            <Route path="/models" element={<ModelsPage />} />
            <Route path="/deployments" element={<DeploymentsPage />} />
            <Route path="/inference" element={<InferencePage />} />
            <Route path="/monitoring" element={<MonitoringPage />} />
            <Route path="/drift" element={<DriftDetectionPage />} />
            <Route path="/retraining" element={<RetrainingPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
