import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense } from "react";

import { appRoutes } from "./routes";
import { BrowserRouter, Route, Routes } from "../shared/routing/router";
import { Shell } from "../shared/ui/Shell";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Shell>
          <Suspense fallback={<RouteLoadingState />}>
            <Routes>
              {appRoutes.map((route) => (
                <Route
                  key={route.path}
                  path={route.path}
                  element={route.element}
                />
              ))}
            </Routes>
          </Suspense>
        </Shell>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function RouteLoadingState() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-[320px] items-center justify-center rounded border border-slate-200 bg-white text-sm font-medium text-steel"
    >
      Loading workspace
    </div>
  );
}
