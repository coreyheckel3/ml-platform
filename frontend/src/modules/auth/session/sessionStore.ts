import type { TokenResponse } from "../api/auth";

export const ACCESS_TOKEN_KEY = "forgeml_access_token";
export const REFRESH_TOKEN_KEY = "forgeml_refresh_token";
export const TOKEN_TYPE_KEY = "forgeml_token_type";
export const TOKEN_EXPIRES_AT_KEY = "forgeml_token_expires_at";
export const PROJECT_CONTEXT_KEY = "forgeml_project_id";

const sessionChangeEvent = "forgeml_session_change";
const sessionKeys = new Set([
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  TOKEN_TYPE_KEY,
  TOKEN_EXPIRES_AT_KEY,
  PROJECT_CONTEXT_KEY,
]);

export type StoredSession = {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresAt: string;
};

export function readStoredSession(): StoredSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  const tokenType = window.localStorage.getItem(TOKEN_TYPE_KEY);
  const expiresAt = window.localStorage.getItem(TOKEN_EXPIRES_AT_KEY);

  if (!accessToken || !refreshToken || !tokenType || !expiresAt) {
    return null;
  }

  return {
    accessToken,
    refreshToken,
    tokenType,
    expiresAt,
  };
}

export function writeStoredSession(tokens: TokenResponse, nowMs = Date.now()): StoredSession {
  const expiresAt = new Date(nowMs + tokens.expires_in * 1000).toISOString();
  const session = {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    tokenType: tokens.token_type,
    expiresAt,
  };

  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, session.accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, session.refreshToken);
    window.localStorage.setItem(TOKEN_TYPE_KEY, session.tokenType);
    window.localStorage.setItem(TOKEN_EXPIRES_AT_KEY, session.expiresAt);
    notifySessionChanged();
  }

  return session;
}

export function clearStoredSession(options: { clearProjectContext?: boolean } = {}): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(TOKEN_TYPE_KEY);
  window.localStorage.removeItem(TOKEN_EXPIRES_AT_KEY);
  if (options.clearProjectContext) {
    window.localStorage.removeItem(PROJECT_CONTEXT_KEY);
  }
  notifySessionChanged();
}

export function subscribeToSessionChanges(handler: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  function handleStorage(event: StorageEvent) {
    if (event.key === null || sessionKeys.has(event.key)) {
      handler();
    }
  }

  function handleLocalChange() {
    handler();
  }

  window.addEventListener("storage", handleStorage);
  window.addEventListener(sessionChangeEvent, handleLocalChange);

  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(sessionChangeEvent, handleLocalChange);
  };
}

function notifySessionChanged(): void {
  window.dispatchEvent(new Event(sessionChangeEvent));
}
