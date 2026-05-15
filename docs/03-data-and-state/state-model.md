# Modelo de Datos y Estado — Synapse

## Principio General

Synapse es **stateless** a nivel de infraestructura. No hay base de datos, no hay persistencia en disco, no hay cookies. Todo el estado es efímero y se almacena exclusivamente en memoria durante la sesión del navegador.

## Estados por Capa

### 1. Frontend (SolidJS)


| Estado                          | Tipo                           | Dónde vive               | Persiste        |
| ------------------------------- | ------------------------------ | ------------------------ | --------------- |
| Pregunta actual                 | `createSignal<string>`         | Componente ChatInput     | ❌               |
| Respuesta actual (streaming)    | `createSignal<string>`         | Componente ChatPanel     | ❌               |
| Historial de conversación       | `createStore<Message[]>`       | Context global           | ❌ (máx 5 pares) |
| Metadatos de clasificación      | `createSignal<Metadata>`       | Componente MetadataPanel | ❌               |
| Estado de carga del modelo ONNX | `createSignal<ModelStatus>`    | Context global           | ❌               |
| Estado del Web Worker           | `createSignal<WorkerState>`    | Context global           | ❌               |
| Preferencia de tema             | `createSignal<"dark"|"light">` | Context global           | ✅ localStorage  |


### 2. Web Worker (Clasificador)


| Estado              | Tipo               | Persiste                  |
| ------------------- | ------------------ | ------------------------- |
| Sesión ONNX Runtime | `InferenceSession` | ❌ (se recrea al recargar) |
| Modelo ONNX cargado | `ArrayBuffer`      | ✅ Cache del navegador     |


### 3. Backend (FastAPI)


| Estado                     | Tipo                | Persiste                   |
| -------------------------- | ------------------- | -------------------------- |
| Caché de respuestas        | LRU dict en memoria | ❌ (se pierde al reiniciar) |
| Estado del circuit breaker | Contador de fallos  | ❌                          |
| Rate limiter               | Dict por IP         | ❌                          |


## Estructura del Historial de Conversación

```typescript
interface ConversationState {
  messages: Message[];
  maxMessages: number; // 10 (5 pares)
}

interface Message {
  id: string; // nanoid
  rol: "user" | "assistant";
  contenido: string;
  metadata?: ClassificationMetadata; // solo en mensajes de usuario
  timestamp: number;
}
```

El historial se usa para:

1. Enviar contexto al LLM (últimos 5 pares)
2. Mostrar la conversación en la UI (scrollable)

## Flujo de Estado en una Interacción

```
1. Usuario escribe pregunta
   → setPregunta(texto)

2. Usuario envía (Enter o botón)
   → addToHistory({rol: "user", contenido: pregunta})
   → postMessage(pregunta) al Worker
   → setWorkerState("classifying")

3. Worker termina clasificación
   → setMetadata(resultado)
   → setWorkerState("idle")
   → POST /api/chat con pregunta + metadata + historial
   → setStreaming(true)

4. Backend responde con SSE
   → onToken: setResponse(prev => prev + token)
   → onDone:
       → addToHistory({rol: "assistant", contenido: response})
       → setStreaming(false)
       → setPregunta("")
```

## Persistencia (solo lo necesario)


| Dato              | Mecanismo                      | Justificación             |
| ----------------- | ------------------------------ | ------------------------- |
| Tema (dark/light) | `localStorage`                 | Experiencia de usuario    |
| Modelo ONNX       | Cache del navegador (CDN)      | Evitar redescarga de 30MB |
| API keys          | Variables de entorno en Render | Seguridad                 |


## Lo que NO se almacena

- ❌ Usuarios / cuentas
- ❌ Historial de conversaciones entre sesiones
- ❌ Métricas de uso entre reinicios
- ❌ Cookies de seguimiento
- ❌ Analytics de terceros

