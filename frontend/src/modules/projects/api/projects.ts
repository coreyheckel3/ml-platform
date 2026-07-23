import { apiGet, apiPost } from "../../../shared/api/client";

export type Project = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string;
  status: string;
  owner_user_id: string;
};

export type ProjectListResponse = {
  items: Project[];
  next_cursor: string | null;
};

export type CreateProjectPayload = {
  name: string;
  description: string;
};

export function listProjects(token: string): Promise<ProjectListResponse> {
  return apiGet<ProjectListResponse>("/api/v1/projects", { token });
}

export function createProject(
  payload: CreateProjectPayload,
  token: string
): Promise<Project> {
  return apiPost<CreateProjectPayload, Project>("/api/v1/projects", payload, { token });
}
