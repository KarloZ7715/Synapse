import { render, screen } from "@solidjs/testing-library";
import { describe, expect, it } from "vitest";
import { MetadataPanel } from "~/components/MetadataPanel";

describe("MetadataPanel", () => {
  it("muestra estado y metadatos cuando hay resultado", () => {
    render(() => (
      <MetadataPanel
        status="ready"
        loadMs={120}
        error={null}
        result={{
          metadata: {
            nivel_tecnico: "intermedio",
            urgencia: "alta",
            emocion: "frustracion",
            dominio: "backend",
            confianza: 0.75,
          },
          inferenceMs: 42,
          ortBackend: "wasm",
          headConfidences: {
            nivel_tecnico: 0.5,
            urgencia: 0.9,
            emocion: 0.8,
            dominio: 0.7,
          },
        }}
      />
    ));
    expect(screen.getByTestId("metadata-panel")).toBeTruthy();
    expect(screen.getByText("intermedio")).toBeTruthy();
    expect(screen.getByText("frustracion")).toBeTruthy();
  });
});
