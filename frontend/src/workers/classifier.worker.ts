import * as ort from "onnxruntime-web/webgpu";
import {
  MODEL_MAX_LEN,
  MODEL_ONNX_FILENAME,
  MODEL_VOCAB_FILENAME,
  ONNX_INPUT_NAME,
  ONNX_OUTPUT_NAMES,
} from "~/config/model";
import type { ClassificationResult } from "~/types/classifier";
import type { MainToWorker, WorkerToMain } from "~/types/worker";
import { postprocessOrtOutputs } from "~/utils/postprocess";
import { type Word2Idx, encodeText, padIds } from "~/utils/tokenizer";

const ORT_VERSION = "1.20.1";
ort.env.wasm.wasmPaths = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
ort.env.wasm.numThreads = 1;

let session: ort.InferenceSession | null = null;
let word2idx: Word2Idx | null = null;
let padId = 0;
/** Backend activo tras `init` (intento WebGPU primero, luego WASM). */
let activeOrtBackend: "webgpu" | "wasm" = "wasm";
let assetsBase = "";

function post(msg: WorkerToMain): void {
  self.postMessage(msg);
}

function resolveUrl(rel: string): string {
  const base = assetsBase.endsWith("/") ? assetsBase : `${assetsBase}/`;
  try {
    return new URL(rel, base).toString();
  } catch {
    return `${base}${rel.replace(/^\//, "")}`;
  }
}

function webGpuAvailable(): boolean {
  return typeof navigator !== "undefined" && "gpu" in navigator;
}

async function loadVocab(): Promise<void> {
  const url = resolveUrl(MODEL_VOCAB_FILENAME);
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`No se pudo cargar vocab.json (${res.status}) desde ${url}`);
  }
  const data = (await res.json()) as { word2idx: Record<string, number> };
  if (!data.word2idx || typeof data.word2idx !== "object") {
    throw new Error("vocab.json inválido: falta word2idx");
  }
  word2idx = data.word2idx;
  padId = word2idx["<pad>"] ?? 0;
}

async function createSessionWithFallback(onnxUrl: string): Promise<ort.InferenceSession> {
  if (webGpuAvailable()) {
    try {
      const webgpuSession = await ort.InferenceSession.create(onnxUrl, {
        executionProviders: ["webgpu", "wasm"],
        graphOptimizationLevel: "all",
      });
      activeOrtBackend = "webgpu";
      return webgpuSession;
    } catch (error) {
      console.warn("[synapse:classifier] WebGPU falló, usando WASM", error);
    }
  }

  activeOrtBackend = "wasm";
  return ort.InferenceSession.create(onnxUrl, {
    executionProviders: ["wasm"],
    graphOptimizationLevel: "all",
  });
}

async function handleInit(msg: Extract<MainToWorker, { type: "init" }>): Promise<void> {
  const t0 = performance.now();
  assetsBase = msg.assetsBase;
  await loadVocab();
  if (!word2idx) {
    throw new Error("word2idx no cargado");
  }
  const onnxUrl = msg.onnxUrl ?? resolveUrl(MODEL_ONNX_FILENAME);
  session = await createSessionWithFallback(onnxUrl);
  const loadMs = performance.now() - t0;
  post({ type: "ready", ortBackend: activeOrtBackend, loadMs });
}

function tensorFromInputIds(ids: number[]): ort.Tensor {
  const data = new BigInt64Array(ids.length);
  for (let i = 0; i < ids.length; i++) {
    data[i] = BigInt(ids[i]);
  }
  return new ort.Tensor("int64", data, [1, ids.length]);
}

async function handleClassify(msg: Extract<MainToWorker, { type: "classify" }>): Promise<void> {
  if (!session || !word2idx) {
    post({ type: "error", requestId: msg.requestId, message: "Clasificador no inicializado" });
    return;
  }
  const t0 = performance.now();
  const encoded = encodeText(msg.text, word2idx, MODEL_MAX_LEN);
  const padded = padIds(encoded, MODEL_MAX_LEN, padId);
  const inputTensor = tensorFromInputIds(padded);
  const feeds: Record<string, ort.Tensor> = {
    [ONNX_INPUT_NAME]: inputTensor,
  };
  const outputs = await session.run(feeds);
  const map: Record<string, Float32Array> = {};
  for (const name of ONNX_OUTPUT_NAMES) {
    const t = outputs[name];
    if (!t?.data) {
      throw new Error(`Salida ausente: ${name}`);
    }
    const raw = t.data as Float32Array | readonly number[] | Float64Array;
    map[name] = raw instanceof Float32Array ? raw : new Float32Array(raw);
  }
  const { metadata, headConfidences } = postprocessOrtOutputs(map);
  const inferenceMs = performance.now() - t0;
  const result: ClassificationResult = {
    metadata,
    inferenceMs,
    ortBackend: activeOrtBackend,
    headConfidences,
  };
  post({ type: "result", requestId: msg.requestId, result });
}

self.onmessage = async (ev: MessageEvent<MainToWorker>) => {
  const msg = ev.data;
  try {
    if (msg.type === "init") {
      await handleInit(msg);
      return;
    }
    if (msg.type === "classify") {
      await handleClassify(msg);
      return;
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    if (msg.type === "classify") {
      post({ type: "error", requestId: msg.requestId, message });
      return;
    }
    post({ type: "error", message });
  }
};
