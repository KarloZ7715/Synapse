/**
 * Hiperparámetros fijos del run de referencia (`run_config.json` del checkpoint).
 * Deben coincidir con el ONNX exportado para esa corrida.
 */
export const MODEL_MAX_LEN = 160;

export const MODEL_ONNX_FILENAME = "synapse_textcnn.onnx" as const;

export const MODEL_VOCAB_FILENAME = "vocab.json" as const;

export const ONNX_INPUT_NAME = "input_ids" as const;

export const ONNX_OUTPUT_NAMES = [
  "logits_nivel_tecnico",
  "logits_urgencia",
  "logits_emocion",
  "logits_dominio",
] as const;

/** Base pública bajo la que viven `synapse_textcnn.onnx` y `vocab.json` tras `pnpm sync:model`. */
export const MODEL_ASSETS_SUBPATH = "models/" as const;
