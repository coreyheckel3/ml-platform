import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProjectsPage } from "./ProjectsPage";

describe("ProjectsPage", () => {
  it("creates a browser-scoped project from the New action", () => {
    window.localStorage.clear();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <QueryClientProvider client={queryClient}>
        <ProjectsPage />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "New" }));
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Audience Forecasting" }
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Demand planning models" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Create project" }));

    expect(screen.getByText("Audience Forecasting")).toBeInTheDocument();
    expect(screen.getByText("Demand planning models")).toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "Create project" })).not.toBeInTheDocument();
  });
});
