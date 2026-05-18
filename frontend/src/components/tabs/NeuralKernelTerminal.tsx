import { For, Show, createMemo, createSignal, onCleanup, onMount } from "solid-js";
import type { ConversationStore } from "~/store/conversation";
import type { ClassificationResult, ClassifierStatus, HeadKey } from "~/types/classifier";

type Classifier = {
  status: () => ClassifierStatus;
  result: () => ClassificationResult | null;
  loadMs: () => number | null;
  error: () => string | null;
};

const HEAD_LABELS: Record<HeadKey, string> = {
  nivel_tecnico: "NIVEL",
  urgencia: "URGENCIA",
  emocion: "EMOCIÓN",
  dominio: "DOMINIO",
};

const FILE_TREE = [
  {
    name: "neural_engine/",
    open: true,
    files: ["synapse_textcnn.onnx", "vocab.json", "training_labels.py"],
  },
  { name: "workers/", open: false, files: ["classifier.worker.ts"] },
  { name: "ui/", open: false, files: ["AppLayout.tsx", "PipelineNav.tsx"] },
];

function nowStamp() {
  const d = new Date();
  return d.toTimeString().slice(0, 8) + "." + d.getMilliseconds().toString().padStart(3, "0");
}

export function NeuralKernelTerminal(props: {
  classifier: Classifier;
  convo: ConversationStore;
  onClose: () => void;
}) {
  // Live wall-clock so the terminal feels alive
  const [tick, setTick] = createSignal(nowStamp());
  onMount(() => {
    const id = window.setInterval(() => setTick(nowStamp()), 1000);
    onCleanup(() => window.clearInterval(id));
  });

  const logs = createMemo<Array<{ stamp: string; kind: "info" | "ok" | "warn" | "err"; text: string }>>(() => {
    const out: Array<{ stamp: string; kind: "info" | "ok" | "warn" | "err"; text: string }> = [];
    out.push({ stamp: tick(), kind: "ok", text: "KERNEL_BOOT: secuencia primaria · OK" });
    if (props.classifier.loadMs() !== null) {
      out.push({
        stamp: tick(),
        kind: "ok",
        text: `MODEL_LOAD: synapse_textcnn.onnx (${Math.round(props.classifier.loadMs() ?? 0)}ms)`,
      });
    }
    if (props.classifier.status() === "loading_model") {
      out.push({ stamp: tick(), kind: "info", text: "NEURAL_PROCESS: cargando pesos..." });
    }
    if (props.classifier.status() === "classifying") {
      out.push({
        stamp: tick(),
        kind: "info",
        text: "NEURAL_PROCESS: inferencia en curso...",
      });
    }
    const r = props.classifier.result() ?? props.convo.lastResult;
    if (r) {
      out.push({
        stamp: tick(),
        kind: "ok",
        text: `INFERENCE_DONE: ${Math.round(r.inferenceMs)}ms · ${r.ortBackend}`,
      });
      out.push({
        stamp: tick(),
        kind: "info",
        text: `SOFTMAX_HEADS: [${Object.values(r.headConfidences)
          .map((v) => v.toFixed(2))
          .join(", ")}]`,
      });
    }
    if (props.classifier.error()) {
      out.push({ stamp: tick(), kind: "err", text: `SYS_ERR: ${props.classifier.error()}` });
    }
    return out;
  });

  const result = () => props.classifier.result() ?? props.convo.lastResult;

  return (
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-surface-container-lowest/80 backdrop-blur-md"
      onClick={(e) => {
        if (e.currentTarget === e.target) props.onClose();
      }}
    >
      <div class="brutal-border flex h-[min(85vh,720px)] w-[min(1200px,95vw)] flex-col bg-surface-container-lowest">
        {/* Title bar */}
        <div class="flex items-center justify-between border-b border-outline-variant bg-surface-variant px-4 py-2">
          <div class="flex items-center gap-2 font-mono text-[12px] font-bold uppercase tracking-widest text-on-surface">
            <span class="material-symbols-outlined text-base">terminal</span>
            Neural Kernel Terminal
          </div>
          <div class="hidden gap-4 font-mono text-[10px] uppercase text-on-surface-variant md:flex">
            <span>WALL: {tick()}</span>
            <span>
              STATUS:{" "}
              <span
                class={
                  props.classifier.status() === "error"
                    ? "text-error"
                    : "text-primary-container"
                }
              >
                {props.classifier.status().toUpperCase()}
              </span>
            </span>
          </div>
          <button
            type="button"
            onClick={props.onClose}
            class="text-on-surface-variant transition-colors hover:text-error"
            aria-label="Cerrar terminal"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="flex flex-1 gap-px overflow-hidden bg-outline-variant p-px">
          {/* Left: File tree */}
          <section class="hidden w-64 shrink-0 flex-col bg-surface-container-lowest md:flex">
            <div class="border-b border-outline-variant bg-surface-variant px-2 py-1 font-mono text-[10px] uppercase text-on-surface">
              ÁRBOL DEL NÚCLEO
            </div>
            <div class="flex-1 overflow-y-auto p-2 font-mono text-[11px] text-on-surface-variant">
              <div class="flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px] text-primary-container">
                  folder_open
                </span>
                <span class="text-on-surface">root/</span>
              </div>
              <div class="ml-3 border-l border-outline-variant pl-2">
                <For each={FILE_TREE}>
                  {(node) => (
                    <div class="mt-1">
                      <div class="flex items-center gap-1">
                        <span
                          class={`material-symbols-outlined text-[14px] ${node.open ? "text-primary-container" : "text-outline"}`}
                        >
                          {node.open ? "folder_open" : "folder"}
                        </span>
                        <span class={node.open ? "text-primary-container" : "text-on-surface"}>
                          {node.name}
                        </span>
                      </div>
                      <Show when={node.open}>
                        <div class="ml-3 mt-1 space-y-0.5 border-l border-outline-variant pl-2">
                          <For each={node.files}>
                            {(f) => <div class="text-on-surface-variant">{f}</div>}
                          </For>
                        </div>
                      </Show>
                    </div>
                  )}
                </For>
              </div>
            </div>
          </section>

          {/* Center: Console */}
          <section class="flex flex-1 flex-col bg-black">
            <div class="flex items-center justify-between border-b border-outline-variant bg-surface-variant px-2 py-1 font-mono text-[10px] uppercase text-on-surface">
              <span>CONSOLA DEL SISTEMA</span>
              <span class="material-symbols-outlined text-base text-outline">terminal</span>
            </div>
            <div class="flex flex-1 flex-col overflow-y-auto p-4 font-mono text-[12px] text-on-surface-variant">
              <For each={logs()}>
                {(line) => (
                  <div class="flex gap-2">
                    <span class="text-secondary-fixed">[{line.stamp}]</span>
                    <span
                      class={
                        line.kind === "ok"
                          ? "text-primary-fixed-dim"
                          : line.kind === "err"
                            ? "text-error"
                            : line.kind === "warn"
                              ? "text-tertiary-fixed-dim"
                              : "text-on-surface"
                      }
                    >
                      {line.text}
                    </span>
                  </div>
                )}
              </For>
              <Show when={logs().length === 0}>
                <p class="text-on-surface-variant">// Sin eventos aún. Esperando boot...</p>
              </Show>
              <div class="mt-4 flex items-center gap-2">
                <span class="text-primary-container">&gt;_</span>
                <span class="animate-blink text-primary-container">█</span>
              </div>
            </div>
          </section>

          {/* Right: Hardware HUD */}
          <section class="hidden w-80 shrink-0 flex-col bg-surface-container-lowest md:flex">
            <div class="border-b border-outline-variant bg-surface-variant px-2 py-1 font-mono text-[10px] uppercase text-on-surface">
              ESTADO DEL CLASIFICADOR
            </div>
            <div class="flex-1 space-y-6 overflow-y-auto p-4">
              {/* Status */}
              <div class="space-y-2">
                <div class="flex justify-between font-mono text-[11px] uppercase">
                  <span class="text-on-surface-variant">Backend ONNX</span>
                  <span class="text-primary-container">
                    {result()?.ortBackend.toUpperCase() ?? "—"}
                  </span>
                </div>
                <div class="flex justify-between font-mono text-[11px] uppercase">
                  <span class="text-on-surface-variant">Carga modelo</span>
                  <span class="text-on-surface">
                    {props.classifier.loadMs() !== null
                      ? `${Math.round(props.classifier.loadMs() ?? 0)}ms`
                      : "—"}
                  </span>
                </div>
                <div class="flex justify-between font-mono text-[11px] uppercase">
                  <span class="text-on-surface-variant">Inferencia</span>
                  <span class="text-on-surface">
                    {result() ? `${Math.round(result()?.inferenceMs ?? 0)}ms` : "—"}
                  </span>
                </div>
              </div>

              {/* Head confidences as VRAM-like blocks */}
              <div class="space-y-2">
                <div class="flex justify-between font-mono text-[11px] uppercase text-on-surface-variant">
                  <span>Confianzas por cabeza</span>
                  <span class="text-primary-container">
                    {result()
                      ? `${Math.round((result()?.metadata.confianza ?? 0) * 100)}%`
                      : "—"}
                  </span>
                </div>
                <For each={Object.keys(HEAD_LABELS) as HeadKey[]}>
                  {(k) => {
                    const pct = () => Math.round((result()?.headConfidences[k] ?? 0) * 100);
                    return (
                      <div>
                        <div class="flex justify-between font-mono text-[10px] uppercase text-on-surface-variant">
                          <span>{HEAD_LABELS[k]}</span>
                          <span class="text-on-surface">{pct()}%</span>
                        </div>
                        <div class="h-2 w-full bg-surface-container-highest">
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

              {/* Last submitted */}
              <div class="space-y-1">
                <div class="font-mono text-[11px] uppercase text-on-surface-variant">
                  Última consulta
                </div>
                <div class="border border-outline-variant bg-surface-container-lowest p-2 font-mono text-[11px] text-on-surface">
                  {props.convo.lastSubmittedText ?? "—"}
                </div>
              </div>

              {/* Actions */}
              <div class="space-y-2">
                <button
                  type="button"
                  class="w-full border border-on-surface bg-on-surface px-2 py-2 font-mono text-[11px] uppercase text-background transition-colors hover:border-primary-container hover:bg-primary-container"
                  onClick={() => window.location.reload()}
                >
                  PURGAR CACHÉ
                </button>
                <button
                  type="button"
                  class="w-full border border-error bg-transparent px-2 py-2 font-mono text-[11px] uppercase text-error transition-colors hover:bg-error hover:text-on-error"
                  onClick={() => window.location.reload()}
                >
                  PARADA DE EMERGENCIA
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
