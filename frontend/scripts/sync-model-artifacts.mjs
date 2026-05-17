#!/usr/bin/env node
/**
 * Copia artefactos de inferencia al frontend para desarrollo y E2E.
 * Origen por defecto: corrida local en `neural_network/notebook/data/`.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.join(__dirname, "..");
const repoRoot = path.join(frontendRoot, "..");

const defaultOnnx = path.join(
  repoRoot,
  "neural_network/notebook/data/checkpoints/textcnn_run/synapse_textcnn.onnx",
);
const defaultVocab = path.join(repoRoot, "neural_network/notebook/data/artifacts/vocab.json");

const destDir = path.join(frontendRoot, "public", "models");
const destOnnx = path.join(destDir, "synapse_textcnn.onnx");
const destVocab = path.join(destDir, "vocab.json");

/**
 * @param {string} src
 * @param {string} dest
 * @param {string} label
 */
function copyIfExists(src, dest, label) {
  if (!fs.existsSync(src)) {
    console.error(`[sync:model] No existe ${label}: ${src}`);
    process.exit(1);
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log(`[sync:model] ${label}: ${src} -> ${dest}`);
}

copyIfExists(defaultOnnx, destOnnx, "ONNX");
copyIfExists(defaultVocab, destVocab, "vocab.json");
console.log("[sync:model] Listo.");
