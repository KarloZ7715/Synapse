# ADR-002: FastAPI como Backend API Gateway

## Contexto

Necesitamos un backend que actúe como API Gateway entre el frontend (SolidJS SPA) y los proveedores de LLM (Groq, Google Gemini). Debe soportar:

- Streaming de tokens en tiempo real (SSE)
- Rate limiting y circuit breaker entre múltiples proveedores
- Caché semántico para reducir costos
- Despliegue gratuito en Render
- Integración nativa con SDKs de Groq y Google Gemini

## Decisión

Usaremos **FastAPI + Python 3.12 con Pydantic AI** como framework de backend.

## Justificación

1. **Ecosistema LLM dominante:** Los SDKs oficiales de Groq (`groq` Python library con `AsyncGroq`) y Google Gemini (`google-generativeai` con retry automático y exponential backoff) están en Python con tipado completo. Pydantic AI unifica ambos bajo una misma API de agentes.
2. **SSE nativo:** FastAPI 0.135.0+ incluye `EventSourceResponse` nativo, diseñado específicamente para streaming de tokens de LLMs. El patrón `yield` con generadores async es natural y eficiente.
3. **Validación tipada end-to-end:** Pydantic valida schemas desde el request HTTP hasta la respuesta del LLM y de vuelta. Zod en el frontend + Pydantic en el backend = type safety completa.
4. **Circuit breaker probado:** Librerías como `tenacity` permiten implementar reintentos con exponential backoff y jitter. Patrones documentados para evitar "retry storms" cuando un proveedor falla.
5. **Deploy simple:** Render auto-detecta FastAPI, solo necesita `uvicorn` como ASGI server. Un solo comando: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
6. **No necesitas base de datos:** El caché semántico se implementa en memoria (LRU cache). No hay usuarios, no hay persistencia. FastAPI es ligero sin ORM.

## Alternativas Consideradas


| Alternativa        | Rechazada porque                                                                |
| ------------------ | ------------------------------------------------------------------------------- |
| Node.js + Hono/Bun | SDKs de LLM menos maduros. Sin equivalente a Pydantic AI. Type safety más débil |
| Node.js + Express  | Callback-based, TypeScript "afterthought". Sin validación nativa                |
| Go + Gin/Fiber     | Excelente performance, pero ecosistema LLM casi inexistente                     |
| Vercel Serverless  | Timeout 10s en plan free — insuficiente para streaming de LLM                   |


## Consecuencias

- **Positivas:** SDKs oficiales, Pydantic AI multi-provider, SSE nativo, deploy simple
- **Negativas:** Python es más lento que Go/Rust en I/O pura (irrelevante: el cuello de botella es el LLM, no el framework)
- **Mitigación:** Uvicorn con workers para concurrencia. Async/await para no bloquear

