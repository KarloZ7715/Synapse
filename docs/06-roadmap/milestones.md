# Milestones — Synapse (Estado Actual)

Referencia operativa alineada con `docs/06-roadmap/roadmap.md`.

Última actualización: 17 mayo 2026.

---

## Snapshot de Avance


| Bloque                                     | Estado                                 |
| ------------------------------------------ | -------------------------------------- |
| Dataset base (F1-F2)                       | Completado                             |
| Etiquetado LLM (F3)                        | Completado                             |
| Augmentation + dataset final ~10k-12k (F4) | Completado                             |
| Entrenamiento TextCNN (F5)                 | Completado                             |
| Exportación ONNX (F6)                      | Completado                             |
| App (F7-F10)                               | En curso (F7 listo; F8–F10 pendientes) |
| Testing + Deploy (F11-F12)                 | Pendiente                              |


---

## Milestone M1 — Dataset Curado (Completado)

Ventana: 14 mayo 2026  
Estado: Completado

Incluye:

- GoEmotions ES descargado y mapeado.
- Stack Overflow ES reequilibrado con `body` completo.
- Etiquetado consolidado en `dataset/processed/labeled.json`.

DoD:

- 250/250 filas válidas.
- Cuerpos no vacíos.
- Gate de calidad F3 aprobado.

---

## Milestone M2 — Dataset Final Entrenable (Completado)

Ventana objetivo: 15-17 mayo 2026  
Estado: Completado

Incluye:

- Ejecutar `build_final_dataset.py` (meta ~4.000–6.000 filas; default 5.000), deduplicación por texto normalizado.
- Muestreo por `emocion` con mínimos por clase; opcional augmentation SO ligera si falta volumen.
- Split reproducible train/val/test (70/15/15), integrado en el mismo script salvo `--no-split`.

DoD:

- `dataset/final/dataset.json`, `quality_report.json`, `train.json`, `val.json`, `test.json`, `split_meta.json`.
- Conteo total en rango acordado y `quality_report.json` con `balance_mvp.passes: true` (MVP); `stretch_goals` opcional para ≥12 % `avanzado` vía LLM o más SO.

---

## Milestone M3 — Modelo ONNX Validado

Ventana objetivo: 18-20 mayo 2026  
Estado: **Completado**

### Parte 1: Entrenamiento TextCNN (COMPLETADA)

Incluye:

- TextCNN multi-cabeza entrenado en `neural_network/notebook/synapse_textcnn_training.ipynb`.
- Artefactos en `neural_network/notebook/data/checkpoints/textcnn_run/`:
  - Checkpoint óptimo: `best.pt`
  - Métricas entrenamiento: `history.json` (por época), `test_metrics.json`, `val_source_metrics.json`
  - Gate de calidad: `dod_report.json` con `all_pass: true`
  - Calibración post-hoc: `posthoc_calibration.json`, `majority_baselines.json`
  - Configuración: `run_config.json`
- Scripts: `neural_network/scripts/build_vocab.py`, `train_textcnn.py`, `diagnose_textcnn_run.py`

DoD Parte 1:

- Checkpoint final con métricas completas (`history.json`, `test_metrics.json`).
- Gate de cierre: `dod_report.json` con `all_pass: true` ✓
- Checkpoint exportable a ONNX ✓

### Parte 2: Exportación ONNX (COMPLETADA)

Incluye:

- Export ORT: `neural_network/notebook/data/checkpoints/textcnn_run/synapse_textcnn.onnx`
- Vocabulario: `neural_network/notebook/data/artifacts/vocab.json`
- Scripts: `neural_network/scripts/export_onnx.py`, `calibrate_checkpoint.py`, `verify_onnx.py`

DoD Parte 2 (cierre M3 / F6):

- Paridad PyTorch ↔ ONNX Runtime CPU en inferencia de prueba (`verify_onnx.py` OK).

Seguimiento (Fase 7 — worker frontend):

- `onnxruntime-web` (WASM/WebGPU), latencia en cliente, INT8 opcional.
- **Implementado:** `frontend/` (worker + UI pipeline). Pendiente: optimización INT8 y métricas de latencia publicadas.

---

## Milestone M4 — Producto Integrado para Demo

Ventana objetivo: 21-26 mayo 2026  
Estado: Pendiente

Incluye:

- Frontend pipeline + chat.
- Backend API con SSE y fallback.
- Integración E2E.

DoD:

- Flujo completo estable (pregunta → clasificación → streaming).

---

## Milestone M5 — Release de Sustentación

Ventana objetivo: 27-28 mayo 2026  
Estado: Pendiente

Incluye:

- Testing completo.
- Deploy frontend/backend.
- Smoke tests post-deploy.

DoD:

- Entorno público estable para demostración.

