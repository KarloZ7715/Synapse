import { For, Show, createSignal } from "solid-js";
import { MarkdownContent } from "~/components/markdown/MarkdownContent";
import { usePromptPreview } from "~/hooks/usePromptPreview";
import type { ConversationStore } from "~/store/conversation";
import type { ChatOptions } from "~/types/chat";

type ModelPreset = {
  id: string;
  name: string;
  provider: string;
  context: string;
  hint: string;
};

const PRESETS: ReadonlyArray<ModelPreset> = [
  {
    id: "llama-3.1-8b-instant",
    name: "Llama 3.1 8B",
    provider: "GROQ",
    context: "128K",
    hint: "Preset operativo",
  },
];

export function LLMTab(props: {
  convo: ConversationStore;
  onRun: (options: ChatOptions) => void | Promise<void>;
}) {
  const [activeId, setActiveId] = createSignal(PRESETS[0]?.id ?? "llama-3.1-8b-instant");
  const [temperature, setTemperature] = createSignal(0.7);
  const [topP, setTopP] = createSignal(0.9);
  const [maxTokens, setMaxTokens] = createSignal(2048);

  const lastResult = () => props.convo.lastResult;
  const meta = () => lastResult()?.metadata ?? null;
  const { systemPrompt } = usePromptPreview(lastResult);
  const llm = () => props.convo.llm;
  const canRun = () =>
    Boolean(meta() && props.convo.lastSubmittedText && llm().status !== "streaming");

  const handleRun = () => {
    void props.onRun({
      model_id: activeId(),
      temperature: temperature(),
      top_p: topP(),
      max_tokens: maxTokens(),
    });
  };

  return (
    <div class="relative flex flex-1 overflow-y-auto bg-surface">
      <div class="mx-auto flex w-full max-w-350 flex-col gap-margin-md p-margin-md md:p-margin-lg">
        <div class="flex items-center gap-4 border-2 border-primary-fixed/40 bg-primary-fixed/10 p-margin-sm">
          <span class="material-symbols-outlined text-2xl text-primary-fixed">hub</span>
          <div class="flex-1">
            <div class="font-display text-[16px] font-bold uppercase tracking-wider text-primary-fixed">
              BACKEND · /api/chat
            </div>
            <p class="font-mono text-[11px] uppercase text-on-surface-variant">
              Esta pestaña ya puede invocar el backend FastAPI y streamear la respuesta real del
              proveedor configurado.
            </p>
          </div>
          <span class="hidden border border-primary-fixed/40 bg-primary-fixed/10 px-3 py-1 font-mono text-[10px] uppercase text-primary-fixed md:inline-block">
            LIVE_BINDING
          </span>
        </div>

        <header class="flex items-end justify-between border-b border-outline-variant pb-margin-sm">
          <div>
            <h2 class="font-display text-[28px] font-bold uppercase tracking-tighter text-on-surface">
              Configuración Motor LLM
            </h2>
            <p class="mt-2 font-mono text-[12px] uppercase text-on-surface-variant">
              Configuración real del request hacia FastAPI + Groq
            </p>
          </div>
          <button
            type="button"
            class="border border-primary-fixed bg-primary-fixed px-4 py-2 font-mono text-[11px] uppercase text-on-primary-container transition-colors hover:bg-primary-container hover:text-on-primary-container disabled:cursor-not-allowed disabled:opacity-40"
            onClick={handleRun}
            disabled={!canRun()}
          >
            {llm().status === "streaming" ? "STREAMING..." : "EJECUTAR LLM"}
          </button>
        </header>

        <div class="grid grid-cols-1 gap-margin-md lg:grid-cols-12">
          {/* Left: Config */}
          <div class="flex flex-col gap-margin-md lg:col-span-8">
            {/* Model selection */}
            <section>
              <h3 class="mb-4 font-mono text-[12px] uppercase text-on-surface-variant">
                Selección de Modelo
              </h3>
              <div class="grid grid-cols-1 gap-2">
                <For each={PRESETS}>
                  {(p) => (
                    <button
                      type="button"
                      class="flex items-center justify-between p-4 text-left transition-colors"
                      classList={{
                        "border-2 border-primary-fixed bg-surface-container-highest":
                          activeId() === p.id,
                        "border border-outline-variant bg-surface-container-lowest hover:bg-surface-container-high":
                          activeId() !== p.id,
                      }}
                      onClick={() => setActiveId(p.id)}
                    >
                      <div>
                        <div
                          class="font-display text-[20px] font-bold"
                          classList={{
                            "text-primary-container": activeId() === p.id,
                            "text-on-surface": activeId() !== p.id,
                          }}
                        >
                          {p.name}
                        </div>
                        <div class="mt-1 font-mono text-[11px] uppercase text-on-surface-variant">
                          {p.provider} · CTX {p.context} · {p.hint}
                        </div>
                      </div>
                      <Show
                        when={activeId() === p.id}
                        fallback={
                          <span class="border border-outline-variant px-2 py-1 font-mono text-[10px] uppercase text-on-surface-variant">
                            Preset
                          </span>
                        }
                      >
                        <span class="bg-primary-container px-2 py-1 font-mono text-[10px] uppercase text-on-primary-container">
                          Activo (preview)
                        </span>
                      </Show>
                    </button>
                  )}
                </For>
              </div>
            </section>

            {/* Parameters */}
            <section class="border border-outline-variant bg-surface-container-lowest p-6">
              <div class="mb-6 flex items-end justify-between border-b border-outline-variant pb-2">
                <h3 class="font-mono text-[12px] uppercase text-on-surface-variant">
                  Parámetros de Inferencia
                </h3>
                <span class="font-mono text-[10px] uppercase text-primary-container">
                  MODO: LIVE
                </span>
              </div>
              <div class="space-y-6">
                <SliderRow
                  label="Temperature"
                  value={temperature()}
                  onChange={setTemperature}
                  min={0}
                  max={2}
                  step={0.1}
                  leftHint="PRECISO"
                  rightHint="CREATIVO"
                />
                <SliderRow
                  label="Top-P"
                  value={topP()}
                  onChange={setTopP}
                  min={0}
                  max={1}
                  step={0.05}
                />
                <SliderRow
                  label="Max Tokens"
                  value={maxTokens()}
                  onChange={setMaxTokens}
                  min={256}
                  max={8192}
                  step={256}
                  format="int"
                />
              </div>
            </section>

            {/* System prompt preview */}
            <section>
              <div class="mb-2 flex items-end justify-between">
                <h3 class="font-mono text-[12px] uppercase text-on-surface-variant">
                  Prompt de Sistema (ensamblado en backend)
                </h3>
                <div class="flex gap-2">
                  <Show when={meta()}>
                    <span class="border border-outline bg-surface-container-highest px-2 py-1 font-mono text-[10px] uppercase text-on-surface">
                      NIVEL: {meta()?.nivel_tecnico}
                    </span>
                    <span class="border border-outline bg-surface-container-highest px-2 py-1 font-mono text-[10px] uppercase text-on-surface">
                      EMOCIÓN: {meta()?.emocion}
                    </span>
                  </Show>
                  <Show when={!meta()}>
                    <span class="border border-outline-variant bg-surface px-2 py-1 font-mono text-[10px] uppercase text-on-surface-variant">
                      Sin clasificación aún
                    </span>
                  </Show>
                </div>
              </div>
              <div class="relative max-h-64 overflow-y-auto whitespace-pre-wrap border border-outline-variant bg-[#0a0a0a] p-4 font-mono text-[12px] leading-relaxed">
                <div class="absolute right-0 top-0 bg-outline-variant px-2 py-1 font-mono text-[10px] uppercase text-background">
                  READ_ONLY
                </div>
                <Show
                  when={meta()}
                  fallback={
                    <span class="text-on-surface-variant">
                      Clasifica una consulta para ver el system prompt que se envía a Groq.
                    </span>
                  }
                >
                  <Show
                    when={!systemPrompt.loading}
                    fallback={
                      <span class="text-on-surface-variant animate-pulse">Cargando preview…</span>
                    }
                  >
                    <Show
                      when={!systemPrompt.error}
                      fallback={
                        <span class="text-error">
                          {systemPrompt.error instanceof Error
                            ? systemPrompt.error.message
                            : String(systemPrompt.error)}
                        </span>
                      }
                    >
                      <span class="text-on-surface-variant">{systemPrompt()}</span>
                    </Show>
                  </Show>
                </Show>
              </div>
            </section>
          </div>

          {/* Right: Live output */}
          <aside class="flex flex-col gap-4 border border-outline-variant bg-surface-container-lowest p-margin-sm lg:col-span-4">
            <h3 class="flex items-center justify-between border-b border-outline-variant pb-2 font-mono text-[12px] uppercase">
              Salida del Modelo
              <span class="material-symbols-outlined text-sm text-primary-fixed">stream</span>
            </h3>
            <div class="border border-outline-variant bg-background p-3 font-mono text-[11px] uppercase text-on-surface-variant">
              STATUS: <span class="text-on-surface">{llm().status}</span>
              <Show when={props.convo.lastSubmittedText}>
                <div class="mt-2 truncate border-t border-outline-variant pt-2 text-[10px] text-secondary-fixed">
                  QUERY: {props.convo.lastSubmittedText}
                </div>
              </Show>
            </div>

            <div class="border border-outline-variant p-3">
              <div class="mb-1 font-mono text-[10px] uppercase text-on-surface-variant">
                Tokens de entrada
              </div>
              <div class="flex items-baseline justify-between font-display text-[20px] text-on-surface">
                <span>{llm().usage?.tokens_input ?? "—"}</span>
                <span class="font-mono text-[11px] text-on-surface-variant">prompt</span>
              </div>
            </div>
            <div class="border border-outline-variant p-3">
              <div class="mb-1 font-mono text-[10px] uppercase text-on-surface-variant">
                Tokens de salida
              </div>
              <div class="flex items-baseline gap-2 font-display text-[20px] text-on-surface">
                <span>{llm().usage?.tokens_output ?? "—"}</span>
                <span class="font-mono text-[11px] text-on-surface-variant">completion</span>
              </div>
            </div>

            <div class="border border-outline-variant p-3">
              <div class="mb-1 font-mono text-[10px] uppercase text-on-surface-variant">
                Latencia / proveedor
              </div>
              <div class="flex items-baseline justify-between font-display text-[20px] text-on-surface">
                <span>
                  {llm().usage?.latency_ms ?? "—"}
                  {llm().usage ? "ms" : ""}
                </span>
                <span class="font-mono text-[11px] text-on-surface-variant">
                  {llm().usage?.provider ?? activeId()}
                </span>
              </div>
            </div>

            <Show when={llm().error}>
              {(error) => (
                <div class="border border-error/40 bg-error/10 p-3 font-mono text-[11px] text-error">
                  {error()}
                </div>
              )}
            </Show>

            <div class="flex flex-1 flex-col">
              <div class="mb-2 border-b border-outline-variant pb-1 font-mono text-[10px] uppercase text-on-surface-variant">
                Stream de respuesta
              </div>
              <div class="flex-1 border border-outline-variant bg-background p-3">
                <Show
                  when={llm().response}
                  fallback={
                    <span class="font-mono text-[12px] text-on-surface-variant">
                      Ejecuta el LLM para ver aquí la respuesta generada por el backend.
                    </span>
                  }
                >
                  <MarkdownContent
                    source={llm().response}
                    streaming={llm().status === "streaming"}
                    class="text-[12px]"
                  />
                </Show>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function SliderRow(props: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  leftHint?: string;
  rightHint?: string;
  format?: "int";
}) {
  const display = () =>
    props.format === "int" ? Math.round(props.value).toString() : props.value.toFixed(2);
  return (
    <div>
      <div class="mb-2 flex items-center justify-between font-mono text-[12px] uppercase">
        <span class="text-on-surface">{props.label}</span>
        <span class="border border-primary-container bg-surface-container-highest px-2 py-0.5 text-primary-container">
          {display()}
        </span>
      </div>
      <input
        type="range"
        min={props.min}
        max={props.max}
        step={props.step}
        value={props.value}
        onInput={(e) => props.onChange(Number.parseFloat(e.currentTarget.value))}
        aria-label={props.label}
        title={props.label}
        class="w-full accent-primary-container"
      />
      <Show when={props.leftHint || props.rightHint}>
        <div class="mt-1 flex justify-between font-mono text-[10px] uppercase text-on-surface-variant">
          <span>{props.leftHint ?? ""}</span>
          <span>{props.rightHint ?? ""}</span>
        </div>
      </Show>
    </div>
  );
}
