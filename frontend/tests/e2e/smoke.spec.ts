import { expect, test } from "@playwright/test";

test("opens dashboard and navigates to projects", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await page.getByRole("link", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  await page.getByRole("link", { name: "Projects" }).click();
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
  await page.getByRole("button", { name: "New" }).click();
  await expect(page.getByRole("form", { name: "Create project" })).toBeVisible();
  await page.getByLabel("Name").fill("Audience Forecasting");
  await page.getByLabel("Description").fill("Demand planning models");
  await page.getByRole("button", { name: "Create project" }).click();
  await expect(page.getByRole("cell", { name: "Audience Forecasting" })).toBeVisible();

  await page.getByRole("link", { name: "Examples" }).click();
  await expect(page.getByRole("heading", { name: "Example Projects" })).toBeVisible();

  await page.getByRole("link", { name: "Feature Store" }).click();
  await expect(page.getByRole("heading", { name: "Feature Store" })).toBeVisible();

  await page.getByRole("link", { name: "Experiments" }).click();
  await expect(page.getByRole("heading", { name: "Experiments" })).toBeVisible();

  await page.getByRole("link", { name: "Training Runs" }).click();
  await expect(page.getByRole("heading", { name: "Training Runs" })).toBeVisible();

  await page.getByRole("link", { name: "Models" }).click();
  await expect(page.getByRole("heading", { name: "Models" })).toBeVisible();

  await page.getByRole("link", { name: "Deployments" }).click();
  await expect(page.getByRole("heading", { name: "Deployments" })).toBeVisible();

  await page.getByRole("link", { name: "Inference" }).click();
  await expect(page.getByRole("heading", { name: "Inference" })).toBeVisible();

  await page.getByRole("link", { name: "Monitoring" }).click();
  await expect(page.getByRole("heading", { name: "Monitoring" })).toBeVisible();

  await page.getByRole("link", { name: "Drift" }).click();
  await expect(page.getByRole("heading", { name: "Drift Detection" })).toBeVisible();

  await page.getByRole("link", { name: "Retraining" }).click();
  await expect(page.getByRole("heading", { name: "Retraining", exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Alerts" }).click();
  await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
});
