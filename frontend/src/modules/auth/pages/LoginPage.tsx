import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, KeyRound, LogIn, ShieldCheck } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { login } from "../api/auth";
import {
  readStoredSession,
  subscribeToSessionChanges,
  writeStoredSession,
  type StoredSession,
} from "../session/sessionStore";
import { DataPanel } from "../../../shared/ui/DataPanel";
import { MetricCard } from "../../../shared/ui/MetricCard";
import { PageHeader } from "../../../shared/ui/PageHeader";

const seededDemoEmail = "admin@forgeml.dev";

export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const redirectPath = sanitizeRedirect(searchParams.get("redirect"));
  const [email, setEmail] = useState(seededDemoEmail);
  const [password, setPassword] = useState("");
  const [operationError, setOperationError] = useState<string | null>(null);
  const [session, setSession] = useState<StoredSession | null>(() => readStoredSession());
  const sessionStatus = useMemo(() => getSessionStatus(session), [session]);
  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: async (tokens) => {
      writeStoredSession(tokens);
      setOperationError(null);
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      navigate(redirectPath, { replace: true });
    },
    onError: (error) => {
      setOperationError(error instanceof Error ? error.message : "Sign in failed.");
    },
  });

  useEffect(
    () => subscribeToSessionChanges(() => setSession(readStoredSession())),
    [],
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail || !password) {
      setOperationError("Email and password are required.");
      return;
    }

    loginMutation.mutate({ email: trimmedEmail, password });
  }

  return (
    <>
      <PageHeader
        eyebrow="Authentication"
        title="Sign In"
        description="Exchange operator credentials for ForgeML API tokens and unlock backend-backed platform workflows."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="Session"
          value={sessionStatus.label}
          detail={sessionStatus.detail}
          tone={sessionStatus.tone}
        />
        <MetricCard
          label="Token Type"
          value={session?.tokenType ?? "none"}
          detail="bearer access control"
        />
        <MetricCard
          label="Redirect"
          value={redirectPath}
          detail="post-login destination"
        />
      </div>

      {operationError ? (
        <div className="mt-4 rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-risk">
          {operationError}
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <DataPanel title="Credential Exchange">
          <form aria-label="Sign in" onSubmit={handleSubmit} className="grid gap-4">
            <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
              Email
              <input
                type="email"
                value={email}
                autoComplete="username"
                onChange={(event) => setEmail(event.target.value)}
                className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
              />
            </label>
            <label className="grid gap-1 text-xs font-semibold uppercase text-steel">
              Password
              <input
                type="password"
                value={password}
                autoComplete="current-password"
                onChange={(event) => setPassword(event.target.value)}
                className="h-10 rounded border border-slate-200 bg-white px-3 text-sm font-normal normal-case text-ink outline-none focus:border-signal"
              />
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={loginMutation.isPending}
                className="inline-flex h-10 items-center gap-2 rounded bg-ink px-4 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-70"
              >
                <LogIn className="h-4 w-4" />
                Sign in
              </button>
              {session ? (
                <Link
                  to="/projects"
                  className="inline-flex h-10 items-center rounded border border-slate-200 bg-white px-4 text-sm font-semibold text-steel transition hover:text-ink"
                >
                  Continue to projects
                </Link>
              ) : null}
            </div>
          </form>
        </DataPanel>

        <DataPanel title="Session Policy">
          <div className="grid gap-3 md:grid-cols-2">
            <SignalTile
              icon={<ShieldCheck className="h-4 w-4" />}
              label="Principal"
              value={seededDemoEmail}
              detail="local seeded admin"
            />
            <SignalTile
              icon={<Clock3 className="h-4 w-4" />}
              label="Access Expiry"
              value={session ? formatDateTime(session.expiresAt) : "none"}
              detail="controlled by backend token TTL"
            />
            <SignalTile
              icon={<KeyRound className="h-4 w-4" />}
              label="Refresh Token"
              value={session?.refreshToken ? "stored" : "none"}
              detail="reserved for backend rotation"
            />
            <SignalTile
              icon={<CheckCircle2 className="h-4 w-4" />}
              label="Storage"
              value="browser-local"
              detail="cleared by sign out"
            />
          </div>
        </DataPanel>
      </div>
    </>
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
    <div className="min-w-0 rounded border border-slate-200 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-steel">
        {icon}
        {label}
      </div>
      <div className="mt-2 truncate text-sm font-medium text-ink">{value}</div>
      <div className="mt-1 truncate text-xs text-steel">{detail}</div>
    </div>
  );
}

function sanitizeRedirect(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/projects";
  }
  return value;
}

function getSessionStatus(session: StoredSession | null): {
  label: string;
  detail: string;
  tone: "neutral" | "success" | "warning" | "danger";
} {
  if (!session) {
    return {
      label: "signed out",
      detail: "no token in storage",
      tone: "warning",
    };
  }

  const expiresAtMs = Date.parse(session.expiresAt);
  if (Number.isNaN(expiresAtMs)) {
    return {
      label: "unknown",
      detail: "expiry metadata unavailable",
      tone: "danger",
    };
  }

  if (expiresAtMs <= Date.now()) {
    return {
      label: "expired",
      detail: formatDateTime(session.expiresAt),
      tone: "danger",
    };
  }

  return {
    label: "active",
    detail: formatDateTime(session.expiresAt),
    tone: "success",
  };
}

function formatDateTime(value: string): string {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return "invalid expiry";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}
