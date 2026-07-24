import { apiGet, apiPost } from "../../../shared/api/client";

export type LoginPayload = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type RefreshTokenPayload = {
  refresh_token: string;
};

export type LogoutPayload = {
  refresh_token: string;
};

export type LogoutResponse = {
  revoked: boolean;
};

export type CurrentUser = {
  id: string;
  email: string;
  organization_id: string;
  permissions: string[];
};

export function login(payload: LoginPayload): Promise<TokenResponse> {
  return apiPost<LoginPayload, TokenResponse>("/api/v1/auth/login", payload);
}

export function refreshSession(payload: RefreshTokenPayload): Promise<TokenResponse> {
  return apiPost<RefreshTokenPayload, TokenResponse>("/api/v1/auth/refresh", payload);
}

export function logoutSession(payload: LogoutPayload): Promise<LogoutResponse> {
  return apiPost<LogoutPayload, LogoutResponse>("/api/v1/auth/logout", payload);
}

export function getCurrentUser(token: string): Promise<CurrentUser> {
  return apiGet<CurrentUser>("/api/v1/auth/me", { token });
}
