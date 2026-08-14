import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReleaseEvidencePage } from "./ReleaseEvidencePage";

describe("ReleaseEvidencePage", () => {
  it("renders release artifact evidence and reviewer commands", () => {
    render(<ReleaseEvidencePage />);

    expect(
      screen.getByRole("heading", { name: "Release Evidence" }),
    ).toBeInTheDocument();
    expect(screen.getByText("36")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getAllByText("forgeml-release-manifest").length).toBeGreaterThan(1);
    expect(screen.getByText("Release Manifest")).toBeInTheDocument();
    expect(screen.getByText("Live Evidence Retrieval")).toBeInTheDocument();
    expect(screen.getByText("GitHubActionsReleaseEvidenceGateway")).toBeInTheDocument();
    expect(screen.getByText("Comparison Signals")).toBeInTheDocument();
    expect(screen.getByText("required_artifact_coverage")).toBeInTheDocument();
    expect(screen.getByText("OpenAPI Contract")).toBeInTheDocument();
    expect(
      screen.getAllByText("Release Evidence Retrieval Contract").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("Security Hardening Contract").length).toBeGreaterThan(0);
    expect(screen.getByText("make production-readiness")).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "PYTHONPATH=backend/src:. python scripts/ops/retrieve_release_evidence.py --repo coreyheckel3/ml-platform --branch main --workflow ci.yml --artifact-name forgeml-release-manifest",
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("make demo-screenshots")).toBeInTheDocument();
  });

  it("surfaces quality gates and screenshot evidence", () => {
    render(<ReleaseEvidencePage />);

    expect(screen.getByText("Quality Gate Coverage")).toBeInTheDocument();
    expect(screen.getByText("backend_tests")).toBeInTheDocument();
    expect(screen.getByText("frontend_e2e")).toBeInTheDocument();
    expect(screen.getByText("release_manifest_verifier_contract")).toBeInTheDocument();
    expect(screen.getByText("operational_audit_ux_contract")).toBeInTheDocument();
    expect(screen.getByText("release_evidence_retrieval_contract")).toBeInTheDocument();
    expect(screen.getByText("Demo Screenshot Evidence")).toBeInTheDocument();
    expect(screen.getByText("09-release-evidence.png")).toBeInTheDocument();
    expect(screen.getByText("10-operational-audit.png")).toBeInTheDocument();
    expect(screen.getByText("/release-evidence")).toBeInTheDocument();
  });
});
