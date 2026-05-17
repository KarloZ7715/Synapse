import { test, expect } from "@playwright/test";

test.describe("Theme System", () => {
  test("defaults to dark mode", async ({ page }) => {
    await page.goto("/");
    const html = await page.locator("html").getAttribute("data-theme");
    expect(html).toBe("dark");
  });

  test("toggle switches to light mode", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /modo claro/i }).click();
    const html = await page.locator("html").getAttribute("data-theme");
    expect(html).toBe("light");
  });
});
