import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  FolderKanban,
  KeyRound,
  Layers3,
  Plus,
  ShieldCheck,
  X,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { ACCESS_TOKEN_KEY, PROJECT_CONTEXT_KEY } from "../../auth/session/sessionStore";
import { createProject, listProjects, type Project } from "../api/projects";

type ProjectRow = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  status: string;
  description: string;
  owner_user_id: string;
  source: "api" | "local";
};

const exampleProjectRows: ProjectRow[] = [
  {
    id: "example-movie-recommendation",
    organization_id: "example-org",
    name: "Movie Recommendation",
    slug: "movie-recommendation",
    status: "active",
    description: "Ranking and candidate generation",
    owner_user_id: "example-owner",
    source: "local",
  },
  {
    id: "example-semantic-search",
    organization_id: "example-org",
    name: "Semantic Search",
    slug: "semantic-search",
    status: "active",
    description: "Embedding-based document retrieval",
    owner_user_id: "example-owner",
    source: "local",
  },
  {
    id: "example-fraud-detection",
    organization_id: "example-org",
    name: "Fraud Detection",
    slug: "fraud-detection",
    status: "active",
    description: "Payment risk scoring",
    owner_user_id: "example-owner",
    source: "local",
  },
];

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage(ACCESS_TOKEN_KEY);
  const canLoadProjects = Boolean(token);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState(
    () => readLocalStorage(PROJECT_CONTEXT_KEY) ?? "",
  );
  const [sessionProjects, setSessionProjects] = useState<ProjectRow[]>([]);
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => listProjects(token ?? ""),
    enabled: canLoadProjects,
  });
  const apiProjectRows = useMemo(
    () => (projectsQuery.data?.items ?? []).map(projectToRow),
    [projectsQuery.data?.items],
  );
  const projectRows = useMemo(
    () => [
      ...(canLoadProjects ? apiProjectRows : exampleProjectRows),
      ...sessionProjects,
    ],
    [apiProjectRows, canLoadProjects, sessionProjects],
  );
  const selectedProject =
    projectRows.find((project) => project.id === selectedProjectId) ?? projectRows[0];
  const activeProjects = projectRows.filter((project) => project.status === "active");
  const contextSource = selectedProject?.source === "api" ? "API project" : "local project";
  const createMutation = useMutation({
    mutationFn: (payload: { name: string; description: string }) =>
      createProject(payload, token ?? ""),
    onSuccess: (project) => {
      const row = projectToRow(project);
      queryClient.setQueryData<{ items: Project[]; next_cursor: string | null }>(
        ["projects"],
        (current) => ({
          items: [project, ...(current?.items.filter((item) => item.id !== project.id) ?? [])],
          next_cursor: current?.next_cursor ?? null,
        }),
      );
      setOperationError(null);
      setOperationMessage(`Created and selected ${project.name}.`);
      selectProjectContext(row, false);
      closeCreateForm();
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error) => {
      setOperationMessage(null);
      setOperationError(error instanceof Error ? error.message : "Project creation failed.");
    },
  });

  useEffect(() => {
    if (!selectedProjectId && projectRows[0]) {
      setSelectedProjectId(projectRows[0].id);
      setSelectedProjectContext(projectRows[0].id);
      return;
    }
    if (selectedProjectId && !projectRows.some((project) => project.id === selectedProjectId)) {
      if (projectRows[0]) {
        setSelectedProjectId(projectRows[0].id);
        setSelectedProjectContext(projectRows[0].id);
      } else {
        setSelectedProjectId("");
      }
    }
  }, [projectRows, selectedProjectId]);

  function closeCreateForm() {
    setIsCreateOpen(false);
    setProjectName("");
    setProjectDescription("");
  }

  function selectProjectContext(project: ProjectRow, announce = true) {
    setSelectedProjectId(project.id);
    setSelectedProjectContext(project.id);
    if (announce) {
      setOperationError(null);
      setOperationMessage(`Selected ${project.name} as the active project.`);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = projectName.trim();
    const description = projectDescription.trim();
    if (name.length < 3) {
      setOperationMessage(null);
      setOperationError("Project name must be at least 3 characters.");
      return;
    }

    if (!token) {
      const project = {
        id: createBrowserScopedId(),
        organization_id: "browser-session",
        name,
        slug: slugify(name),
        status: "active",
        description: description || "General ML product area",
        owner_user_id: "browser-user",
        source: "local" as const,
      };
      setSessionProjects((current) => [project, ...current]);
      setOperationError(null);
      setOperationMessage(`Created and selected ${project.name}.`);
      selectProjectContext(project, false);
      closeCreateForm();
      return;
    }

    createMutation.mutate({ name, description });
  }

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Projects"
        description="Independent ML product areas with isolated datasets, experiments, models, deployments, and operational policy."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Projects" value={String(projectRows.length)} detail="visible workspaces" />
        <MetricCard
          label="Active"
          value={String(activeProjects.length)}
          detail="operational"
          tone="success"
        />
        <MetricCard
          label="Context"
          value={selectedProject ? selectedProject.name : "none"}
          detail={contextSource}
        />
        <MetricCard
          label="API Mode"
          value={canLoadProjects ? "connected" : "local"}
          detail={canLoadProjects ? "token present" : "demo context"}
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

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <DataPanel
          title="Project Inventory"
          action={
            <button
              type="button"
              onClick={() => {
                setIsCreateOpen(true);
                setOperationError(null);
              }}
              className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              <Plus className="h-4 w-4" />
              New
            </button>
          }
        >
          {isCreateOpen ? (
            <CreateProjectForm
              name={projectName}
              description={projectDescription}
              isPending={createMutation.isPending}
              onSubmit={handleSubmit}
              onCancel={closeCreateForm}
              onNameChange={setProjectName}
              onDescriptionChange={setProjectDescription}
            />
          ) : null}
          {canLoadProjects && projectsQuery.error ? (
            <StateMessage message="Project inventory request failed." tone="danger" />
          ) : projectRows.length === 0 ? (
            <StateMessage
              message={projectsQuery.isFetching ? "Loading projects." : "No projects are available."}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="text-xs uppercase text-steel">
                  <tr>
                    <th className="py-2">Project</th>
                    <th>Status</th>
                    <th>Domain</th>
                    <th>Source</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {projectRows.map((project) => (
                    <ProjectTableRow
                      key={project.id}
                      project={project}
                      selected={project.id === selectedProject?.id}
                      onSelect={() => selectProjectContext(project)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataPanel>

        <DataPanel title="Project Context">
          {!selectedProject ? (
            <StateMessage message="No project context is selected." />
          ) : (
            <ProjectContextPanel project={selectedProject} />
          )}
        </DataPanel>
      </div>
    </>
  );
}

type CreateProjectFormProps = {
  name: string;
  description: string;
  isPending: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
};

function CreateProjectForm({
  name,
  description,
  isPending,
  onSubmit,
  onCancel,
  onNameChange,
  onDescriptionChange,
}: CreateProjectFormProps) {
  return (
    <form
      aria-label="Create project"
      onSubmit={onSubmit}
      className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(180px,0.7fr)_minmax(220px,1fr)_auto]">
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Name
          <input
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
          Description
          <input
            value={description}
            onChange={(event) => onDescriptionChange(event.target.value)}
            className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
          />
        </label>
        <div className="flex items-end gap-2">
          <button
            type="submit"
            disabled={isPending}
            className="inline-flex h-10 items-center gap-2 rounded bg-signal px-3 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <Check className="h-4 w-4" />
            Create project
          </button>
          <button
            type="button"
            aria-label="Cancel project creation"
            onClick={onCancel}
            className="inline-flex h-10 w-10 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </form>
  );
}

function ProjectTableRow({
  project,
  selected,
  onSelect,
}: {
  project: ProjectRow;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr className="border-t border-slate-100">
      <td className="py-3">
        <div className="font-medium">{project.name}</div>
        <div className="text-xs text-steel">{project.slug}</div>
      </td>
      <td>
        <span className={statusClassName(project.status)}>{project.status}</span>
      </td>
      <td>{project.description || "General ML product area"}</td>
      <td>{project.source}</td>
      <td aria-label="Project actions">
        <button
          type="button"
          aria-label={`Select project ${project.name}`}
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

function ProjectContextPanel({ project }: { project: ProjectRow }) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{project.name}</div>
          <div className="mt-1 text-xs text-steel">{project.description}</div>
        </div>
        <span className={statusClassName(project.status)}>{project.status}</span>
      </div>
      <div className="grid gap-3 rounded border border-slate-200 p-3 sm:grid-cols-2">
        <SignalTile
          icon={<FolderKanban className="h-4 w-4" />}
          label="Project"
          value={project.id}
          detail={project.slug}
        />
        <SignalTile
          icon={<Layers3 className="h-4 w-4" />}
          label="Organization"
          value={project.organization_id}
          detail="workspace scope"
        />
        <SignalTile
          icon={<ShieldCheck className="h-4 w-4" />}
          label="Owner"
          value={project.owner_user_id}
          detail="RBAC principal"
        />
        <SignalTile
          icon={<KeyRound className="h-4 w-4" />}
          label="Context Key"
          value={PROJECT_CONTEXT_KEY}
          detail="saved locally"
        />
      </div>
      <div className="rounded border border-slate-200 p-3 text-sm">
        <div className="font-medium">Downstream Scope</div>
        <div className="mt-2 text-xs leading-5 text-steel">
          Datasets, feature sets, experiments, training runs, models, deployments,
          inference endpoints, monitoring, drift, retraining, and alerts read this
          project id from local workspace context.
        </div>
      </div>
    </div>
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

function projectToRow(project: Project): ProjectRow {
  return {
    id: project.id,
    organization_id: project.organization_id,
    name: project.name,
    slug: project.slug,
    status: project.status,
    description: project.description || "General ML product area",
    owner_user_id: project.owner_user_id,
    source: "api",
  };
}

function statusClassName(status: string): string {
  if (status === "active") {
    return "rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-signal";
  }
  if (status === "archived") {
    return "rounded bg-slate-100 px-2 py-1 text-xs font-medium text-steel";
  }
  return "rounded bg-field px-2 py-1 text-xs font-medium";
}

function slugify(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "project";
}

function createBrowserScopedId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `browser-project-${Date.now()}`;
}

function readLocalStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(key);
}

function setSelectedProjectContext(projectId: string): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(PROJECT_CONTEXT_KEY, projectId);
  }
}
