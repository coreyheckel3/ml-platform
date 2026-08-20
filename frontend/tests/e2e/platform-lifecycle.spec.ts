import { expect, test } from "@playwright/test";

import { installForgeMLApiMock } from "./fixtures/forgemlApiMock";

test("drives the ML lifecycle through the browser with stateful API contracts", async ({
  page,
}) => {
  await installForgeMLApiMock(page);
  await page.goto("/login");

  await page.getByLabel("Password").fill("forgeml-local-admin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
  await expect(page.getByText("admin@forgeml.dev")).toBeVisible();

  await page.getByRole("button", { name: "New" }).click();
  const projectForm = page.getByRole("form", { name: "Create project" });
  await projectForm.getByLabel("Name").fill("Chargeback Risk Platform");
  await projectForm
    .getByLabel("Description")
    .fill("Payment fraud lifecycle validation.");
  await projectForm.getByRole("button", { name: "Create project" }).click();
  await expect(
    page.getByText("Created and selected Chargeback Risk Platform."),
  ).toBeVisible();

  await page.getByRole("link", { name: "Datasets" }).click();
  await expect(page.getByRole("heading", { name: "Datasets" })).toBeVisible();
  await page.getByRole("button", { name: "Dataset" }).click();
  const datasetForm = page.getByRole("form", { name: "Create dataset" });
  await datasetForm
    .getByLabel("Dataset Name")
    .fill("Chargeback Feature Snapshot");
  await datasetForm
    .getByLabel("Description")
    .fill("Daily labeled payment features.");
  await datasetForm.getByRole("button", { name: "Create dataset" }).click();
  await expect(
    page.getByText("Created dataset Chargeback Feature Snapshot."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Version" }).click();
  const versionForm = page.getByRole("form", {
    name: "Create dataset version",
  });
  await versionForm.getByLabel("Filename").fill("chargeback_features.csv");
  await versionForm.getByRole("button", { name: "Create version" }).click();
  await expect(page.getByText("Created upload plan for v1.")).toBeVisible();

  const finalizeForm = page.getByRole("form", {
    name: "Finalize dataset version",
  });
  await finalizeForm.getByLabel("Content Hash").fill("sha256:e2e-chargeback");
  await finalizeForm.getByLabel("Size Bytes").fill("2048");
  await finalizeForm
    .getByRole("textbox", { name: "CSV Sample" })
    .fill("account_id,amount,is_fraud\nacct-1,42.5,false\nacct-2,500,true");
  await finalizeForm.getByRole("button", { name: "Finalize version" }).click();
  await expect(page.getByText("Finalized dataset v1.")).toBeVisible();
  await expect(page.getByText("account_id")).toBeVisible();

  await page.getByRole("button", { name: "Validate" }).click();
  await expect(page.getByText("Validation completed for validati.")).toBeVisible();

  await page.getByRole("link", { name: "Training Runs" }).click();
  await expect(
    page.getByRole("heading", { name: "Training Runs" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run", exact: true }).click();
  const startRunForm = page.getByRole("form", { name: "Start training run" });
  await startRunForm.getByLabel("Run Name").fill("chargeback-xgb-depth-8");
  await startRunForm.getByLabel("Algorithm").fill("xgboost");
  await startRunForm.getByLabel("Model Type").fill("xgboost");
  await startRunForm.getByLabel("Objective Metric").fill("auc");
  await startRunForm
    .getByLabel("Hyperparameters")
    .fill(JSON.stringify({ max_depth: 8, learning_rate: 0.05 }));
  await expect(
    startRunForm.getByRole("button", { name: "Start run" }),
  ).toBeEnabled();
  await startRunForm.getByRole("button", { name: "Start run" }).click();
  await expect(page.getByText("Started training run training.")).toBeVisible();
  await expect(page.getByText("Started from the training UI.")).toBeVisible();
  await page
    .getByRole("heading", { name: "Execution Logs" })
    .scrollIntoViewIfNeeded();
  await expect(
    page
      .getByLabel("Execution logs")
      .getByText("Training run was queued for execution."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Record result" }).click();
  await expect(
    page.getByText("Recorded succeeded result for training."),
  ).toBeVisible();
  await expect(
    page.getByText("Training run finished with status succeeded."),
  ).toBeVisible();
  await expect(page.getByText("Training artifact metadata uploaded.")).toBeVisible();

  await page.getByRole("link", { name: "Models" }).click();
  await expect(page.getByRole("heading", { name: "Models" })).toBeVisible();
  await expect(
    page.getByRole("form", { name: "Promote training run" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Promote" })).toBeEnabled();
  await page.getByRole("button", { name: "Promote" }).click();
  await expect(page.getByText("Promoted v1 from training")).toBeVisible();
  await page.getByRole("button", { name: "Request approval" }).click();
  await expect(page.getByText("Approval requested.")).toBeVisible();
  await page.getByRole("button", { name: "Approve v1" }).click();
  await expect(page.getByText("Version approved.")).toBeVisible();

  await page.getByRole("link", { name: "Deployments" }).click();
  await expect(page.getByRole("heading", { name: "Deployments" })).toBeVisible();
  await expect(
    page.getByRole("form", { name: "Create deployment revision" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Create revision" }).click();
  await expect(page.getByText("Created revision 1.")).toBeVisible();
  await page.getByRole("button", { name: "Mark revision 1 healthy" }).click();
  await expect(page.getByText("Revision 1 health recorded.")).toBeVisible();
  await page
    .getByRole("button", { name: "Promote revision 1 to full traffic" })
    .click();
  await expect(page.getByText("Revision 1 traffic is 100%.")).toBeVisible();

  await page.getByRole("link", { name: "Inference" }).click();
  await expect(page.getByRole("heading", { name: "Inference" })).toBeVisible();
  const endpointForm = page.getByRole("form", {
    name: "Create inference endpoint",
  });
  await endpointForm.getByLabel("Name").fill("Chargeback Scoring Endpoint");
  await endpointForm.getByLabel("Route").fill("/inference/chargeback-scoring");
  await endpointForm
    .getByLabel("Description")
    .fill("Online chargeback risk scoring.");
  await endpointForm.getByRole("button", { name: "Create endpoint" }).click();
  await expect(
    page.getByText("Created endpoint Chargeback Scoring Endpoint."),
  ).toBeVisible();

  await page.getByRole("button", { name: "Probe endpoint" }).click();
  await expect(
    page.getByText(/^Probe control-plane-probe-.+ succeeded in 17.5ms\.$/),
  ).toBeVisible();
  await expect(page.getByText('"risk_band": "high"')).toBeVisible();
  await page.getByRole("button", { name: "Record snapshot" }).click();
  await expect(
    page.getByText("Recorded 300s snapshot for 1200 predictions."),
  ).toBeVisible();

  await page.getByRole("link", { name: "Monitoring" }).click();
  await expect(page.getByRole("heading", { name: "Monitoring" })).toBeVisible();
  await expect(page.getByText("Chargeback Scoring Endpoint").first()).toBeVisible();
  await expect(page.getByText("1200").first()).toBeVisible();
  await page.getByRole("button", { name: "Evaluate rule" }).click();
  await expect(
    page.getByText(
      "Triggered Chargeback Risk Platform p95 latency breach at 138.0ms.",
    ),
  ).toBeVisible();
});
