import { describe, expect, it } from "vitest";
import { ONNX_OUTPUT_NAMES } from "~/config/model";
import { postprocessOrtOutputs } from "~/utils/postprocess";

describe("postprocessOrtOutputs", () => {
  it("mapea logits a etiquetas y confianza", () => {
    const logitsNivel = new Float32Array([10, 0, 0]);
    const logitsUrg = new Float32Array([0, 5, 0]);
    const logitsEmo = new Float32Array([0, 0, 0, 0, 0, 0, 0, 0, 8]);
    const logitsDom = new Float32Array([9, 0, 0, 0, 0, 0, 0, 0]);
    const map: Record<string, Float32Array> = {
      [ONNX_OUTPUT_NAMES[0]]: logitsNivel,
      [ONNX_OUTPUT_NAMES[1]]: logitsUrg,
      [ONNX_OUTPUT_NAMES[2]]: logitsEmo,
      [ONNX_OUTPUT_NAMES[3]]: logitsDom,
    };
    const { metadata, headConfidences } = postprocessOrtOutputs(map);
    expect(metadata.nivel_tecnico).toBe("principiante");
    expect(metadata.urgencia).toBe("media");
    expect(metadata.emocion).toBe("neutral");
    expect(metadata.dominio).toBe("backend");
    expect(metadata.confianza).toBeGreaterThan(0);
    expect(metadata.confianza).toBeLessThanOrEqual(1);
    expect(headConfidences.nivel_tecnico).toBeGreaterThan(0.5);
  });
});
