import { LogIn, LogOut, Menu, Search } from "lucide-react";
import { type PropsWithChildren, useEffect, useMemo, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { navigationItems } from "../../app/navigation";
import { getCurrentUser } from "../../modules/auth/api/auth";
import {
  clearStoredSession,
  readStoredSession,
  subscribeToSessionChanges,
  type StoredSession,
} from "../../modules/auth/session/sessionStore";

export function Shell({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [session, setSession] = useState<StoredSession | null>(() => readStoredSession());
  const token = session?.accessToken ?? "";
  const currentUserQuery = useQuery({
    queryKey: ["current-user", token],
    queryFn: () => getCurrentUser(token),
    enabled: Boolean(token),
    retry: false,
  });
  const accountSummary = useMemo(
    () => getAccountSummary(session, currentUserQuery.data?.email),
    [currentUserQuery.data?.email, session],
  );

  useEffect(
    () => subscribeToSessionChanges(() => setSession(readStoredSession())),
    [],
  );

  function handleSignOut() {
    clearStoredSession({ clearProjectContext: true });
    setSession(null);
    queryClient.removeQueries({ queryKey: ["current-user"] });
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-cloud text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-16 items-center border-b border-slate-200 px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded bg-ink text-sm font-bold text-white">
            FM
          </div>
          <div className="ml-3">
            <div className="text-sm font-semibold">ForgeML</div>
            <div className="text-xs text-steel">ML Platform</div>
          </div>
        </div>
        <nav className="space-y-1 px-3 py-4">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  [
                    "flex h-10 items-center gap-3 rounded px-3 text-sm font-medium transition",
                    isActive
                      ? "bg-ink text-white"
                      : "text-steel hover:bg-field hover:text-ink"
                  ].join(" ")
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 text-steel lg:hidden"
              aria-label="Open navigation"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div className="hidden h-9 w-80 items-center gap-2 rounded border border-slate-200 bg-cloud px-3 text-sm text-steel md:flex">
              <Search className="h-4 w-4" aria-hidden="true" />
              <span>Search projects, datasets, models</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="max-w-[180px] truncate text-sm font-medium">
                {accountSummary.name}
              </div>
              <div className="text-xs text-steel">{accountSummary.detail}</div>
            </div>
            {session ? (
              <button
                type="button"
                aria-label="Sign out"
                onClick={handleSignOut}
                className="inline-flex h-9 w-9 items-center justify-center rounded border border-slate-200 bg-white text-steel transition hover:text-ink"
              >
                <LogOut className="h-4 w-4" />
              </button>
            ) : (
              <Link
                to="/login"
                className="inline-flex h-9 items-center gap-2 rounded bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-700"
              >
                <LogIn className="h-4 w-4" />
                Sign in
              </Link>
            )}
          </div>
        </header>
        <main className="px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}

function getAccountSummary(
  session: StoredSession | null,
  email?: string,
): { name: string; detail: string } {
  if (!session) {
    return {
      name: "Local Demo",
      detail: "signed out",
    };
  }

  const expiresAtMs = Date.parse(session.expiresAt);
  const expiryDetail =
    Number.isNaN(expiresAtMs) || expiresAtMs <= Date.now()
      ? "session expired"
      : `expires ${formatTime(session.expiresAt)}`;

  return {
    name: email ?? "Platform Admin",
    detail: expiryDetail,
  };
}

function formatTime(value: string): string {
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return "soon";
  }
  return new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp));
}
