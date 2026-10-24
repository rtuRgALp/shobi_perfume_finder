import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";

test("browse, dark appearance and mobile filters have no automated WCAG violations", async ({
  page,
  isMobile,
}) => {
  await page.goto("/");
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  for (let appearance = 0; appearance < 2; appearance++) {
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
    if (!appearance)
      await page
        .getByRole("button", { name: "Switch to dark appearance" })
        .click();
  }
  if (isMobile) {
    await page.getByRole("button", { name: "Filters", exact: true }).click();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(
      page.getByRole("button", { name: "Filters", exact: true }),
    ).toBeFocused();
  }
});

test("details support keyboard navigation without automated WCAG violations", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".perfume-card")).toHaveCount(24);
  await page.locator(".card-copy h3 a").first().click();
  await expect(page.locator("#perfume-title")).toBeFocused();
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});
