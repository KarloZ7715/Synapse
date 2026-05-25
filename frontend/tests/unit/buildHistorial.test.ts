import { describe, expect, it } from "vitest";
import { buildHistorial } from "~/lib/buildHistorial";
import type { ConversationTurn } from "~/store/conversation";
import { createEmptyLlmState } from "~/store/conversation";

function turn(
  id: string,
  text: string,
  reply?: string,
): ConversationTurn {
  return {
    id,
    submittedText: text,
    classification: { status: "done", result: null, error: null },
    llm: reply
      ? { ...createEmptyLlmState(), status: "done", response: reply }
      : createEmptyLlmState(),
  };
}

describe("buildHistorial", () => {
  it("incluye turnos previos completados y excluye el turno actual", () => {
    const turns = [
      turn("t1", "Primera pregunta", "Primera respuesta"),
      turn("t2", "Segunda pregunta"),
    ];
    const historial = buildHistorial(turns, "t2");
    expect(historial).toEqual([
      { rol: "user", contenido: "Primera pregunta" },
      { rol: "assistant", contenido: "Primera respuesta" },
    ]);
  });

  it("limita a los ultimos 10 mensajes", () => {
    const turns: ConversationTurn[] = [];
    for (let i = 0; i < 8; i++) {
      turns.push(turn(`t${i}`, `q${i}`, `a${i}`));
    }
    turns.push(turn("current", "ultima"));
    const historial = buildHistorial(turns, "current");
    expect(historial.length).toBeLessThanOrEqual(10);
    expect(historial.at(-1)?.contenido).toBe("a7");
  });
});
