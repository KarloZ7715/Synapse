import { Show } from "solid-js";
import type { ClassificationResult } from "~/types/classifier";

export function CommandInput(props: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  lastResult: ClassificationResult | null;
}) {
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!props.disabled && props.value.trim()) {
        props.onSubmit();
      }
    }
  };
  return (
    <div class="z-10 shrink-0 border-t border-outline-variant bg-surface-container-lowest/90 p-6 backdrop-blur-md">
      <Show when={props.lastResult}>
        {(r) => (
          <div
            data-testid="metadata-panel"
            class="mb-3 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-wider"
          >
            <span class="border border-outline-variant bg-surface-variant px-2 py-1 text-on-surface">
              [TECH_LEVEL: {r().metadata.nivel_tecnico}]
            </span>
            <span class="border border-outline-variant bg-surface-variant px-2 py-1 text-on-surface">
              [URGENCY: {r().metadata.urgencia}]
            </span>
            <span class="border border-primary-fixed/50 bg-primary-fixed/20 px-2 py-1 text-primary-fixed">
              [EMOTION: {r().metadata.emocion}]
            </span>
            <span class="border border-outline-variant bg-surface-variant px-2 py-1 text-on-surface">
              [DOMAIN: {r().metadata.dominio}]
            </span>
          </div>
        )}
      </Show>
      <div class="relative flex items-end border-b-2 border-primary-fixed bg-surface transition-shadow focus-within:shadow-[0_4px_12px_rgba(57,255,20,0.2)]">
        <span class="absolute bottom-3 left-0 pl-2 font-mono text-primary-fixed">&gt;</span>
        <textarea
          data-testid="chat-input"
          class="h-12 w-full resize-none border-none bg-transparent p-3 pl-6 font-mono text-sm text-on-surface focus:outline-none focus:ring-0"
          placeholder={props.disabled ? "Esperando modelo..." : "Ingresa tu duda de programación..."}
          rows={1}
          value={props.value}
          disabled={props.disabled}
          onInput={(e) => props.onChange(e.currentTarget.value)}
          onKeyDown={onKeyDown}
        />
        <button
          type="button"
          class="mb-2 mr-2 p-1 text-primary-fixed transition-colors hover:bg-primary-fixed/20 disabled:cursor-not-allowed disabled:opacity-30"
          disabled={props.disabled || !props.value.trim()}
          onClick={props.onSubmit}
          aria-label="Enviar"
        >
          <span class="material-symbols-outlined" style={{ "font-variation-settings": "'FILL' 1" }}>
            send
          </span>
        </button>
      </div>
      <p class="mt-2 font-mono text-[10px] uppercase tracking-wider text-on-surface-variant">
        Enter envía · Shift+Enter nueva línea
      </p>
    </div>
  );
}
