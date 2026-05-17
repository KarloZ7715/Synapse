import type { ClassificationMetadata } from "./classifier";

/** Contrato previsto con FastAPI (Fase 9); el frontend solo tipa aquí. */
export type MessageRole = "user" | "assistant";

export type ChatMessage = {
  rol: MessageRole;
  contenido: string;
};

export type ChatRequest = {
  pregunta: string;
  metadata: ClassificationMetadata;
  historial?: ChatMessage[];
};
