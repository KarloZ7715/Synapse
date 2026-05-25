# API Contracts — Synapse

> **Alineación con el modelo TextCNN:** el clasificador ONNX actual expone **8** etiquetas de `dominio` (ver `neural_network/scripts/training_labels.py` y `frontend/src/types/classifier.ts`). Los contratos de request deben usar exactamente ese literal union hasta que un reentrenamiento amplíe la taxonomía.

## Base URL

- **Desarrollo:** `http://localhost:8000`
- **Producción:** `https://synapse-api.onrender.com`

## Endpoints

### POST /api/chat

Envía la pregunta del usuario con metadatos de clasificación y recibe la respuesta del LLM en streaming SSE.

**Request:**

```json
{
  "pregunta": "No entiendo nada de recursividad",
  "metadata": {
    "nivel_tecnico": "principiante",
    "urgencia": "alta",
    "emocion": "frustracion",
    "dominio": "backend",
    "confianza": 0.87
  },
  "historial": [
    { "rol": "user", "contenido": "¿Qué es un bucle for?" },
    { "rol": "assistant", "contenido": "Un bucle for es..." }
  ],
  "head_confidences": {
    "nivel_tecnico": 0.91,
    "urgencia": 0.88,
    "emocion": 0.85,
    "dominio": 0.72
  },
  "options": {
    "model_id": "llama-3.1-8b-instant",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 1024
  }
}
```

> **Ensamblaje del system prompt:** `backend/app/prompts/builder.py` (`build_system_prompt`). El frontend envía `historial` (últimos 10 mensajes de turnos previos completados) y opcionalmente `head_confidences` para suavizar reglas en cabezas con softmax &lt; 0.5.

---

### POST /api/prompt/preview

Devuelve el system prompt ensamblado (misma lógica que `/api/chat`, sin invocar al LLM). Usado por las pestañas Prompt y LLM del HUD.

**Request:**

```json
{
  "metadata": {
    "nivel_tecnico": "principiante",
    "urgencia": "alta",
    "emocion": "frustracion",
    "dominio": "backend",
    "confianza": 0.87
  },
  "head_confidences": {
    "nivel_tecnico": 0.91,
    "urgencia": 0.88,
    "emocion": 0.85,
    "dominio": 0.72
  }
}
```

**Response:**

```json
{
  "system_prompt": "Eres Synapse, un tutor de programacion..."
}
```

**Response:** `text/event-stream` (SSE)

```
data: {"token": "¡Tranquilo! "}
data: {"token": "La recursividad "}
data: {"token": "es más simple "}
...
data: [DONE]
```

**Último evento (metadatos de uso):**

```
data: {"type": "usage", "provider": "groq", "tokens_input": 245, "tokens_output": 512, "latency_ms": 3200}
```

**Errores:**

```json
// 400 — Request inválido
{"error": "validation_error", "detail": "pregunta es requerida"}

// 429 — Rate limit excedido
{"error": "rate_limit", "retry_after": 30}

// 500 — Error interno / proveedores caídos
{"error": "service_unavailable", "detail": "Todos los proveedores LLM no disponibles"}
```

---

### GET /health

Health check para UptimeRobot y monitoreo.

**Response:**

```json
{
  "status": "ok",
  "groq": "available",
  "gemini": "available",
  "cache_size": 47
}
```

---

## Tipos TypeScript (Frontend ↔ Backend)

```typescript
// === Request Types ===

interface ChatRequest {
  pregunta: string;
  metadata: ClassificationMetadata;
  historial?: Message[];
}

interface ClassificationMetadata {
  nivel_tecnico: "principiante" | "intermedio" | "avanzado";
  urgencia: "baja" | "media" | "alta";
  emocion:
    | "frustracion"
    | "confusion"
    | "curiosidad"
    | "ansiedad"
    | "motivacion"
    | "abrumado"
    | "confiado"
    | "desesperado"
    | "neutral";
  /** Cabezal `dominio` del ONNX actual (8 clases). */
  dominio:
    | "backend"
    | "frontend"
    | "bases_de_datos"
    | "movil"
    | "devops"
    | "data_science"
    | "sistemas_seguridad"
    | "general";
  confianza: number; // 0-1
}

interface Message {
  rol: "user" | "assistant";
  contenido: string;
}

// === Response Types ===

interface SSETokenEvent {
  token: string;
}

interface SSEUsageEvent {
  type: "usage";
  provider: "groq" | "gemini";
  tokens_input: number;
  tokens_output: number;
  latency_ms: number;
}

interface ErrorResponse {
  error: string;
  detail?: string;
  retry_after?: number;
}

interface HealthResponse {
  status: "ok" | "degraded";
  groq: "available" | "unavailable";
  gemini: "available" | "unavailable";
  cache_size: number;
}
```

## Esquemas Pydantic (Backend)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class ClassificationMetadata(BaseModel):
    nivel_tecnico: Literal["principiante", "intermedio", "avanzado"]
    urgencia: Literal["baja", "media", "alta"]
    emocion: Literal[
        "frustracion",
        "confusion",
        "curiosidad",
        "ansiedad",
        "motivacion",
        "abrumado",
        "confiado",
        "desesperado",
        "neutral",
    ]
    dominio: Literal[
        "backend",
        "frontend",
        "bases_de_datos",
        "movil",
        "devops",
        "data_science",
        "sistemas_seguridad",
        "general",
    ]
    confianza: float = Field(ge=0.0, le=1.0)

class Message(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str

class ChatRequest(BaseModel):
    pregunta: str = Field(min_length=1, max_length=2000)
    metadata: ClassificationMetadata
    historial: Optional[list[Message]] = Field(default_factory=list, max_length=10)
```

## Rate Limiting

- **Límite por IP:** 20 requests/minuto
- **Límite global:** 100 requests/minuto
- **Cabeceras de respuesta:** `X-RateLimit-Remaining`, `Retry-After`

## Versionado

- API v1: ruta base sin prefijo (`/api/chat`)
- Futuras versiones: `/api/v2/chat`

