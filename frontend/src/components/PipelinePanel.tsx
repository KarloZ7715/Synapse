import { For } from "solid-js";
import { Brain, FileCode, FileText, Monitor, Target, Type, Zap } from "~/components/icons";
import type { ClassifierStatus } from "~/types/classifier";

const NODES = [
  { id: "input", label: "Input", Icon: FileText },
  { id: "tokenizer", label: "Tokenizer", Icon: Type },
  { id: "rn", label: "Red Neuronal", Icon: Brain },
  { id: "classif", label: "Clasificación", Icon: Target },
  { id: "prompt", label: "Prompt", Icon: FileCode },
  { id: "llm", label: "LLM", Icon: Monitor },
] as const;

type NodeVisual = "pending" | "active" | "done" | "error";

function nodeState(status: ClassifierStatus, index: number): NodeVisual {
  if (status === "error" && index === 2) return "error";
  if (status === "loading_model") return index <= 2 ? "active" : "pending";
  if (status === "classifying") return index <= 3 ? "active" : "pending";
  if (status === "ready") return index <= 3 ? "done" : "pending";
  return "pending";
}

export function PipelinePanel(props: { status: ClassifierStatus }) {
  return (
    <aside
      class="flex w-[260px] shrink-0 flex-col gap-4 overflow-y-auto border-r border-[var(--border-color)] bg-[var(--bg-base)] p-4"
      aria-label="Pipeline de inferencia"
    >
      <h2 class="text-[10px] font-mono font-medium uppercase tracking-widest text-[var(--text-tertiary)]">
        Pipeline
      </h2>

      {/* SVG Pipeline */}
      <div class="relative flex flex-col items-center">
        <svg
          width="120"
          height="320"
          class="absolute left-1/2 -translate-x-1/2"
          style={{ "z-index": 0 }}
          role="img"
          aria-label="Pipeline connections"
        >
          <For each={NODES}>
            {(_, i) => {
              if (i() === NODES.length - 1) return null;
              const st = nodeState(props.status, i());
              return (
                <line
                  x1="60"
                  y1={32 + i() * 52}
                  x2="60"
                  y2={32 + (i() + 1) * 52}
                  stroke-width="1.5"
                  classList={{
                    "stroke-[#22d3ee]": st === "active",
                    "stroke-[#4ade80]/50": st === "done",
                    "stroke-[var(--border-color)]": st === "pending",
                    "stroke-[#f87171]/80": st === "error",
                    "animate-dash": st === "active",
                  }}
                  stroke-dasharray={st === "active" ? "4 4" : "none"}
                />
              );
            }}
          </For>
        </svg>

        <For each={NODES}>
          {(node, i) => {
            const st = () => nodeState(props.status, i());
            const isRn = node.id === "rn";
            return (
              <div class="relative z-10 flex flex-col items-center gap-1.5 py-2">
                <div
                  class="flex items-center justify-center rounded-full border-2 transition-all duration-300"
                  classList={{
                    "h-9 w-9": !isRn,
                    "h-11 w-11": isRn,
                    "border-[#22d3ee] bg-[#22d3ee]/15 shadow-[0_0_12px_rgba(34,211,238,0.25)] animate-pulse":
                      st() === "active",
                    "border-[#4ade80]/50 bg-[#4ade80]/15 shadow-[0_0_8px_rgba(74,222,128,0.15)]":
                      st() === "done",
                    "border-[#f87171]/50 bg-[#f87171]/15": st() === "error",
                    "border-[var(--border-color)] bg-[var(--bg-elevated)] opacity-40":
                      st() === "pending",
                  }}
                >
                  <node.Icon
                    color={
                      st() === "active"
                        ? "#22d3ee"
                        : st() === "done"
                          ? "#4ade80"
                          : st() === "error"
                            ? "#f87171"
                            : "var(--text-tertiary)"
                    }
                    size={isRn ? 20 : 16}
                  />
                </div>
                <span
                  class="text-[10px] font-mono font-medium"
                  classList={{
                    "text-[#22d3ee]": st() === "active",
                    "text-[#4ade80]": st() === "done",
                    "text-[#f87171]": st() === "error",
                    "text-[var(--text-tertiary)] opacity-40": st() === "pending",
                  }}
                >
                  {node.label}
                </span>
              </div>
            );
          }}
        </For>
      </div>

      {/* Info técnica */}
      <div class="space-y-2 rounded-xl bg-[var(--bg-elevated)] p-3 ring-1 ring-[var(--border-color)]">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono text-[var(--text-tertiary)]">Backend</span>
          <span class="flex items-center gap-1.5 text-[10px] font-mono text-[#22d3ee]">
            <Zap color="#22d3ee" size={12} />
            WebGPU
          </span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono text-[var(--text-tertiary)]">Latencia</span>
          <span class="text-[10px] font-mono text-[#4ade80]">48ms</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono text-[var(--text-tertiary)]">Proveedor</span>
          <span class="flex items-center gap-1.5 text-[10px] font-mono text-[#4ade80]">
            <span class="h-2 w-2 rounded-full bg-[#4ade80] shadow-[0_0_6px_#4ade80]" />
            Groq
          </span>
        </div>
      </div>

      <button
        type="button"
        class="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border-color)] bg-[var(--bg-elevated)] py-2.5 text-[10px] font-mono text-[var(--text-secondary)] ring-1 ring-transparent transition-all hover:bg-[var(--bg-surface)] hover:ring-[var(--border-color)]"
      >
        <Brain color="var(--text-secondary)" size={14} />
        Modo Neurona
      </button>
    </aside>
  );
}
