import { createStore } from "solid-js/store";
import type { Message } from "~/components/chat/ChatMessage";
import type { ClassificationResult } from "~/types/classifier";

export type ConversationStore = {
  draftQuestion: string;
  lastResult: ClassificationResult | null;
  messages: Message[];
};

export function createConversationStore() {
  const [state, setState] = createStore<ConversationStore>({
    draftQuestion: "",
    lastResult: null,
    messages: [],
  });
  return { state, setState } as const;
}
