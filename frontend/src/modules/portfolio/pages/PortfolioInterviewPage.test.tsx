import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MemoryRouter } from "../../../shared/routing/router";
import { PortfolioInterviewPage } from "./PortfolioInterviewPage";

describe("PortfolioInterviewPage", () => {
  it("renders the reviewer dashboard and architecture walkthrough", () => {
    renderPortfolioInterviewPage();

    expect(
      screen.getByRole("heading", { name: "Portfolio Interview Mode" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Reviewer Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Architecture Walkthrough")).toBeInTheDocument();
    expect(screen.getByText("Evidence Explanations")).toBeInTheDocument();
    expect(screen.getAllByText("Validation Paths").length).toBeGreaterThan(0);
    expect(screen.getByText("Interview Talk Track")).toBeInTheDocument();
    expect(
      screen.getByText("Multi-project ML platform control plane"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Modular monolith with extractable boundaries"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Release-governance loop with audit evidence"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/conversational-movie-recommender/),
    ).toBeInTheDocument();
  });

  it("surfaces validation commands and contract evidence", () => {
    renderPortfolioInterviewPage();

    expect(screen.getByText("make demo-stack-fresh")).toBeInTheDocument();
    expect(screen.getAllByText("make demo-walkthrough").length).toBeGreaterThan(0);
    expect(screen.getByText("make production-readiness")).toBeInTheDocument();
    expect(
      screen.getByText(
        "PYTHONPATH=. python scripts/ci/check_portfolio_interview_mode_contract.py",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("portfolio_interview_mode_contract")).toBeInTheDocument();
    expect(
      screen.getAllByText("contracts/ops/portfolio-interview-mode.v1.json")[0],
    ).toBeInTheDocument();
    expect(screen.getByText("11-portfolio-interview-mode.png")).toBeInTheDocument();
  });

  it("links interview claims and validation paths to product routes", () => {
    renderPortfolioInterviewPage();

    expect(
      screen.getByRole("link", {
        name: "Open Release-governance loop with audit evidence",
      }),
    ).toHaveAttribute("href", "/release-evidence");
    expect(
      screen.getByRole("link", {
        name: "Open Observability, drift, alerts, and retraining loop",
      }),
    ).toHaveAttribute("href", "/monitoring");

    const validationPanel = screen
      .getByRole("heading", { name: "Validation Paths" })
      .closest("section");
    expect(validationPanel).not.toBeNull();
    expect(
      within(validationPanel as HTMLElement).getAllByRole("link", {
        name: "/portfolio",
      }).length,
    ).toBeGreaterThan(0);
  });
});

function renderPortfolioInterviewPage() {
  render(
    <MemoryRouter>
      <PortfolioInterviewPage />
    </MemoryRouter>,
  );
}
