import { ONNX_OUTPUT_NAMES } from "~/config/model";
import {
  type ClassificationMetadata,
  HEAD_KEYS,
  type HeadKey,
  LABEL_SPECS,
} from "~/types/classifier";
import { argmax, geometricMean, softmax } from "~/utils/softmax";

const NUM_LABELS: Record<HeadKey, number> = {
  nivel_tecnico: LABEL_SPECS.nivel_tecnico.length,
  urgencia: LABEL_SPECS.urgencia.length,
  emocion: LABEL_SPECS.emocion.length,
  dominio: LABEL_SPECS.dominio.length,
};

export type OrtOutputMap = Record<string, Float32Array>;

function asFloat32(name: string, data: unknown, expectedLen: number): Float32Array {
  if (data instanceof Float32Array) {
    if (data.length !== expectedLen) {
      throw new Error(`Salida ${name}: longitud ${data.length}, esperada ${expectedLen}`);
    }
    return data;
  }
  if (Array.isArray(data) && data.length === expectedLen) {
    return Float32Array.from(data);
  }
  throw new Error(`Salida ${name}: tipo no soportado`);
}

/**
 * Convierte el mapa de logits ORT (por nombre de tensor) a metadatos + confianzas por cabeza.
 */
export function postprocessOrtOutputs(outputMap: OrtOutputMap): {
  metadata: ClassificationMetadata;
  headConfidences: Record<HeadKey, number>;
} {
  const headConfidences: Record<HeadKey, number> = {
    nivel_tecnico: 0,
    urgencia: 0,
    emocion: 0,
    dominio: 0,
  };

  const labels: Partial<Record<HeadKey, string>> = {};

  for (let i = 0; i < HEAD_KEYS.length; i++) {
    const head = HEAD_KEYS[i];
    const oname = ONNX_OUTPUT_NAMES[i];
    const raw = outputMap[oname];
    if (!raw) {
      throw new Error(`Falta salida ONNX: ${oname}`);
    }
    const logits = asFloat32(oname, raw, NUM_LABELS[head]);
    const probs = softmax(logits);
    const idx = argmax(probs);
    const spec = LABEL_SPECS[head];
    const label = spec[idx];
    if (label === undefined) {
      throw new Error(`Índice fuera de rango para ${head}: ${idx}`);
    }
    labels[head] = label;
    headConfidences[head] = probs[idx] ?? 0;
  }

  const confianza = geometricMean([
    headConfidences.nivel_tecnico,
    headConfidences.urgencia,
    headConfidences.emocion,
    headConfidences.dominio,
  ]);

  return {
    metadata: {
      nivel_tecnico: labels.nivel_tecnico as ClassificationMetadata["nivel_tecnico"],
      urgencia: labels.urgencia as ClassificationMetadata["urgencia"],
      emocion: labels.emocion as ClassificationMetadata["emocion"],
      dominio: labels.dominio as ClassificationMetadata["dominio"],
      confianza,
    },
    headConfidences,
  };
}
