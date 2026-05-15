# Milestones — Synapse (Estado Actual)

Referencia operativa alineada con `docs/06-roadmap/roadmap.md`.

Última actualización: 14 mayo 2026.

---

## Snapshot de Avance

| Bloque | Estado |
| --- | --- |
| Dataset base (F1-F2) | Completado |
| Etiquetado LLM (F3) | Completado |
| Augmentation + split (F4) | Pendiente |
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

## Milestone M2 — Dataset Final Entrenable (Pendiente)

Ventana objetivo: 15-17 mayo 2026  
Estado: Pendiente

Incluye:
- Augmentation dirigido a clases minoritarias.
- Limpieza de duplicados.
- Split reproducible train/val/test.

DoD:
- `dataset/final/dataset.json`, `train.json`, `val.json`, `test.json`.
- Balance por clases dentro de umbrales definidos.

---

## Milestone M3 — Modelo ONNX Validado

Ventana objetivo: 18-20 mayo 2026  
Estado: Pendiente

Incluye:
- Fine-tuning DistilBETO multi-etiqueta.
- Exportación ONNX y validación de inferencia.

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
