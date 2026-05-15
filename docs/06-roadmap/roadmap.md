# Roadmap — Synapse

Proyecto de simulación. Universidad de Córdoba.  
Autores: Carlos Alberto Canabal Cordero, Sebastián José Leal Flórez.  
Última actualización: 14 mayo 2026.

---

## Estado General

| Fase | Descripción | Estado | Progreso |
| --- | --- | --- | --- |
| 1 | Dataset - GoEmotions ES | Completada | 100% |
| 2 | Dataset - Stack Overflow ES | Completada | 100% |
| 3 | Dataset - Etiquetado LLM | Completada | 100% |
| 4 | Dataset - Augmentation + Split | Pendiente | 0% |
| 5 | Fine-tuning RN | Pendiente | 0% |
| 6 | Exportación ONNX | Pendiente | 0% |
| 7 | Frontend - Pipeline | Pendiente | 0% |
| 8 | Frontend - Chat UI | Pendiente | 0% |
| 9 | Backend - API Gateway | Pendiente | 0% |
| 10 | Integración E2E | Pendiente | 0% |
| 11 | Testing | Pendiente | 0% |
| 12 | Deploy | Pendiente | 0% |

Progreso total: **3/12 fases (25%)**.

---

## Cronograma Ajustado

Semana 1 (14-20 mayo 2026): Fases 1-6  
- Cerrar dataset final para entrenamiento  
- Entrenar clasificador multi-etiqueta  
- Exportar y validar ONNX

Semana 2 (21-28 mayo 2026): Fases 7-12  
- Frontend + backend funcionales  
- Integración completa con streaming  
- Testing, deploy y preparación de sustentación

---

## Fases Completadas

## Fase 1 — Dataset GoEmotions ES

Estado: **Completada**  
Fecha: **14 mayo 2026**

Resultado:
- 54,263 ejemplos en español.
- Emociones GoEmotions mapeadas al esquema Synapse.
- Salida consolidada en `dataset/processed/goemotions_mapped.json`.

Criterios de cierre cumplidos:
- Archivo generado y legible.
- Distribución de clases inspeccionada.
- Mapeo consistente entre etiquetas fuente y destino.

---

## Fase 2 — Dataset Stack Overflow ES

Estado: **Completada**  
Fecha: **14 mayo 2026**

Resultado:
- 250 preguntas en español.
- Cuerpo (`body`) no vacío en 250/250.
- Rebalanceo de dominios para reducir sesgo extremo a backend.

Distribución actual por dominio:
- backend: 71
- frontend: 28
- bases_de_datos: 28
- devops: 28
- data_science: 28
- general: 28
- movil: 27
- ingenieria_software: 9
- seguridad: 3

Criterios de cierre cumplidos:
- `so_questions.json` con título, cuerpo, tags, score y dominio.
- Sin cuerpos vacíos.
- Set suficientemente diverso para etiquetado robusto.

---

## Fase 3 — Etiquetado LLM con Copilot

Estado: **Completada**  
Fecha: **14 mayo 2026**

Configuración de etiquetado:
- Proveedor: Copilot vía proxy OpenAI-compatible.
- Modelos de rotación: `gpt-5-mini`, `gpt-4.1`, `gpt-4o`.
- Validación de IDs contra `/v1/models`.

Resultado final (`dataset/processed/labeled.json`):
- 250/250 filas etiquetadas.
- 250/250 `question_id` únicos.
- Esquema completo por fila: `question_id`, `title`, `body`, `tags`, `domain_synapse`, `nivel_tecnico`, `urgencia`, `model_used`.
- Cuerpo no vacío en 250/250.

Distribución final:
- Nivel técnico: 122 principiante, 116 intermedio, 12 avanzado.
- Urgencia: 27 baja, 199 media, 24 alta.

Gate de calidad Fase 3:
- `dataset/processed/backups/deprecated/phase3_quality_report.json` => `overall_ready_for_phase4 = true`.

---

## Fases Pendientes (Plan Detallado)

## Fase 4 — Augmentation + Split

Estado: **Pendiente**  
Ventana objetivo: **15-17 mayo 2026**

Objetivo:
- Aumentar cobertura de clases minoritarias.
- Construir dataset final entrenable y reproducible.

Entradas:
- `dataset/processed/labeled.json`
- `dataset/processed/goemotions_mapped.json`

Actividades:
- Diseñar política de augmentation dirigida por clase minoritaria.
- Generar variaciones semánticamente equivalentes (sin cambiar etiqueta).
- Filtrar duplicados semánticos (título+cuerpo).
- Verificar balance mínimo por etiqueta en `nivel_tecnico`, `urgencia`, `dominio`.
- Construir split `train/val/test` reproducible con semilla fija.

Entregables:
- `dataset/final/dataset.json`
- `dataset/final/train.json`
- `dataset/final/val.json`
- `dataset/final/test.json`
- Métricas de balance por split.

Criterios de salida:
- Sin duplicados exactos entre splits.
- Balance aceptable por dimensión objetivo.
- Integridad JSON validada al 100%.

---

## Fase 5 — Fine-tuning de la RN

Estado: **Pendiente**  
Ventana objetivo: **18-19 mayo 2026**

Objetivo:
- Entrenar clasificador multi-etiqueta para 4 dimensiones.

Entradas:
- `dataset/final/train.json`, `val.json`, `test.json`

Actividades:
- Construir pipeline de tokenización.
- Configurar etiqueta multi-hot (26 salidas).
- Entrenar DistilBETO (`dccuchile/distilbert-base-spanish-wwm-cased`).
- Registrar métricas por epoch (F1 macro/micro, precision, recall).
- Seleccionar mejor checkpoint por `f1_macro`.

Entregables:
- Checkpoint final.
- Reporte de métricas en validación y test.

Criterios de salida:
- Entrenamiento reproducible.
- Métricas reportadas y trazables.
- Checkpoint exportable.

---

## Fase 6 — Exportación ONNX

Estado: **Pendiente**  
Ventana objetivo: **20 mayo 2026**

Objetivo:
- Exportar modelo a ONNX optimizado para navegador.

Actividades:
- Exportar con `optimum-cli`.
- Cuantizar modelo (INT8 cuando aplique).
- Validar inferencia local en Python.
- Preparar artefacto para frontend.

Entregables:
- Carpeta `onnx/` con modelo y tokenizer.
- Registro de tamaño, latencia y compatibilidad.

Criterios de salida:
- Carga correcta de ONNX.
- Inferencia consistente contra checkpoint base.

---

## Fase 7 — Frontend Pipeline

Estado: **Pendiente**  
Ventana objetivo: **21-22 mayo 2026**

Objetivo:
- Visualizar pipeline usuario → RN → LLM.

Actividades:
- Integrar worker ONNX.
- Renderizar metadata (`nivel`, `urgencia`, `emoción`, `dominio`).
- Mostrar estado de carga/inferencia.

Criterios de salida:
- Clasificación visible y estable en UI.
- Sin bloqueo del hilo principal.

---

## Fase 8 — Frontend Chat UI

Estado: **Pendiente**  
Ventana objetivo: **23-24 mayo 2026**

Actividades:
- Input + historial + streaming.
- Panel de conversación usable en desktop y móvil.
- Control de contexto corto en sesión.

Criterios de salida:
- UX completa para demo.
- Sin regresiones de accesibilidad crítica.

---

## Fase 9 — Backend API Gateway

Estado: **Pendiente**  
Ventana objetivo: **24-25 mayo 2026**

Actividades:
- `POST /api/chat`
- Prompt enriquecido con metadata RN.
- Fallback proveedor LLM.
- Rate limit + caché en memoria.

Criterios de salida:
- SSE estable.
- Fallback funcional ante fallo del primario.

---

## Fase 10 — Integración E2E

Estado: **Pendiente**  
Ventana objetivo: **26 mayo 2026**

Actividades:
- Flujo completo pregunta → clasificación → respuesta.
- Afinar prompts.
- Validar latencias objetivo.

Criterios de salida:
- Demo integral estable.

---

## Fase 11 — Testing

Estado: **Pendiente**  
Ventana objetivo: **27 mayo 2026**

Actividades:
- Unit tests frontend/backend.
- E2E Playwright.
- Cobertura y sanity checks.

Criterios de salida:
- Cobertura objetivo alcanzada.
- Escenarios críticos cubiertos.

---

## Fase 12 — Deploy

Estado: **Pendiente**  
Ventana objetivo: **28 mayo 2026**

Actividades:
- Deploy frontend (Cloudflare Pages).
- Deploy backend (Render).
- Smoke tests post-deploy.

Criterios de salida:
- URL pública estable para sustentación.

---

## Riesgos Actuales y Mitigaciones

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Clase `avanzado` vuelve a caer en Fase 4 | Medio | Validar balance por clase antes de split final |
| Modelo ONNX excede tamaño/latencia objetivo | Alto | Cuantización + poda + fallback WASM |
| Inestabilidad de proveedor LLM | Medio | Fallback + límites + observabilidad |
| Regresión de UX durante integración | Medio | Verificación E2E incremental por fase |

---

## Evidencia de Cierre Fase 3

- `dataset/processed/labeled.json`
- `dataset/processed/backups/deprecated/phase3_quality_report.json`
- `dataset/raw/so_questions.json`
