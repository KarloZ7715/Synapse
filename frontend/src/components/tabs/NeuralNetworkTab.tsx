import { For, Show, createMemo } from "solid-js";
import type { ConversationStore } from "~/store/conversation";
import type { ClassificationResult, ClassifierStatus } from "~/types/classifier";

type Classifier = {
  status: () => ClassifierStatus;
  result: () => ClassificationResult | null;
  loadMs: () => number | null;
};

const OUTPUT_HEADS = [
  { key: "nivel_tecnico", label: "NIVEL" },
  { key: "urgencia", label: "URGENCIA" },
  { key: "emocion", label: "EMOCIÓN" },
  { key: "dominio", label: "DOMINIO" },
] as const;

export function NeuralNetworkTab(props: { classifier: Classifier; convo: ConversationStore }) {
  const result = () => props.convo.lastResult;
  const conf = (key: (typeof OUTPUT_HEADS)[number]["key"]) =>
    result()?.headConfidences[key] ?? 0;

  const statusBadge = createMemo(() => {
    const s = props.classifier.status();
    if (s === "ready") return { text: "ACTIVO", cls: "bg-primary-container text-on-primary-container" };
    if (s === "classifying") return { text: "INFERENCIA", cls: "bg-secondary-container text-on-secondary-container" };
    if (s === "loading_model") return { text: "CARGANDO", cls: "bg-surface-variant text-on-surface" };
    if (s === "error") return { text: "ERROR", cls: "bg-error text-on-error" };
    return { text: "IDLE", cls: "bg-surface-variant text-on-surface-variant" };
  });

  return (
    <div class="relative flex flex-1 overflow-y-auto bg-surface">
      <div class="mx-auto flex w-full max-w-[1400px] flex-col gap-margin-md p-margin-md md:p-margin-lg">
        {/* Header banner */}
        <div class="flex items-center justify-between border border-outline-variant bg-surface-container-low p-4">
          <div class="flex items-center gap-4">
            <span class="material-symbols-outlined text-[32px] text-primary-container">
              account_tree
            </span>
            <div>
              <h2 class="font-display text-[24px] font-bold uppercase tracking-tight text-primary-container">
                NEURAL_NETWORK_DEEP_DIVE
              </h2>
              <p class="font-mono text-[11px] uppercase text-on-surface-variant">
                Submodelo TextCNN local · 4 cabezas de clasificación
              </p>
            </div>
          </div>
          <div class={`px-3 py-1 font-mono text-[11px] uppercase font-bold ${statusBadge().cls}`}>
            ESTADO: {statusBadge().text}
          </div>
        </div>

        <div class="grid grid-cols-1 gap-margin-md xl:grid-cols-12">
          {/* Architecture viz */}
          <section class="flex min-h-[500px] flex-col border border-outline-variant bg-surface-container-lowest xl:col-span-8">
            <div class="flex items-center justify-between border-b border-outline-variant bg-surface-container-high p-2">
              <span class="font-mono text-[11px] uppercase text-on-background">
                Arquitectura de capas
              </span>
              <span class="font-mono text-[10px] text-primary-container">VIEW: LIVE</span>
            </div>

            <div class="relative flex flex-1 items-center justify-between p-8">
              {/* Input nodes */}
              <div class="z-10 flex flex-col gap-3">
                <For each={[1, 2, 3]}>
                  {(i) => (
                    <div
                      class="relative flex h-14 w-14 items-center justify-center border bg-surface font-mono text-[10px]"
                      classList={{
                        "border-primary-container text-primary-container": i === 2,
                        "border-outline-variant text-on-surface-variant": i !== 2,
                      }}
                    >
                      IN_{i}
                      <div
                        class="absolute -right-12 top-1/2 h-px w-12"
                        classList={{
                          "bg-primary-container": i === 2,
                          "bg-outline-variant": i !== 2,
                        }}
                      />
                    </div>
                  )}
                </For>
              </div>

              {/* Hidden layers (decorative) */}
              <div class="z-10 flex gap-8">
                <div class="flex flex-col gap-2">
                  <For each={[1, 2, 3, 4]}>
                    {(i) => (
                      <div
                        class="h-8 w-8 rounded-full border bg-surface-variant"
                        classList={{
                          "border-primary-container": i === 2,
                          "border-outline-variant": i !== 2,
                        }}
                      >
                        <Show when={i === 2}>
                          <div class="h-full w-full animate-pulse rounded-full bg-primary-container opacity-30" />
                        </Show>
                      </div>
                    )}
                  </For>
                </div>
                <div class="flex flex-col justify-center gap-2">
                  <For each={[1, 2, 3]}>
                    {(i) => (
                      <div
                        class="h-8 w-8 rounded-full border bg-surface-variant"
                        classList={{
                          "border-primary-container shadow-[0_0_10px_rgba(57,255,20,0.5)]": i === 2,
                          "border-outline-variant": i !== 2,
                        }}
                      />
                    )}
                  </For>
                </div>
              </div>

              {/* Output heads — real confidences */}
              <div class="z-10 flex flex-col gap-3">
                <For each={OUTPUT_HEADS}>
                  {(head) => {
                    const pct = () => Math.round(conf(head.key) * 100);
                    const has = () => !!result();
                    return (
                      <div
                        class="relative border bg-surface p-3 min-w-[140px]"
                        classList={{
                          "border-primary-container": has(),
                          "border-outline-variant": !has(),
                        }}
                      >
                        <div
                          class="absolute -left-12 top-1/2 h-px w-12"
                          classList={{
                            "bg-primary-container": has(),
                            "bg-outline-variant": !has(),
                          }}
                        />
                        <span
                          class="block font-mono text-[10px] uppercase"
                          classList={{
                            "text-primary-container": has(),
                            "text-on-surface-variant": !has(),
                          }}
                        >
                          {head.label}
                        </span>
                        <div class="mt-1 flex items-center justify-between gap-2 font-mono text-[10px]">
                          <span class="text-on-surface-variant">{pct()}%</span>
                          <Show when={has()}>
                            <span class="uppercase text-on-surface">
                              {result()?.metadata[head.key]}
                            </span>
                          </Show>
                        </div>
                        <div class="mt-1 h-2 w-full bg-surface-container-highest">
                          <div
                            class="h-full bg-primary-container transition-all"
                            style={{ width: `${pct()}%` }}
                          />
                        </div>
                      </div>
                    );
                  }}
                </For>
              </div>

              {/* Corner crosshairs */}
              <div class="absolute left-2 top-2 font-mono text-primary-container">+</div>
              <div class="absolute right-2 top-2 font-mono text-primary-container">+</div>
              <div class="absolute bottom-2 left-2 font-mono text-primary-container">+</div>
              <div class="absolute bottom-2 right-2 font-mono text-primary-container">+</div>
            </div>
          </section>

          {/* Side HUD */}
          <section class="flex flex-col border border-outline-variant bg-surface-container-lowest xl:col-span-4">
            <div class="flex items-center justify-between border-b border-outline-variant bg-surface-container-high p-2">
              <span class="font-mono text-[11px] uppercase text-on-background">DIAGNÓSTICO_HUD</span>
              <span class="material-symbols-outlined text-sm text-on-surface-variant">radar</span>
            </div>
            <div class="flex flex-1 flex-col gap-margin-md p-margin-md">
              <FocusMetric
                label="Confianza global"
                value={
                  result()
                    ? `${Math.round((result() as ClassificationResult).metadata.confianza * 100)}%`
                    : "—"
                }
                accent="primary"
                pct={result() ? (result() as ClassificationResult).metadata.confianza * 100 : 0}
              />
              <FocusMetric
                label="Latencia de inferencia"
                value={result() ? `${Math.round((result() as ClassificationResult).inferenceMs)}ms` : "—"}
                subtitle="Óptimo < 50ms"
              />
              <FocusMetric
                label="Backend ONNX"
                value={result()?.ortBackend.toUpperCase() ?? "—"}
                subtitle="WebGPU → WASM fallback"
              />
              <FocusMetric
                label="Carga inicial"
                value={
                  props.classifier.loadMs() !== null
                    ? `${Math.round(props.classifier.loadMs() ?? 0)}ms`
                    : "—"
                }
              />
            </div>
          </section>

          {/* Tensor flow logs */}
          <section class="flex h-[260px] flex-col border border-outline-variant bg-surface-container-lowest xl:col-span-12">
            <div class="flex items-center justify-between border-b border-outline-variant bg-surface-container-high p-2">
              <span class="font-mono text-[11px] uppercase text-on-background">
                Flujo Tensorial (decorativo)
              </span>
              <div
                class="h-2 w-2 rounded-full"
                classList={{
                  "bg-primary-container animate-pulse": props.classifier.status() === "classifying",
                  "bg-primary-container": props.classifier.status() === "ready",
                  "bg-outline": props.classifier.status() === "idle",
                  "bg-secondary-container animate-pulse": props.classifier.status() === "loading_model",
                  "bg-error animate-pulse": props.classifier.status() === "error",
                }}
              />
            </div>
            <div class="relative flex flex-1 flex-col justify-end overflow-hidden bg-black p-4 font-mono text-[11px] text-on-surface-variant">
              <div class="opacity-30">&gt; INPUT_IDS: int64[1, 160] tensorizado</div>
              <div class="opacity-50">&gt; EMBEDDING_LOOKUP: V × D, V=vocab</div>
              <div class="opacity-60">&gt; CONV1D_KERNELS: [3, 4, 5] × n_filters · ReLU</div>
              <div class="opacity-70">&gt; MAX_POOL_OVER_TIME · concat heads</div>
              <Show when={result()}>
                <div class="text-primary-container">
                  &gt; SOFTMAX_HEADS · 4 salidas · argmax → metadata
                </div>
                <div class="text-secondary-container">
                  &gt; INFERENCE_DONE in {Math.round((result() as ClassificationResult).inferenceMs)}ms ({result()?.ortBackend})
                </div>
              </Show>
              <Show when={props.classifier.status() === "classifying"}>
                <div class="text-secondary-container animate-pulse">&gt; INFERENCE_IN_PROGRESS...</div>
              </Show>
              <Show when={!result() && props.classifier.status() === "ready"}>
                <div class="text-on-surface-variant">&gt; AWAITING_NEXT_BATCH</div>
              </Show>
              <div class="pointer-events-none absolute left-0 right-0 top-0 h-12 bg-gradient-to-b from-black to-transparent" />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function FocusMetric(props: {
  label: string;
  value: string;
  subtitle?: string;
  accent?: "primary";
  pct?: number;
}) {
  const valueCls = props.accent === "primary" ? "text-primary-container" : "text-on-background";
  return (
    <div class="relative border border-outline-variant bg-surface p-4">
      <span class="absolute -top-3 left-2 bg-surface px-1 font-mono text-[10px] uppercase text-on-surface-variant">
        {props.label}
      </span>
      <div class={`mt-1 font-display text-[28px] font-bold ${valueCls}`}>{props.value}</div>
      <Show when={props.subtitle}>
        <div class="mt-1 font-mono text-[10px] text-on-surface-variant">{props.subtitle}</div>
      </Show>
      <Show when={props.pct !== undefined && props.accent === "primary"}>
        <div class="mt-2 h-1 w-full bg-surface-container-highest">
          <div
            class="h-full bg-primary-container transition-all"
            style={{ width: `${props.pct ?? 0}%` }}
          />
        </div>
      </Show>
    </div>
  );
}
