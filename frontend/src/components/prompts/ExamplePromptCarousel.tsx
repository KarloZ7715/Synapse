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
      class="mb-2 border border-outline-variant/70 bg-surface-container-lowest/80"
      aria-label="Ejemplos de consultas"
    >
      <div class="flex items-center gap-0 overflow-hidden py-0.5">
        <button
          type="button"
          class="example-carousel-nav shrink-0"
          onClick={() => go("prev")}
          disabled={props.disabled || total <= 1}
          aria-label="Ejemplo anterior"
        >
          <span class="material-symbols-outlined">chevron_left</span>
        </button>

        <div class="relative min-w-0 flex-1 overflow-hidden px-1">
          <Show when={slideKey()} keyed>
            {() => (
              <div class={`example-slide-panel ${animClass()}`}>
                <button
                  type="button"
                  class="example-prompt-card group w-full rounded-sm px-1 py-0.5 text-left disabled:cursor-not-allowed disabled:opacity-40"
                  onClick={useExample}
                  disabled={props.disabled}
                  data-testid="example-prompt-card"
                >
                  <p class="line-clamp-2 font-mono text-xs leading-snug text-on-surface-variant group-hover:text-primary-fixed">
                    {current().text}
                  </p>
                </button>
              </div>
            )}
          </Show>
        </div>

        <button
          type="button"
          class="example-carousel-nav shrink-0"
          onClick={() => go("next")}
          disabled={props.disabled || total <= 1}
          aria-label="Siguiente ejemplo"
        >
          <span class="material-symbols-outlined">chevron_right</span>
        </button>
      </div>

      <div class="example-carousel-dots" role="tablist" aria-label="Seleccionar ejemplo">
        <For each={EXAMPLE_PROMPTS}>
          {(_item, i) => (
            <button
              type="button"
              role="tab"
              class="example-carousel-dot-btn"
              classList={{ "is-active": i() === index() }}
              onClick={() => {
                const target = i();
                const from = index();
                if (props.disabled || target === from) return;
                const dir: SlideDirection = target > from ? "next" : "prev";
                advanceTo(target, dir);
              }}
              aria-label={`Ir al ejemplo ${i() + 1}`}
              aria-selected={i() === index()}
            >
              <span class="example-carousel-dot" aria-hidden="true" />
            </button>
          )}
        </For>
      </div>
    </section>
  );
}
