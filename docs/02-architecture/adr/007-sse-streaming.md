# ADR-007: SSE Streaming para Respuestas del LLM

## Contexto

Las respuestas del LLM pueden tardar 3-15 segundos en generarse completamente. Necesitamos transmitir los tokens al frontend en tiempo real para que el usuario vea la respuesta generándose, en lugar de esperar a que esté completa.

## Decisión

Usaremos **Server-Sent Events (SSE)** con `EventSourceResponse` de FastAPI en el backend y `EventSource` en el frontend.

## Justificación

1. **Unidireccional y simple:** SSE es perfecto para streaming servidor→cliente. No necesitamos comunicación bidireccional (WebSocket sería overkill).
2. **Nativo en FastAPI:** `EventSourceResponse` es parte de FastAPI desde v0.135.0. Implementación con `yield` en generadores async:

```python
from fastapi.sse import EventSourceResponse

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate():
        async for token in llm_stream(request):
            yield {"data": token}
        yield {"data": "[DONE]"}
    return EventSourceResponse(generate())
```

1. **Nativo en navegadores:** `EventSource` API está disponible en todos los navegadores modernos. Reconexión automática si la conexión se cae.
2. **Renderizado progresivo:** Cada token recibido actualiza un signal de SolidJS, que renderiza solo el nodo DOM afectado (sin re-renderizar todo el componente).
3. **Sin dependencias extra:** A diferencia de WebSocket (requiere librerías adicionales en ambos lados), SSE usa HTTP estándar.

## Formato de Mensajes

```
data: {"token": "La "}

data: {"token": "recursividad "}

data: {"token": "es "}

data: {"token": "cuando "}
...

data: [DONE]
```

## Implementación Frontend

```typescript
// useChat.ts — SolidJS
const [response, setResponse] = createSignal("");
const [streaming, setStreaming] = createSignal(false);

async function sendMessage(question: string, metadata: Metadata) {
  setStreaming(true);
  setResponse("");

  const eventSource = new EventSource(
    `/api/chat?question=${encodeURIComponent(question)}&metadata=${JSON.stringify(metadata)}`,
  );

  eventSource.onmessage = (event) => {
    if (event.data === "[DONE]") {
      setStreaming(false);
      eventSource.close();
      return;
    }
    const { token } = JSON.parse(event.data);
    setResponse((prev) => prev + token);
  };
}
```

Nota: Idealmente se usará POST + fetch con streaming en lugar de GET + EventSource. Implementación final con `fetch` + `ReadableStream`.

## Alternativas Consideradas

| Alternativa        | Rechazada porque                                                                 |
| ------------------ | -------------------------------------------------------------------------------- |
| WebSocket          | Bidireccional innecesario. Más complejo en Render (necesita upgrade de conexión) |
| Long Polling       | Ineficiente, latencia alta, desperdicio de requests                              |
| Respuesta completa | Mala UX: usuario espera 10s viendo un spinner                                    |
| gRPC streaming     | Overkill para navegador, requiere tooling extra                                  |

## Consecuencias

- **Positivas:** UX fluida (token por token). Nativo en FastAPI y navegadores. Sin dependencias extra.
- **Negativas:** HTTP/1.1 limita a 6 conexiones simultáneas por dominio. No es problema para 1 usuario.
- **Mitigación:** HTTP/2 en Cloudflare Pages y Render resuelve el límite de conexiones.
