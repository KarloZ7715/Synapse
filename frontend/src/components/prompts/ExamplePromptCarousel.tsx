import { For, Show, createMemo, createSignal } from "solid-js";
import { EXAMPLE_PROMPTS, type ExamplePrompt } from "~/config/examplePrompts";

type SlideDirection = "next" | "prev";

export function ExamplePromptCarousel(props: {
  disabled?: boolean;
  onSelect: (text: string) => void;
}) {
  const total = EXAMPLE_PROMPTS.length;
  const [index, setIndex] = createSignal(0);
  const [slideKey, setSlideKey] = createSignal("slide-0");
  const [animClass, setAnimClass] = createSignal("example-slide-enter");

  const current = createMemo<ExamplePrompt>(() => EXAMPLE_PROMPTS[index()] ?? EXAMPLE_PROMPTS[0]);

  const advanceTo = (nextIndex: number, dir: SlideDirection) => {
    setAnimClass(dir === "next" ? "example-slide-exit-left" : "example-slide-exit-right");
    window.setTimeout(() => {
      setIndex(nextIndex);
      setSlideKey(`slide-${nextIndex}-${Date.now()}`);
      setAnimClass(dir === "next" ? "example-slide-enter-right" : "example-slide-enter-left");
    }, 180);
  };

  const go = (dir: SlideDirection) => {
    if (props.disabled || total <= 1) return;
    const nextIndex =
      dir === "next" ? (index() + 1) % total : (index() - 1 + total) % total;
    advanceTo(nextIndex, dir);
  };

  const useExample = () => {
    if (props.disabled) return;
    props.onSelect(current().text);
  };

  return (
    <section
      class="mb-3 border border-outline-variant bg-surface-container-lowest/90"
      aria-label="Ejemplos de consultas"
    >
      <div class="flex items-center justify-between border-b border-outline-variant bg-surface-container-high/60 px-3 py-1.5">
        <div class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-on-surface-variant">
          <span class="material-symbols-outlined text-sm text-primary-fixed">tips_and_updates</span>
          <span>Ejemplos · RN + LLM</span>
        </div>
        <span class="font-mono text-[10px] tabular-nums text-on-surface-variant">
          {index() + 1} / {total}
        </span>
      </div>

      <div class="relative flex items-stretch gap-0 overflow-hidden p-2">
        <button
          type="button"
          class="example-carousel-nav shrink-0 self-center"
          onClick={() => go("prev")}
          disabled={props.disabled || total <= 1}
          aria-label="Ejemplo anterior"
        >
          <span class="material-symbols-outlined">chevron_left</span>
        </button>

        <div class="relative min-h-14 min-w-0 flex-1 overflow-hidden px-1">
          <Show when={slideKey()} keyed>
            {() => (
              <div class={`example-slide-panel ${animClass()}`}>
                <button
                  type="button"
                  class="group w-full border border-outline-variant/80 bg-surface-container-low p-3 text-left transition-colors hover:border-primary-fixed/50 hover:bg-primary-fixed/5 disabled:cursor-not-allowed disabled:opacity-40"
                  onClick={useExample}
                  disabled={props.disabled}
                  data-testid="example-prompt-card"
                >
                  <p class="line-clamp-2 font-mono text-[12px] leading-relaxed text-on-surface group-hover:text-primary-fixed">
                    {current().text}
                  </p>
                  <div class="mt-2 flex flex-wrap gap-1.5">
                    <Tag label={current().domain.replaceAll("_", " ")} variant="domain" />
                    <Tag label={current().nivel} variant="muted" />
                    <Tag label={current().emotion} variant="accent" />
                  </div>
                </button>
              </div>
            )}
          </Show>
        </div>

        <button
          type="button"
          class="example-carousel-nav shrink-0 self-center"
          onClick={() => go("next")}
          disabled={props.disabled || total <= 1}
          aria-label="Siguiente ejemplo"
        >
          <span class="material-symbols-outlined">chevron_right</span>
        </button>
      </div>

      <div class="flex justify-center gap-1 border-t border-outline-variant/60 px-3 py-2">
        <For each={EXAMPLE_PROMPTS}>
          {(_item, i) => (
            <button
              type="button"
              class="h-1.5 w-1.5 border border-outline-variant transition-all duration-300"
              classList={{
                "scale-125 border-primary-fixed bg-primary-fixed shadow-[0_0_6px_var(--color-primary-fixed)]":
                  i() === index(),
                "bg-surface-variant hover:bg-primary-fixed/40": i() !== index(),
              }}
              onClick={() => {
                const target = i();
                const from = index();
                if (props.disabled || target === from) return;
                const dir: SlideDirection = target > from ? "next" : "prev";
                advanceTo(target, dir);
              }}
              aria-label={`Ir al ejemplo ${i() + 1}`}
              aria-current={i() === index() ? "true" : undefined}
            />
          )}
        </For>
      </div>
    </section>
  );
}

function Tag(props: { label: string; variant: "domain" | "muted" | "accent" }) {
  const cls = () => {
    if (props.variant === "domain") {
      return "border-secondary-fixed/40 bg-secondary-fixed/10 text-secondary-fixed";
    }
    if (props.variant === "accent") {
      return "border-primary-fixed/40 bg-primary-fixed/10 text-primary-fixed";
    }
    return "border-outline-variant bg-surface-variant text-on-surface-variant";
  };
  return (
    <span class={`px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide ${cls()}`}>
      {props.label}
    </span>
  );
}
