import { expect, type Page, test } from "@playwright/test";

import { installForgeMLApiMock } from "./fixtures/forgemlApiMock";

const demoWalkthroughSteps = [
  {
    path: "/",
    heading: "Dashboard",
    signals: ["API Health", "Recent Training Runs"],
  },
  {
    path: "/portfolio",
    heading: "Portfolio Interview Mode",
    signals: ["Reviewer Dashboard", "Architecture Walkthrough", "Validation Paths"],
  },
  {
    path: "/projects",
    heading: "Projects",
    signals: ["Fraud Detection"],
  },
  {
    path: "/examples",
    heading: "Example Projects",
    signals: ["Movie Recommendation"],
  },
  {
    path: "/datasets",
    heading: "Datasets",
    signals: ["Dataset Registry"],
  },
  {
    path: "/feature-store",
    heading: "Feature Store",
    signals: ["Feature Set Inventory"],
  },
  {
    path: "/experiments",
    heading: "Experiments",
    signals: ["Experiment Registry"],
  },
  {
    path: "/training-runs",
    heading: "Training Runs",
    signals: ["Run Detail", "Execution Logs"],
  },
  {
    path: "/models",
    heading: "Models",
    signals: ["Model Registry"],
  },
  {
    path: "/deployments",
    heading: "Deployments",
    signals: ["Release Console"],
  },
  {
    path: "/inference",
    heading: "Inference",
    signals: ["Probe Console"],
  },
  {
    path: "/monitoring",
    heading: "Monitoring",
    signals: ["Operational Focus"],
  },
  {
    path: "/alerts",
    heading: "Alerts",
    signals: ["Alert Events"],
  },
  {
    path: "/drift",
    heading: "Drift Detection",
    signals: ["Run Drift Report"],
  },
  {
    path: "/retraining",
    heading: "Retraining",
    signals: ["Retraining Policies"],
  },
  {
    path: "/release-evidence",
    heading: "Release Evidence",
    signals: ["Notification Routing"],
  },
  {
    path: "/operational-audit",
    heading: "Operational Audit",
    signals: ["Live Audit Events"],
  },
] as const;

test("walks reviewer through demo readiness paths", async ({ page }) => {
  await signInAndSelectDemoProject(page);

  for (const step of demoWalkthroughSteps) {
    await test.step(`review ${step.heading}`, async () => {
      await page.goto(step.path);
      await expect(page).toHaveURL(new RegExp(`${escapeRegExp(step.path)}$`));
      await expect(
        page.getByRole("heading", { name: step.heading, exact: true }),
      ).toBeVisible();
      for (const signal of step.signals) {
        await expect(page.getByText(signal).first()).toBeVisible();
      }
    });
  }
});

async function signInAndSelectDemoProject(page: Page): Promise<void> {
  await installForgeMLApiMock(page);
  await page.goto("/login");
  await page.getByLabel("Password").fill("forgeml-local-admin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await page.getByRole("button", { name: "Select project Fraud Detection" }).click();
  await expect(
    page.getByText("Selected Fraud Detection as the active project."),
  ).toBeVisible();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
