import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const onnxPath = path.join(__dirname, "..", "..", "public", "models", "synapse_textcnn.onnx");

test.describe("pipeline smoke", () => {
  test.skip(!fs.existsSync(onnxPath), "Ejecuta `pnpm sync:model` para habilitar inferencia E2E");

  test("carga la app y muestra metadatos tras clasificar", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Synapse")).toBeVisible();
    await page.getByTestId("chat-input").fill("No entiendo nada de recursividad en Python");
    await page.getByRole("button", { name: /enviar/i }).click();
    await expect(page.getByTestId("metadata-panel")).toContainText(
      /principiante|intermedio|avanzado/,
      {
        timeout: 90_000,
      },
    );
  });
});
