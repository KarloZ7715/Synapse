import { createStore } from "solid-js/store";
import type { ClassificationResult } from "~/types/classifier";
import type { ChatUsage } from "~/types/chat";

export type LlmState = {
  status: "idle" | "streaming" | "done" | "error";
  response: string;
  usage: ChatUsage | null;
  error: string | null;
};

export type ClassificationTurnState = {
  status: "pending" | "done" | "error";
  result: ClassificationResult | null;
  error: string | null;
};

export type ConversationTurn = {
  id: string;
  submittedText: string;
  classification: ClassificationTurnState;
  llm: LlmState;
};

export function createEmptyLlmState(): LlmState {
  return {
    status: "idle",
    response: "",
    usage: null,
    error: null,
  };
}

export type ConversationStore = {
  draftQuestion: string;
  turns: ConversationTurn[];
  lastSubmittedText: string | null;
  lastResult: ClassificationResult | null;
  llm: LlmState;
};

export function createConversationStore() {
  const [state, setState] = createStore<ConversationStore>({
    draftQuestion: "",
    turns: [],
    lastSubmittedText: null,
    lastResult: null,
    llm: createEmptyLlmState(),
  });
  return { state, setState } as const;
}
