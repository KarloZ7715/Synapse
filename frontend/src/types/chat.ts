import type { ClassificationMetadata, HeadKey } from "./classifier";

/** Contrato previsto con FastAPI (Fase 9); el frontend solo tipa aquí. */
export type MessageRole = "user" | "assistant";
export type LlmProvider = "groq" | "gemini";

export type HeadConfidences = Record<HeadKey, number>;

export type ChatMessage = {
  rol: MessageRole;
  contenido: string;
};

export type ChatOptions = {
  model_id?: string;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
};

export type ChatRequest = {
  pregunta: string;
  metadata: ClassificationMetadata;
  historial?: ChatMessage[];
  head_confidences?: HeadConfidences;
  options?: ChatOptions;
};

export type ChatUsage = {
  type: "usage";
  provider: LlmProvider;
  tokens_input: number;
  tokens_output: number;
  latency_ms: number;
};

export type ChatTokenEvent = {
  token: string;
};

export type ChatErrorEvent = {
  error: string;
  detail?: string;
};

export type ChatStreamEvent = ChatTokenEvent | ChatUsage | ChatErrorEvent;
