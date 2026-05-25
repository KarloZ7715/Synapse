import { For, Show, createMemo } from "solid-js";
import { usePromptPreview } from "~/hooks/usePromptPreview";
import type { ConversationStore } from "~/store/conversation";
import type { ClassificationMetadata } from "~/types/classifier";

const VAR_KEYS = ["LEVEL", "EMOTION", "URGENCY", "DOMAIN", "CONFIDENCE"] as const;
type VarKey = (typeof VAR_KEYS)[number];

const META_OF: Record<VarKey, keyof ClassificationMetadata> = {
  LEVEL: "nivel_tecnico",
  EMOTION: "emocion",
  URGENCY: "urgencia",
  DOMAIN: "dominio",
  CONFIDENCE: "confianza",
};

export function PromptTab(props: { convo: ConversationStore }) {
  const result = () => props.convo.lastResult;
  const meta = () => result()?.metadata ?? null;
  const { systemPrompt } = usePromptPreview(result);

  const varValue = (k: VarKey): string => {
    const m = meta();
    if (!m) return "—";
    if (k === "CONFIDENCE") {
      return `${Math.round(m.confianza * 100)}%`;
    }
    return m[META_OF[k]].toString();
  };

  const headRows = createMemo(() => {
    const r = result();
    if (!r) return [];
    return [
      { key: "nivel_tecnico", label: "NIVEL", value: r.metadata.nivel_tecnico },
      { key: "urgencia", label: "URGENCIA", value: r.metadata.urgencia },
      { key: "emocion", label: "EMOCION", value: r.metadata.emocion },
      { key: "dominio", label: "DOMINIO", value: r.metadata.dominio },
    ] as const;
  });

  return (
    <div class="relative flex flex-1 overflow-y-auto bg-surface">
      <div class="mx-auto flex w-full max-w-[1400px] flex-col gap-margin-md p-margin-md md:p-margin-lg">
        <header class="flex items-end justify-between border-b border-outline-variant pb-margin-sm">
          <div>
            <h2 class="font-display text-[28px] font-bold uppercase tracking-tighter text-on-surface">
              PROMPT_ENGINEERING_HUD
            </h2>
            <p class="mt-2 font-mono text-[12px] uppercase text-on-surface-variant">
              System prompt ensamblado en backend (POST /api/prompt/preview)
            </p>
          </div>
          <div class="flex items-center gap-3 font-mono text-[11px]">
            <span class="border border-outline-variant bg-surface-container px-3 py-1 text-on-surface-variant">
              ESTADO:{" "}
              <span class={meta() ? "text-primary-container" : "text-on-surface-variant"}>
                {meta() ? "PROMPT LISTO" : "ESPERANDO CLASIFICACIÓN"}
              </span>
            </span>
          </div>
        </header>

        <div class="grid min-h-0 flex-1 grid-cols-1 border border-[#1a1a1a] lg:grid-cols-12">
          <section class="relative flex flex-col bg-[#0a0a0a] p-4 lg:col-span-3">
            <CornerCrosses />
            <div class="mb-4 flex items-center gap-2 bg-surface-bright p-2 font-mono text-[11px] uppercase text-on-surface">
              <span class="material-symbols-outlined text-base">account_tree</span>
              VARIABLE_MAP
            </div>
            <div class="flex flex-1 flex-col gap-4 overflow-y-auto pr-2">
              <For each={VAR_KEYS}>
                {(k) => (
                  <div class="border border-outline-variant bg-surface-container-lowest p-3 transition-colors hover:border-primary-container">
                    <div class="mb-2 flex items-center justify-between">
                      <span class="font-mono text-[12px] text-primary-container">{`{${k}}`}</span>
                      <span
                        class={`border px-1 font-mono text-[10px] ${meta() ? "border-outline-variant bg-[#1a1a1a] text-on-surface-variant" : "border-error/40 bg-error/10 text-error"}`}
                      >
                        {meta() ? "EN_VIVO" : "VACÍO"}
                      </span>
                    </div>
                    <div class="mb-3 truncate font-mono text-[13px] uppercase text-on-surface">
                      {varValue(k)}
                    </div>
                  </div>
                )}
              </For>
            </div>
          </section>

          <section class="relative flex flex-col border-[#1a1a1a] bg-black lg:col-span-6 lg:border-l lg:border-r">
            <div class="flex items-center justify-between bg-surface-bright p-2 font-mono text-[11px] uppercase text-on-surface">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-base">terminal</span>
                SYSTEM_PROMPT_LIVE
              </div>
              <div class="font-mono text-[10px] text-on-surface-variant">backend · v2</div>
            </div>
            <div class="flex-1 overflow-y-auto p-6 font-mono text-[12px] leading-relaxed">
              <Show
                when={!meta()}
                fallback={
                  <Show
                    when={!systemPrompt.loading}
                    fallback={
                      <p class="text-on-surface-variant animate-pulse">
                        Cargando system prompt desde backend…
                      </p>
                    }
                  >
                    <Show
                      when={!systemPrompt.error}
                      fallback={
                        <p class="text-error">
                          Error al cargar preview:{" "}
                          {systemPrompt.error instanceof Error
                            ? systemPrompt.error.message
                            : String(systemPrompt.error)}
                        </p>
                      }
                    >
                      <pre class="whitespace-pre-wrap text-on-surface-variant">
                        {systemPrompt() ?? ""}
                      </pre>
                    </Show>
                  </Show>
                }
              >
                <p class="text-outline-variant">
                  Clasifica una consulta para ver el system prompt exacto que recibe Groq.
                </p>
              </Show>

              <Show when={props.convo.lastSubmittedText}>
                <div class="mt-6 border-t border-[#1a1a1a] pt-4">
                  <div class="text-outline">/* USER_MESSAGE (rol user, no en system) */</div>
                  <p class="mt-2 whitespace-pre-wrap text-secondary-fixed">
                    {props.convo.lastSubmittedText}
                  </p>
                </div>
              </Show>
            </div>
            <div class="border-t border-[#1a1a1a] bg-surface-container-lowest p-2 text-right font-mono text-[10px] text-on-surface-variant">
              destino: POST /api/chat · historial: turnos previos completados
            </div>
          </section>

          <section class="relative flex flex-col bg-[#0a0a0a] p-4 lg:col-span-3">
            <CornerCrosses />
            <div class="mb-4 flex items-center gap-2 bg-surface-bright p-2 font-mono text-[11px] uppercase text-on-surface">
              <span class="material-symbols-outlined text-base">analytics</span>
              HEAD_CONFIDENCES
            </div>
            <div class="flex flex-1 flex-col gap-3 overflow-y-auto pr-2">
              <For each={headRows()}>
                {(row) => (
                  <HeadConfidenceCard
                    label={row.label}
                    value={row.value}
                    prob={result()?.headConfidences[row.key] ?? 0}
                    active={!!meta()}
                  />
                )}
              </For>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function HeadConfidenceCard(props: {
  label: string;
  value: string;
  prob: number;
  active: boolean;
}) {
  const pct = () => Math.round(props.prob * 100);
  const weak = () => props.prob < 0.5;

  return (
    <div class="flex flex-col border border-outline-variant bg-black p-3">
      <div class="mb-1 font-mono text-[10px] uppercase text-primary-container">{props.label}</div>
      <div class="font-mono text-[11px] uppercase text-on-surface">{props.active ? props.value : "—"}</div>
      <div
        class={`mt-2 font-mono text-[10px] ${weak() ? "text-error" : "text-on-surface-variant"}`}
      >
        softmax max: {props.active ? `${pct()}%` : "—"}
        {weak() && props.active ? " · cabeza debil" : ""}
      </div>
    </div>
  );
}

function CornerCrosses() {
  return (
    <>
      <div class="absolute left-1 top-1 font-mono text-xs text-primary-container/50">+</div>
      <div class="absolute right-1 top-1 font-mono text-xs text-primary-container/50">+</div>
      <div class="absolute bottom-1 left-1 font-mono text-xs text-primary-container/50">+</div>
      <div class="absolute bottom-1 right-1 font-mono text-xs text-primary-container/50">+</div>
    </>
  );
}
