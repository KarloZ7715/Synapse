# ADR-006: Web Worker Dedicado para Inferencia ONNX

## Contexto

La clasificación por red neuronal debe ejecutarse en el navegador sin bloquear la UI. El modelo ONNX (TextCNN + embeddings) es más liviano que un transformer, pero la carga del grafo y la inicialización de WebGPU siguen siendo trabajo intensivo.

## Decisión

La inferencia ONNX se ejecutará en un **Web Worker dedicado**, comunicándose con el hilo principal mediante `postMessage`.

## Justificación

1. **UI no bloqueada:** Sin Web Worker, la descarga del ONNX, la inicialización de `InferenceSession` y WebGPU pueden congelar la UI 1–3 s. El Worker absorbe esta carga.
2. **Aislamiento de dependencias:** ONNX Runtime Web (ort-wasm, ort-webgpu) son dependencias pesadas que no deberían estar en el bundle principal. El Worker mantiene el bundle de la UI ligero.
3. **Comunicación simple:** El patrón request/response con `postMessage` es suficiente:

- Main → Worker: `{ type: "classify", text: "..." }`
- Worker → Main: `{ type: "result", metadata: {...} }`

4. **Carga progresiva:** Mientras el Worker descarga e inicializa el modelo, la UI puede mostrar un indicador de carga y permitir al usuario escribir su pregunta.
5. **Vite soporte nativo:** `new Worker(new URL('./classifier.worker.ts', import.meta.url), { type: 'module' })` — Vite compila Workers con TypeScript y code-splitting automático.

## Implementación

```typescript
// main.ts — Hilo principal
const worker = new Worker(
  new URL("./workers/classifier.worker.ts", import.meta.url),
  { type: "module" },
);

worker.postMessage({ type: "classify", text: userQuestion });

worker.onmessage = (event) => {
  const metadata = event.data;
  // Enviar metadata al backend junto con la pregunta
};

// classifier.worker.ts — Web Worker
import * as ort from "onnxruntime-web";

// Configurar WebGPU
ort.env.wasm.wasmPaths = "https://cdn.example.com/ort/";

let session: ort.InferenceSession;

self.onmessage = async (event) => {
  if (event.data.type === "classify") {
    if (!session) {
      session = await ort.InferenceSession.create(
        "/models/synapse-textcnn.onnx",
      );
    }
    const tokens = tokenize(event.data.text);
    const results = await session.run({ input: tokens });
    const metadata = postProcess(results);
    self.postMessage(metadata);
  }
};
```

## Alternativas Consideradas

| Alternativa              | Rechazada porque                               |
| ------------------------ | ---------------------------------------------- |
| Hilo principal           | Bloquea la UI durante carga e inferencia       |
| Service Worker           | Sin acceso a WebGPU (limitación de Chrome)     |
| Clasificación en backend | Rompe arquitectura híbrida, envía datos crudos |

## Consecuencias

- **Positivas:** UI siempre responsive. Carga del modelo transparente. Bundle splitting automático.
- **Negativas:** Complejidad adicional de comunicación Worker ↔ Main. Debugging más difícil.
- **Mitigación:** Mensajes tipados con TypeScript. Logs del Worker visibles en DevTools.
