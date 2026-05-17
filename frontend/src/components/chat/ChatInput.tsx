import { createSignal } from "solid-js";
import { ChevronDown, Paperclip, Send } from "~/components/icons";

export function ChatInput(props: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}) {
  const [rows, setRows] = createSignal(1);

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!props.disabled && props.value.trim()) {
        props.onSubmit();
      }
    }
  };

  const onInput = (e: InputEvent & { currentTarget: HTMLTextAreaElement }) => {
    const val = e.currentTarget.value;
    props.onChange(val);
    const lineCount = val.split("\n").length;
    setRows(Math.min(6, Math.max(1, lineCount)));
  };

  return (
    <div class="shrink-0 border-t border-[var(--border-color)] bg-[var(--bg-base)]/80 p-4 backdrop-blur-sm">
      <div class="rounded-xl bg-[var(--bg-surface)] p-3 ring-1 ring-[var(--border-color)] transition-all focus-within:ring-[#22d3ee]/40 focus-within:shadow-[0_0_20px_rgba(34,211,238,0.08)]">
        <textarea
          class="w-full resize-none bg-transparent text-sm leading-relaxed text-[var(--text-primary)] outline-none placeholder:text-[var(--text-tertiary)]/60"
          rows={rows()}
          placeholder="Escribe tu duda de programación..."
          value={props.value}
          onInput={onInput}
          onKeyDown={onKeyDown}
          disabled={props.disabled}
          data-testid="chat-input"
        />
        <div class="flex items-center justify-between pt-2">
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[10px] font-mono text-[var(--text-tertiary)] transition-all hover:bg-[var(--bg-elevated)] hover:text-[var(--text-secondary)]"
            disabled={props.disabled}
          >
            <Paperclip color="var(--text-tertiary)" size={12} />
            Adjuntar código
          </button>
          <div class="flex items-center gap-2">
            <div class="relative">
              <select
                class="appearance-none rounded-lg bg-transparent py-1 pl-2.5 pr-7 text-[10px] font-mono text-[var(--text-secondary)] outline-none ring-1 ring-[var(--border-color)] transition-all hover:ring-[var(--text-tertiary)]"
              >
                <option>Groq · Llama 3.1 8B</option>
                <option>Gemini · Gemma 4 26B</option>
              </select>
              <ChevronDown
                class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2"
                color="var(--text-tertiary)"
                size={12}
              />
            </div>
            <button
              type="button"
              onClick={props.onSubmit}
              disabled={props.disabled || !props.value.trim()}
              class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[#22d3ee] to-[#0ea5e9] text-white shadow-[0_0_12px_rgba(34,211,238,0.25)] transition-all hover:shadow-[0_0_20px_rgba(34,211,238,0.4)] disabled:opacity-40 disabled:shadow-none"
              aria-label="Enviar"
            >
              <Send color="#fff" size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
