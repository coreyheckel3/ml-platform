import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReleaseEvidencePage } from "./ReleaseEvidencePage";

describe("ReleaseEvidencePage", () => {
  it("renders release artifact evidence and reviewer commands", () => {
    render(<ReleaseEvidencePage />);

    expect(
      screen.getByRole("heading", { name: "Release Evidence" }),
    ).toBeInTheDocument();
    expect(screen.getByText("35")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("forgeml-release-manifest")).toBeInTheDocument();
    expect(screen.getByText("Release Manifest")).toBeInTheDocument();
    expect(screen.getByText("OpenAPI Contract")).toBeInTheDocument();
    expect(screen.getAllByText("Security Hardening Contract").length).toBeGreaterThan(0);
    expect(screen.getByText("make production-readiness")).toBeInTheDocument();
    expect(screen.getByText("make demo-screenshots")).toBeInTheDocument();
  });

  it("surfaces quality gates and screenshot evidence", () => {
    render(<ReleaseEvidencePage />);

    expect(screen.getByText("Quality Gate Coverage")).toBeInTheDocument();
    expect(screen.getByText("backend_tests")).toBeInTheDocument();
    expect(screen.getByText("frontend_e2e")).toBeInTheDocument();
    expect(screen.getByText("release_manifest_verifier_contract")).toBeInTheDocument();
    expect(screen.getByText("operational_audit_ux_contract")).toBeInTheDocument();
    expect(screen.getByText("Demo Screenshot Evidence")).toBeInTheDocument();
    expect(screen.getByText("09-release-evidence.png")).toBeInTheDocument();
    expect(screen.getByText("10-operational-audit.png")).toBeInTheDocument();
    expect(screen.getByText("/release-evidence")).toBeInTheDocument();
  });
});
