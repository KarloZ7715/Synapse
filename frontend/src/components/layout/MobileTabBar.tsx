import { For } from "solid-js";
import type { PipelineTab } from "~/store/ui";

const TABS: ReadonlyArray<{ id: PipelineTab; short: string; icon: string }> = [
  { id: "input", short: "Input", icon: "input" },
  { id: "tokenizer", short: "Tokens", icon: "code" },
  { id: "neural-network", short: "Red", icon: "hub" },
  { id: "classification", short: "Clasif.", icon: "category" },
  { id: "prompt", short: "Prompt", icon: "terminal" },
  { id: "llm", short: "Gen", icon: "psychology" },
];

export function MobileTabBar(props: {
  active: PipelineTab;
  onSelect: (tab: PipelineTab) => void;
}) {
  return (
    <nav
      aria-label="Pestañas del pipeline (móvil)"
      class="flex shrink-0 overflow-x-auto border-b border-outline-variant bg-surface-container-low"
    >
      <For each={TABS}>
        {(tab) => {
          const isActive = () => props.active === tab.id;
          return (
            <button
              type="button"
              onClick={() => props.onSelect(tab.id)}
              class="flex shrink-0 flex-col items-center gap-1 border-b-2 px-4 py-2 font-mono text-[10px] font-bold uppercase tracking-wider transition-colors"
              classList={{
                "border-secondary-fixed bg-secondary-fixed/10 text-secondary-fixed":
                  isActive(),
                "border-transparent text-on-surface-variant hover:bg-surface-variant/30":
                  !isActive(),
              }}
              aria-current={isActive() ? "page" : undefined}
            >
              <span
                class="material-symbols-outlined text-lg"
                classList={{
                  "[font-variation-settings:'FILL'_1]": isActive(),
                  "[font-variation-settings:'FILL'_0]": !isActive(),
                }}
              >
                {tab.icon}
              </span>
              <span>{tab.short}</span>
            </button>
          );
        }}
      </For>
    </nav>
  );
}
