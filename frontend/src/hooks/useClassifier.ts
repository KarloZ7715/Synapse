import { createSignal, onCleanup, onMount } from "solid-js";
import { MODEL_ASSETS_SUBPATH } from "~/config/model";
import type { ClassificationResult, ClassifierStatus } from "~/types/classifier";
import type { MainToWorker, WorkerToMain } from "~/types/worker";

function makeRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function modelsBaseUrl(): string {
  return new URL(MODEL_ASSETS_SUBPATH, `${window.location.origin}${import.meta.env.BASE_URL}`).href;
}

function onnxModelUrl(): string | undefined {
  const configured = import.meta.env.VITE_ONNX_MODEL_URL?.trim();
  return configured ? configured : undefined;
}

export function useClassifier() {
  const [status, setStatus] = createSignal<ClassifierStatus>("idle");
  const [result, setResult] = createSignal<ClassificationResult | null>(null);
  const [error, setError] = createSignal<string | null>(null);
  const [loadMs, setLoadMs] = createSignal<number | null>(null);
  const [ortBackend, setOrtBackend] = createSignal<"webgpu" | "wasm" | null>(null);

  let worker: Worker | undefined;
  const pending = new Map<
    string,
    { resolve: (r: ClassificationResult) => void; reject: (e: Error) => void }
  >();

  onMount(() => {
    worker = new Worker(new URL("../workers/classifier.worker.ts", import.meta.url), {
      type: "module",
    });

    worker.onmessage = (ev: MessageEvent<WorkerToMain>) => {
      const msg = ev.data;
      if (msg.type === "ready") {
        setStatus("ready");
        setLoadMs(msg.loadMs);
        setOrtBackend(msg.ortBackend);
        setError(null);
        return;
      }
      if (msg.type === "error") {
        if (msg.requestId && pending.has(msg.requestId)) {
          pending.get(msg.requestId)?.reject(new Error(msg.message));
          pending.delete(msg.requestId);
          setError(msg.message);
          setStatus("ready");
          return;
        }
        setStatus("error");
        setError(msg.message);
        return;
      }
      if (msg.type === "result") {
        setResult(msg.result);
        setStatus("ready");
        setError(null);
        const p = pending.get(msg.requestId);
        if (p) {
          p.resolve(msg.result);
          pending.delete(msg.requestId);
        }
      }
    };

    setStatus("loading_model");
    const onnxUrl = onnxModelUrl();
    const initMessage: MainToWorker = onnxUrl
      ? { type: "init", assetsBase: modelsBaseUrl(), onnxUrl }
      : { type: "init", assetsBase: modelsBaseUrl() };
    worker.postMessage(initMessage);
  });

  onCleanup(() => {
    worker?.terminate();
    worker = undefined;
  });

  async function classify(text: string): Promise<ClassificationResult> {
    const w = worker;
    if (!w) {
      throw new Error("Worker no inicializado");
    }
    const s = status();
    if (s !== "ready") {
      if (s === "loading_model") {
        throw new Error("Modelo aún cargando");
      }
      if (s === "classifying") {
        throw new Error("Ya hay una clasificación en curso");
      }
      throw new Error(error() ?? "Clasificador no disponible");
    }
    const id = makeRequestId();
    setResult(null);
    setError(null);
    setStatus("classifying");
    return new Promise<ClassificationResult>((resolve, reject) => {
      pending.set(id, { resolve, reject });
      w.postMessage({ type: "classify", requestId: id, text } satisfies MainToWorker);
    });
  }

  return {
    status,
    error,
    result,
    loadMs,
    ortBackend,
    classify,
  } as const;
}
