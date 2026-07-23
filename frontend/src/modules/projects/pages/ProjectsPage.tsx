import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Plus, X } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { DataPanel } from "../../../shared/ui/DataPanel";
import { PageHeader } from "../../../shared/ui/PageHeader";
import { createProject, listProjects, type Project } from "../api/projects";

type ProjectRow = {
  id: string;
  name: string;
  status: string;
  domain: string;
  latestModel: string;
};

const exampleProjectRows: ProjectRow[] = [
  {
    id: "example-movie-recommendation",
    name: "Movie Recommendation",
    status: "active",
    domain: "Ranking and candidate generation",
    latestModel: "movie-ranker-v2"
  },
  {
    id: "example-semantic-search",
    name: "Semantic Search",
    status: "active",
    domain: "Embedding-based document retrieval",
    latestModel: "semantic-catalog-embed"
  },
  {
    id: "example-fraud-detection",
    name: "Fraud Detection",
    status: "active",
    domain: "Payment risk scoring",
    latestModel: "fraud-risk-xgb"
  }
];

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const token = readLocalStorage("forgeml_access_token");
  const canLoadProjects = Boolean(token);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [sessionProjects, setSessionProjects] = useState<ProjectRow[]>([]);
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => listProjects(token ?? ""),
    enabled: canLoadProjects
  });
  const createMutation = useMutation({
    mutationFn: (payload: { name: string; description: string }) =>
      createProject(payload, token ?? ""),
    onSuccess: (project) => {
      setSelectedProjectContext(project.id);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      closeCreateForm();
    },
    onError: () => {
      setFormError("Project creation failed.");
    }
  });
  const apiProjectRows = useMemo(
    () => (projectsQuery.data?.items ?? []).map(projectToRow),
    [projectsQuery.data?.items]
  );
  const projectRows = [
    ...(canLoadProjects ? apiProjectRows : exampleProjectRows),
    ...sessionProjects
  ];

  function closeCreateForm() {
    setIsCreateOpen(false);
    setProjectName("");
    setProjectDescription("");
    setFormError(null);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = projectName.trim();
    const description = projectDescription.trim();
    if (name.length < 3) {
      setFormError("Project name must be at least 3 characters.");
      return;
    }

    setFormError(null);
    if (!token) {
      setSessionProjects((current) => [
        {
          id: createBrowserScopedId(),
          name,
          status: "active",
          domain: description || "General ML product area",
          latestModel: "not registered"
        },
        ...current
      ]);
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
      <DataPanel
        title="Project Inventory"
        action={
          <button
            type="button"
            onClick={() => {
              setIsCreateOpen(true);
              setFormError(null);
            }}
            className="inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            <Plus className="h-4 w-4" />
            New
          </button>
        }
      >
        {isCreateOpen ? (
          <form
            aria-label="Create project"
            onSubmit={handleSubmit}
            className="-mx-4 -mt-4 mb-4 border-b border-slate-200 bg-field px-4 py-4"
          >
            <div className="grid gap-3 lg:grid-cols-[minmax(180px,0.7fr)_minmax(220px,1fr)_auto]">
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Name
                <input
                  value={projectName}
                  onChange={(event) => setProjectName(event.target.value)}
                  className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
                Description
                <input
                  value={projectDescription}
                  onChange={(event) => setProjectDescription(event.target.value)}
                  className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
                />
              </label>
              <div className="flex items-end gap-2">
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="inline-flex h-10 items-center gap-2 rounded bg-signal px-3 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Check className="h-4 w-4" />
                  Create project
                </button>
                <button
                  type="button"
                  aria-label="Cancel project creation"
                  onClick={closeCreateForm}
                  className="inline-flex h-10 w-10 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            {formError ? <div className="mt-2 text-sm text-risk">{formError}</div> : null}
          </form>
        ) : null}
        {canLoadProjects && projectsQuery.error ? (
          <div className="mb-4 border-b border-rose-200 bg-rose-50 px-4 py-3 text-sm text-risk">
            Project inventory request failed.
          </div>
        ) : null}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs uppercase text-steel">
              <tr>
                <th className="py-2">Project</th>
                <th>Status</th>
                <th>Domain</th>
                <th>Latest Model</th>
              </tr>
            </thead>
            <tbody>
              {projectRows.map((project) => (
                <tr key={project.id} className="border-t border-slate-100">
                  <td className="py-3 font-medium">{project.name}</td>
                  <td>{project.status}</td>
                  <td>{project.domain}</td>
                  <td>{project.latestModel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DataPanel>
    </>
  );
}

function projectToRow(project: Project): ProjectRow {
  return {
    id: project.id,
    name: project.name,
    status: project.status,
    domain: project.description || "General ML product area",
    latestModel: "not registered"
  };
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
    window.localStorage.setItem("forgeml_project_id", projectId);
  }
}
