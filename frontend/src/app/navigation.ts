import {
  AlertTriangle,
  BookOpen,
  Boxes,
  BrainCircuit,
  Database,
  GitBranch,
  FlaskConical,
  Gauge,
  Home,
  RadioTower,
  Radar,
  RefreshCw,
  Rocket,
  Settings,
  Workflow
} from "lucide-react";

export const navigationItems = [
  { label: "Dashboard", path: "/", icon: Home },
  { label: "Projects", path: "/projects", icon: Boxes },
  { label: "Examples", path: "/examples", icon: BookOpen },
  { label: "Datasets", path: "/datasets", icon: Database },
  { label: "Feature Store", path: "/feature-store", icon: GitBranch },
  { label: "Experiments", path: "/experiments", icon: FlaskConical },
  { label: "Training Runs", path: "/training-runs", icon: Workflow },
  { label: "Models", path: "/models", icon: BrainCircuit },
  { label: "Deployments", path: "/deployments", icon: Rocket },
  { label: "Inference", path: "/inference", icon: RadioTower },
  { label: "Monitoring", path: "/monitoring", icon: Gauge },
  { label: "Drift", path: "/drift", icon: Radar },
  { label: "Retraining", path: "/retraining", icon: RefreshCw },
  { label: "Alerts", path: "/alerts", icon: AlertTriangle },
  { label: "Settings", path: "/settings", icon: Settings }
] as const;
