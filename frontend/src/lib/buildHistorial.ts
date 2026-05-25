import type { ConversationTurn } from "~/store/conversation";
import type { ChatMessage } from "~/types/chat";

/** Ultimos 10 mensajes (5 pares), alineado con ChatRequest.historial en el backend. */
export const MAX_HISTORIAL_MESSAGES = 10;

/**
 * Historial de turnos completados antes del turno actual.
 * Politica: cada turno nuevo se clasifica de nuevo; el historial solo aporta contexto conversacional.
 */
export function buildHistorial(
  turns: ConversationTurn[],
  beforeTurnId: string,
): ChatMessage[] {
  const messages: ChatMessage[] = [];

  for (const turn of turns) {
    if (turn.id === beforeTurnId) {
      break;
    }
    const question = turn.submittedText.trim();
    if (question) {
      messages.push({ rol: "user", contenido: question });
    }
    const reply = turn.llm.response.trim();
    if (turn.llm.status === "done" && reply) {
      messages.push({ rol: "assistant", contenido: reply });
    }
  }

  return messages.slice(-MAX_HISTORIAL_MESSAGES);
}
