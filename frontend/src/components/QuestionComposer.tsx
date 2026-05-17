import type { SetStoreFunction } from "solid-js/store";
import type { ConversationStore } from "~/store/conversation";

type Props = {
  state: ConversationStore;
  setState: SetStoreFunction<ConversationStore>;
  disabled: boolean;
  onClassify: () => void | Promise<void>;
};

export function QuestionComposer(props: Props) {
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!props.disabled) {
        void props.onClassify();
      }
    }
  };

  return (
    <section
      class="flex min-h-0 flex-1 flex-col gap-3 rounded-lg border border-[#292930] bg-[#141418] p-4"
      aria-label="Entrada de pregunta"
    >
      <h2 class="text-heading-sm font-semibold text-[#ededef]">Chat (Fase 8)</h2>
      <p class="text-body-sm text-[#9898a0]">
        Área reservada para conversación. En Fase 7 solo se clasifica localmente la pregunta.
      </p>
      <textarea
        class="font-mono-ui min-h-[120px] flex-1 resize-y rounded-lg bg-[#1c1c22] px-3 py-2 text-body text-[#ededef] outline-none ring-cyan-400/30 focus:ring-1"
        placeholder="Escribe tu duda de programación… (Enter envía, Shift+Enter nueva línea)"
        maxlength={2000}
        value={props.state.draftQuestion}
        onInput={(e) => props.setState("draftQuestion", e.currentTarget.value)}
        onKeyDown={onKeyDown}
        disabled={props.disabled}
        data-testid="question-input"
      />
      <div class="flex justify-end gap-2">
        <button
          type="button"
          class="rounded-md bg-[#22d3ee] px-4 py-2 text-sm font-medium text-[#0a0a0c] transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={props.disabled || props.state.draftQuestion.trim().length === 0}
          onClick={() => void props.onClassify()}
          data-testid="classify-button"
        >
          Clasificar localmente
        </button>
      </div>
    </section>
  );
}
