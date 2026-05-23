import { expect, test } from "@playwright/test";

test.describe("Example prompt carousel", () => {
  test("muestra ejemplos y permite navegar", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByLabel("Ejemplos de consultas")).toBeVisible();
    await expect(page.getByTestId("example-prompt-card")).toBeVisible();

    const firstText = await page.getByTestId("example-prompt-card").innerText();
    await page.getByRole("button", { name: "Siguiente ejemplo" }).click();
    await expect(page.getByTestId("example-prompt-card")).not.toHaveText(firstText, {
      timeout: 3000,
    });

    await page.getByTestId("example-prompt-card").click();
    await expect(page.getByTestId("chat-input")).not.toHaveValue("");
  });
});
