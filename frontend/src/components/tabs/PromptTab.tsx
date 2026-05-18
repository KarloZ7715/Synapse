import { For, Show, createMemo } from "solid-js";
import type { ConversationStore } from "~/store/conversation";
import type { ClassificationMetadata } from "~/types/classifier";

const VAR_KEYS = ["LEVEL", "EMOTION", "URGENCY", "DOMAIN"] as const;
type VarKey = (typeof VAR_KEYS)[number];

const META_OF: Record<VarKey, keyof ClassificationMetadata> = {
  LEVEL: "nivel_tecnico",
  EMOTION: "emocion",
  URGENCY: "urgencia",
  DOMAIN: "dominio",
};

const EMOTION_MODIFIER: Record<string, string> = {
  frustracion: "Adopta un tono empático y tranquilizador. Simplifica los conceptos al máximo.",
  confusion: "Estructura la respuesta paso a paso, sin asumir conocimiento previo.",
  curiosidad: "Aprovecha el interés del usuario: añade ejemplos extra y enlaces de profundización.",
  ansiedad: "Empieza calmando: la respuesta es directa, sin alarmismo. No menciones consecuencias graves.",
  motivacion: "Refuerza el momentum: respuesta concisa con un siguiente paso accionable.",
  abrumado: "Reduce al mínimo. Una sola idea, sin opciones múltiples.",
  confiado: "Trato técnico directo. Cero introducción.",
  desesperado: "Solución primero, explicación después. Tono firme y empático.",
  neutral: "Tono profesional estándar.",
};

const LEVEL_MODIFIER: Record<string, string> = {
  principiante: "Evita jerga. Usa analogías. Termina con una pregunta exploratoria.",
  intermedio: "Asume sintaxis básica. Resalta el patrón conceptual.",
  avanzado: "Ve al grano con ejemplos optimizados. Permite referencias a internals.",
};

export function PromptTab(props: { convo: ConversationStore }) {
  const meta = () => props.convo.lastResult?.metadata ?? null;

  const varValue = (k: VarKey): string => {
    const m = meta();
    if (!m) return "—";
    return m[META_OF[k]].toString();
  };

  const renderedPrompt = createMemo(() => {
    const m = meta();
    const lvl = m ? m.nivel_tecnico : "{LEVEL}";
    const emo = m ? m.emocion : "{EMOTION}";
    const urg = m ? m.urgencia : "{URGENCY}";
    const dom = m ? m.dominio : "{DOMAIN}";
    return { lvl, emo, urg, dom };
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
              Salida del submodelo → contexto del LLM upstream
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
          {/* Left: Variable map */}
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

          {/* Center: Prompt template */}
          <section class="relative flex flex-col border-[#1a1a1a] bg-black lg:col-span-6 lg:border-l lg:border-r">
            <div class="flex items-center justify-between bg-surface-bright p-2 font-mono text-[11px] uppercase text-on-surface">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-base">terminal</span>
                SYSTEM_PROMPT_TEMPLATE
              </div>
              <div class="font-mono text-[10px] text-on-surface-variant">v1.0 · static</div>
            </div>
            <div class="flex-1 overflow-y-auto p-6 font-mono text-[13px] leading-relaxed">
              <div class="mb-4 text-outline">/* MASTER_INSTRUCTION_SET_V1 */</div>
              <p class="text-on-surface-variant">
                Eres un tutor de programación experto. El usuario tiene un nivel{" "}
                <PromptVar value={renderedPrompt().lvl} bound={!!meta()} />, se siente{" "}
                <PromptVar value={renderedPrompt().emo} bound={!!meta()} />, su consulta es de
                prioridad <PromptVar value={renderedPrompt().urg} bound={!!meta()} /> y el dominio
                relevante es <PromptVar value={renderedPrompt().dom} bound={!!meta()} />.
              </p>
              <p class="mt-4 text-on-surface-variant">
                Estructura tu respuesta:
                <br />
                1. Diagnóstico breve de la situación.
                <br />
                2. Solución técnica directa.
                <br />
                3. Explicación adaptada al nivel.
              </p>
              <div class="mt-4 text-outline">/* DYNAMIC_INJECTIONS_START */</div>
              <Show
                when={meta()}
                fallback={
                  <p class="mt-2 text-outline-variant">
                    [[INJECT_EMOTION_MODIFIER]]
                    <br />
                    [[INJECT_LEVEL_MODIFIER]]
                  </p>
                }
              >
                <p class="mt-2 text-on-surface">
                  {EMOTION_MODIFIER[renderedPrompt().emo] ?? "[modificador emoción n/a]"}
                </p>
                <p class="mt-2 text-on-surface">
                  {LEVEL_MODIFIER[renderedPrompt().lvl] ?? "[modificador nivel n/a]"}
                </p>
              </Show>
              <div class="mt-4 text-outline">/* DYNAMIC_INJECTIONS_END */</div>

              <Show when={props.convo.lastSubmittedText}>
                <div class="mt-6 border-t border-[#1a1a1a] pt-4">
                  <div class="text-outline">/* USER_QUERY */</div>
                  <p class="mt-2 whitespace-pre-wrap text-secondary-fixed">
                    {props.convo.lastSubmittedText}
                  </p>
                </div>
              </Show>
            </div>
            <div class="border-t border-[#1a1a1a] bg-surface-container-lowest p-2 text-right font-mono text-[10px] text-on-surface-variant">
              destino: backend /api/chat
            </div>
          </section>

          {/* Right: Dynamic replacements */}
          <section class="relative flex flex-col bg-[#0a0a0a] p-4 lg:col-span-3">
            <CornerCrosses />
            <div class="mb-4 flex items-center gap-2 bg-surface-bright p-2 font-mono text-[11px] uppercase text-on-surface">
              <span class="material-symbols-outlined text-base">swap_horiz</span>
              DYNAMIC_REPLACEMENTS
            </div>
            <div class="flex flex-1 flex-col gap-4 overflow-y-auto pr-2">
              <ConditionalCard
                condition="EMOTION"
                value={renderedPrompt().emo}
                rule={EMOTION_MODIFIER[renderedPrompt().emo] ?? "(sin regla específica)"}
                active={!!meta()}
                icon="psychology"
              />
              <ConditionalCard
                condition="LEVEL"
                value={renderedPrompt().lvl}
                rule={LEVEL_MODIFIER[renderedPrompt().lvl] ?? "(sin regla específica)"}
                active={!!meta()}
                icon="school"
              />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function PromptVar(props: { value: string; bound: boolean }) {
  return (
    <span
      class={`border px-1 ${props.bound ? "border-primary-container/40 bg-[#1a1a1a] text-primary-container" : "border-outline-variant bg-surface-variant text-on-surface-variant"}`}
    >
      {props.bound ? props.value.toUpperCase() : `{${props.value}}`}
    </span>
  );
}

function ConditionalCard(props: {
  condition: string;
  value: string;
  rule: string;
  active: boolean;
  icon: string;
}) {
  return (
    <div class="flex flex-col border border-outline-variant bg-black">
      <div class="flex items-center justify-between border-b border-outline-variant bg-[#1a1a1a] p-2">
        <span class="font-mono text-[10px] uppercase text-primary-container">
          CONDICIÓN: {props.condition}
        </span>
        <span class="material-symbols-outlined text-sm text-on-surface-variant">{props.icon}</span>
      </div>
      <div class="p-3">
        <div class="mb-2 inline-block border border-outline-variant bg-[#1a1a1a] px-2 py-0.5 font-mono text-[11px] uppercase text-on-surface">
          {props.active ? props.value : "—"}
        </div>
        <div class="flex items-center gap-2 text-outline-variant">
          <span class="material-symbols-outlined text-base">arrow_downward</span>
        </div>
        <div
          class={`border-l-2 py-1 pl-3 font-mono text-[11px] ${props.active ? "border-primary-container text-on-surface-variant" : "border-outline-variant text-on-surface-variant opacity-50"}`}
        >
          {props.rule}
        </div>
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
