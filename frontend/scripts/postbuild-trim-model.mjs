#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.join(__dirname, "..");
const configuredOnnxUrl = process.env.VITE_ONNX_MODEL_URL?.trim();
const distOnnxPath = path.join(frontendRoot, "dist", "models", "synapse_textcnn.onnx");

if (!configuredOnnxUrl) {
  console.log("[postbuild:model] VITE_ONNX_MODEL_URL no configurada; se conserva el ONNX en dist.");
  process.exit(0);
}

if (!fs.existsSync(distOnnxPath)) {
  console.log("[postbuild:model] No hay ONNX en dist para eliminar.");
  process.exit(0);
}

fs.rmSync(distOnnxPath);
console.log(`[postbuild:model] ONNX eliminado de dist; se usará ${configuredOnnxUrl}`);