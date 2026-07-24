import { apiGet } from "../../../shared/api/client";

export type CurrentUser = {
  id: string;
  email: string;
  organization_id: string;
  permissions: string[];
};

export function getCurrentUser(token: string): Promise<CurrentUser> {
  return apiGet<CurrentUser>("/api/v1/auth/me", { token });
}
