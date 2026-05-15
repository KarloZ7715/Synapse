# ADR-003: ONNX Runtime Web + WebGPU en Web Worker

## Contexto

La arquitectura requiere que la clasificación de la pregunta del usuario se ejecute localmente en el navegador (por privacidad, latencia y para no enviar datos sin procesar al servidor). El modelo debe clasificar en <100ms sin bloquear la UI.

## Decisión

Usaremos **ONNX Runtime Web con backend WebGPU**, ejecutándose dentro de un **Web Worker dedicado**.

## Justificación

1. **WebGPU > WASM para ML:** WebGPU ofrece 15-30x mejor rendimiento que WebGL y alcanza ~80% del rendimiento nativo. Para inferencia de transformers pequeños como DistilBETO, WebGPU es el backend óptimo.
2. **Web Worker = UI no bloqueada:** La carga del modelo ONNX (~30-50MB) y la inferencia ocurren en un hilo separado. El hilo principal solo recibe los metadatos de clasificación vía `postMessage`.
3. **ONNX Runtime Web es el estándar:** Microsoft mantiene ONNX Runtime Web con soporte oficial para WebGPU desde 2024. La API es estable y bien documentada.
4. **Sin dependencias de servidor:** El modelo ONNX se descarga una vez (cacheado por Cloudflare CDN) y se ejecuta completamente offline. Ideal para un demo que debe funcionar sin configuración.
5. **Privacidad:** La pregunta del usuario nunca sale del navegador durante la clasificación. Solo los metadatos (nivel, urgencia, emoción, dominio) se envían al backend.

## Pipeline Técnico

```
1. Frontend: usuario escribe pregunta
2. postMessage(pregunta) → Web Worker
3. Worker: tokeniza → ONNX Runtime Web (WebGPU) → logits
4. Worker: postMessage({nivel, urgencia, emocion, dominio}) → Main thread
5. Frontend: construye payload y envía al backend
```

## Modelo

- **Arquitectura:** DistilBETO (versión ligera de BETO, BERT en español)
- **Fine-tuning:** Clasificación multi-etiqueta con 4 cabezas de clasificación
- **Exportación:** PyTorch → ONNX con cuantización INT8
- **Tamaño estimado:** ~25-40MB (INT8 cuantizado)

## Alternativas Consideradas


| Alternativa                 | Rechazada porque                                             |
| --------------------------- | ------------------------------------------------------------ |
| Clasificación en el backend | Latencia extra, privacidad, rompe la arquitectura híbrida    |
| Transformers.js             | Más pesado que ONNX Runtime, WebGPU support aún experimental |
| TensorFlow.js               | Ecosistema más limitado que ONNX para WebGPU                 |
| WASM sin WebGPU             | Significativamente más lento para transformers               |


## Consecuencias

- **Positivas:** Inferencia <100ms, privacidad, sin costos de servidor para clasificación
- **Negativas:** Descarga inicial del modelo ~30MB. Compatibilidad limitada a navegadores con WebGPU
- **Mitigación:** Mostrar indicador de carga durante la descarga. Fallback a WASM si WebGPU no disponible

