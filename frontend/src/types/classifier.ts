/**
 * Fuente de verdad alineada con `neural_network/scripts/training_labels.py`
 * y el export ONNX (`export_onnx.py`).
 */
export const NIVEL_TECNICO = ["principiante", "intermedio", "avanzado"] as const;
export const URGENCIA = ["baja", "media", "alta"] as const;
export const EMOCION = [
  "frustracion",
  "confusion",
  "curiosidad",
  "ansiedad",
  "motivacion",
  "abrumado",
  "confiado",
  "desesperado",
  "neutral",
] as const;
export const DOMINIO = [
  "backend",
  "frontend",
  "bases_de_datos",
  "movil",
  "devops",
  "data_science",
  "sistemas_seguridad",
  "general",
] as const;

export const LABEL_SPECS = {
  nivel_tecnico: NIVEL_TECNICO,
  urgencia: URGENCIA,
  emocion: EMOCION,
  dominio: DOMINIO,
} as const;

export type HeadKey = keyof typeof LABEL_SPECS;

export const HEAD_KEYS: readonly HeadKey[] = [
  "nivel_tecnico",
  "urgencia",
  "emocion",
  "dominio",
] as const;

export type NivelTecnico = (typeof NIVEL_TECNICO)[number];
export type Urgencia = (typeof URGENCIA)[number];
export type Emocion = (typeof EMOCION)[number];
export type Dominio = (typeof DOMINIO)[number];

/** Metadatos enviados al backend (F9); `confianza` agrega las 4 cabezas (media geométrica de la prob. máx. por cabeza). */
export type ClassificationMetadata = {
  nivel_tecnico: NivelTecnico;
  urgencia: Urgencia;
  emocion: Emocion;
  dominio: Dominio;
  confianza: number;
};

/** Resultado completo de inferencia local (F7). */
export type ClassificationResult = {
  metadata: ClassificationMetadata;
  /** ms desde tokenización hasta salida ORT (aprox.). */
  inferenceMs: number;
  /** Backend ORT usado en el worker. */
  ortBackend: "webgpu" | "wasm";
  /** Probabilidad máxima por cabeza tras softmax (0–1). */
  headConfidences: Record<HeadKey, number>;
};

export type ClassifierStatus = "idle" | "loading_model" | "ready" | "classifying" | "error";
