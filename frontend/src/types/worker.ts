import type { ClassificationResult } from "./classifier";

export type WorkerToMain =
  | { type: "ready"; ortBackend: "webgpu" | "wasm"; loadMs: number }
  | { type: "result"; requestId: string; result: ClassificationResult }
  | { type: "error"; requestId?: string; message: string };

export type MainToWorker =
  | { type: "init"; assetsBase: string; onnxUrl?: string }
  | { type: "classify"; requestId: string; text: string };
