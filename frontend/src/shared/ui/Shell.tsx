import { Menu, Search } from "lucide-react";
import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

import { navigationItems } from "../../app/navigation";

export function Shell({ children }: PropsWithChildren) {
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
              <div className="text-sm font-medium">Platform Admin</div>
              <div className="text-xs text-steel">local</div>
            </div>
            <div className="h-9 w-9 rounded bg-signal text-center text-sm font-semibold leading-9 text-white">
              PA
            </div>
          </div>
        </header>
        <main className="px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
