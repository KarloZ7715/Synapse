import { For } from "solid-js";
import { Zap } from "~/components/icons";
import { ChatInput } from "~/components/chat/ChatInput";
import { ChatMessage } from "~/components/chat/ChatMessage";
import type { ConversationStore } from "~/store/conversation";
import type { SetStoreFunction } from "solid-js/store";

export function ChatPanel(props: {
  state: ConversationStore;
  setState: SetStoreFunction<ConversationStore>;
  disabled: boolean;
  onClassify: () => void | Promise<void>;
}) {
  const messages = () => props.state.messages || [];

  return (
    <section class="flex min-h-0 flex-1 flex-col" aria-label="Chat Central">
      {/* Messages area */}
      <div class="flex-1 overflow-y-auto p-4">
        <div class="flex flex-col gap-4">
          <For each={messages()}>
            {(msg) => <ChatMessage message={msg} />}
          </For>
          {messages().length === 0 && (
            <div class="flex flex-1 flex-col items-center justify-center gap-4 pt-20 opacity-50">
              <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[var(--bg-elevated)] to-[var(--bg-surface)] ring-1 ring-[var(--border-color)]">
                <Zap color="#22d3ee" size={32} />
              </div>
              <div class="text-center">
                <p class="text-sm font-medium text-[var(--text-secondary)]">Synapse está listo</p>
                <p class="mt-1 text-xs text-[var(--text-tertiary)]">
                  Pregúntame sobre cualquier lenguaje o framework
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <ChatInput
        value={props.state.draftQuestion}
        onChange={(v) => props.setState("draftQuestion", v)}
        onSubmit={() => void props.onClassify()}
        disabled={props.disabled}
      />
    </section>
  );
}
