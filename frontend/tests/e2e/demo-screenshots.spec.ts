import { expect, type Page, test } from "@playwright/test";

import { installForgeMLApiMock } from "./fixtures/forgemlApiMock";

const demoScreens = [
  { path: "/", heading: "Dashboard", fileName: "01-dashboard.png" },
  { path: "/projects", heading: "Projects", fileName: "02-projects.png" },
  { path: "/examples", heading: "Example Projects", fileName: "03-examples.png" },
  { path: "/training-runs", heading: "Training Runs", fileName: "04-training-runs.png" },
  { path: "/models", heading: "Models", fileName: "05-models.png" },
  { path: "/deployments", heading: "Deployments", fileName: "06-deployments.png" },
  { path: "/inference", heading: "Inference", fileName: "07-inference.png" },
  { path: "/monitoring", heading: "Monitoring", fileName: "08-monitoring.png" }
] as const;

test("captures reviewer-ready demo screenshots", async ({ page }, testInfo) => {
  await installForgeMLApiMock(page);
  await page.goto("/login");

  await page.getByLabel("Password").fill("forgeml-local-admin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
  await page.getByRole("button", { name: "Select project Fraud Detection" }).click();
  await expect(
    page.getByText("Selected Fraud Detection as the active project.")
  ).toBeVisible();
  await prepareDemoState(page);

  for (const screen of demoScreens) {
    await page.goto(screen.path);
    await expect(page).toHaveURL(new RegExp(`${escapeRegExp(screen.path)}$`));
    await expect(
      page.getByRole("heading", { name: screen.heading, exact: true })
    ).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath(screen.fileName),
      fullPage: true
    });
  }
});

async function prepareDemoState(page: Page): Promise<void> {
  await page.getByRole("link", { name: "Training Runs" }).click();
  await page.getByRole("button", { name: "Run" }).click();
  const startRunForm = page.getByRole("form", { name: "Start training run" });
  await startRunForm.getByLabel("Run Name").fill("fraud-risk-demo-xgb");
  await startRunForm.getByLabel("Algorithm").fill("xgboost");
  await startRunForm.getByLabel("Model Type").fill("xgboost");
  await startRunForm.getByLabel("Objective Metric").fill("auc");
  await startRunForm.getByLabel("Hyperparameters").fill(
    JSON.stringify({ max_depth: 6, learning_rate: 0.05 })
  );
  await startRunForm.getByRole("button", { name: "Start run" }).click();
  await expect(page.getByText("Started training run training.")).toBeVisible();
  await page.getByRole("button", { name: "Record result" }).click();
  await expect(
    page.getByText("Training run finished with status succeeded.")
  ).toBeVisible();

  await page.getByRole("link", { name: "Models" }).click();
  await page.getByRole("button", { name: "Promote" }).click();
  await expect(page.getByText("Promoted v1 from training")).toBeVisible();
  await page.getByRole("button", { name: "Request approval" }).click();
  await page.getByRole("button", { name: "Approve v1" }).click();
  await expect(page.getByText("Version approved.")).toBeVisible();

  await page.getByRole("link", { name: "Deployments" }).click();
  await page.getByRole("button", { name: "Create revision" }).click();
  await expect(page.getByText("Created revision 1.")).toBeVisible();
  await page.getByRole("button", { name: "Mark revision 1 healthy" }).click();
  await expect(page.getByText("Revision 1 health recorded.")).toBeVisible();
  await page.getByRole("button", { name: "Promote revision 1 to full traffic" }).click();
  await expect(page.getByText("Revision 1 traffic is 100%.")).toBeVisible();

  await page.getByRole("link", { name: "Inference" }).click();
  const endpointForm = page.getByRole("form", { name: "Create inference endpoint" });
  await endpointForm.getByLabel("Name").fill("Fraud Risk Demo Endpoint");
  await endpointForm.getByLabel("Route").fill("/inference/fraud-risk-demo");
  await endpointForm.getByLabel("Description").fill("Fraud risk demo scoring.");
  await endpointForm.getByRole("button", { name: "Create endpoint" }).click();
  await expect(page.getByText("Created endpoint Fraud Risk Demo Endpoint.")).toBeVisible();
  await page.getByRole("button", { name: "Probe endpoint" }).click();
  await expect(page.getByText(/Probe control-plane-probe-.+ succeeded/)).toBeVisible();
  await page.getByRole("button", { name: "Record snapshot" }).click();
  await expect(page.getByText("Recorded 300s snapshot for 1200 predictions.")).toBeVisible();

  await page.getByRole("link", { name: "Monitoring" }).click();
  await expect(page.getByText("Fraud Risk Demo Endpoint").first()).toBeVisible();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
