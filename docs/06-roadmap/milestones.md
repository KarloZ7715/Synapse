# Milestones — Synapse (Estado Actual)

Referencia operativa alineada con `docs/06-roadmap/roadmap.md`.

Última actualización: 15 mayo 2026.

---

## Snapshot de Avance

| Bloque | Estado |
| --- | --- |
| Dataset base (F1-F2) | Completado |
| Etiquetado LLM (F3) | Completado |
| Augmentation + dataset final 4k–6k (F4) | Completado |
| Entrenamiento + ONNX (F5-F6) | Pendiente |
| App (F7-F10) | Pendiente |
| Testing + Deploy (F11-F12) | Pendiente |

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
Estado: Pendiente

Incluye:
- Entrenamiento TextCNN + FastText (multi-cabeza categórica).
- Exportación ONNX (`torch.onnx.export`) y validación de inferencia.

DoD:
- Checkpoint final + métricas.
- Artefacto ONNX listo para integración frontend.

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
