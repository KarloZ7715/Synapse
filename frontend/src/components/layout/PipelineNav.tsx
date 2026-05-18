import { For } from "solid-js";
import type { PipelineTab } from "~/store/ui";
import type { ClassifierStatus } from "~/types/classifier";

const TABS: ReadonlyArray<{ id: PipelineTab; label: string; icon: string }> = [
  { id: "input", label: "Input", icon: "input" },
  { id: "tokenizer", label: "Tokenizer", icon: "code" },
  { id: "neural-network", label: "Neural Network", icon: "hub" },
  { id: "classification", label: "Classification", icon: "category" },
  { id: "prompt", label: "Prompt", icon: "terminal" },
  { id: "llm", label: "LLM · Generación", icon: "psychology" },
];

function tabNodeState(
  status: ClassifierStatus,
  index: number,
): "pending" | "active" | "done" | "error" {
  if (status === "error" && index === 2) return "error";
  if (status === "loading_model") return index <= 2 ? "active" : "pending";
  if (status === "classifying") return index <= 3 ? "active" : "pending";
  if (status === "ready") return index <= 3 ? "done" : "pending";
  return "pending";
}

export function PipelineNav(props: {
  active: PipelineTab;
  onSelect: (tab: PipelineTab) => void;
  status: ClassifierStatus;
}) {
  return (
    <nav
      aria-label="Etapas del pipeline"
      class="scanlines relative z-40 flex h-full w-column-pipeline shrink-0 flex-col border-r border-outline-variant bg-surface-container-low"
    >
      <div class="flex flex-col items-center justify-center border-b border-outline-variant p-6">
        <div class="mb-4 flex h-16 w-16 items-center justify-center border-2 border-secondary-fixed bg-surface-dim shadow-[0_0_10px_var(--color-secondary-fixed)]">
          <span class="material-symbols-outlined text-3xl text-secondary-fixed">account_tree</span>
        </div>
        <h2 class="font-mono text-[12px] font-bold tracking-widest text-secondary-fixed">
          PIPELINE
        </h2>
        <p class="mt-1 font-mono text-[10px] text-on-surface-variant">SEQUENCE_01</p>
      </div>

      <ul class="flex flex-1 flex-col gap-1 overflow-y-auto py-4 font-mono text-[12px]">
        <For each={TABS}>
          {(tab, i) => {
            const isActive = () => props.active === tab.id;
            const flowState = () => tabNodeState(props.status, i());
            return (
              <li>
                <button
                  type="button"
                  onClick={() => props.onSelect(tab.id)}
                  class="group relative flex w-full items-center gap-3 py-4 text-left transition-colors"
                  classList={{
                    "border-l-4 border-secondary-fixed bg-secondary-fixed/10 text-secondary-fixed pl-3":
                      isActive(),
                    "pl-4 text-on-surface-variant hover:bg-surface-variant/30 hover:text-on-surface":
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
                  <span class="relative z-10 font-bold uppercase tracking-wider">
                    {tab.label}
                  </span>
                  {/* Flow status dot — separate from tab selection */}
                  <span
                    class="ml-auto mr-4 h-1.5 w-1.5 rounded-full"
                    classList={{
                      "animate-ping bg-secondary-fixed": isActive(),
                      "bg-primary-fixed shadow-[0_0_6px_var(--color-primary-fixed)]":
                        !isActive() && flowState() === "done",
                      "bg-error animate-pulse": !isActive() && flowState() === "error",
                      "bg-secondary-fixed/50 animate-pulse":
                        !isActive() && flowState() === "active",
                      "bg-outline-variant": !isActive() && flowState() === "pending",
                    }}
                    aria-hidden="true"
                  />
                </button>
              </li>
            );
          }}
        </For>
      </ul>

      <div class="flex flex-col gap-2 border-t border-outline-variant p-4">
        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 border border-error bg-error/10 py-3 font-mono text-[10px] uppercase tracking-widest text-error transition-all hover:bg-error hover:text-on-error"
          onClick={() => window.location.reload()}
        >
          <span class="material-symbols-outlined text-sm">warning</span>
          RESET_SYSTEM
        </button>
      </div>
    </nav>
  );
}
