import { createEffect } from "solid-js";
import { ExamplePromptCarousel } from "~/components/prompts/ExamplePromptCarousel";

const TEXTAREA_MIN_PX = 48;
const TEXTAREA_MAX_PX = 160;

function resizeTextarea(el: HTMLTextAreaElement) {
  el.style.height = "0px";
  const contentHeight = el.scrollHeight;
  const next = Math.min(Math.max(contentHeight, TEXTAREA_MIN_PX), TEXTAREA_MAX_PX);
  el.style.height = `${next}px`;
  el.style.overflowY = contentHeight > TEXTAREA_MAX_PX ? "auto" : "hidden";
}

export function CommandInput(props: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}) {
  let textareaEl: HTMLTextAreaElement | undefined;

  createEffect(() => {
    props.value;
    if (textareaEl) {
      resizeTextarea(textareaEl);
    }
  });

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
      <ExamplePromptCarousel
        disabled={props.disabled}
        onSelect={(text) => props.onChange(text)}
      />
      <div class="relative flex items-end border-b-2 border-primary-fixed bg-surface transition-shadow focus-within:shadow-[0_4px_12px_rgba(57,255,20,0.2)]">
        <span class="absolute bottom-3 left-0 pl-2 font-mono text-primary-fixed">&gt;</span>
        <textarea
          ref={(el) => {
            textareaEl = el;
            resizeTextarea(el);
          }}
          data-testid="chat-input"
          class="min-h-12 w-full resize-none overflow-hidden border-none bg-transparent p-3 pl-6 font-mono text-sm text-on-surface focus:outline-none focus:ring-0"
          placeholder={props.disabled ? "Esperando modelo..." : "Ingresa tu duda de programación..."}
          rows={1}
          value={props.value}
          disabled={props.disabled}
          onInput={(e) => {
            props.onChange(e.currentTarget.value);
            resizeTextarea(e.currentTarget);
          }}
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
