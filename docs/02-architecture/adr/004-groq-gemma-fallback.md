# ADR-004: Groq (Llama 3.1 8B) Principal + Gemma 4 Fallback

## Contexto

El sistema necesita un LLM que genere respuestas de tutoría de programación en español, adaptadas a los metadatos de clasificación (nivel, urgencia, emoción, dominio). Debe ser rápido (<5s total), gratuito y con buena calidad de español.

## Decisión

Usaremos **Groq con Llama 3.1 8B Instant como proveedor principal** y **Google Gemini con Gemma 4 26B A4B como fallback** automático mediante circuit breaker.

## Justificación

### Groq como Principal

1. **Velocidad extrema:** 560 tokens/segundo (vs ~300-500 de Gemini). Para un tutor interactivo, la velocidad de respuesta es crítica.
2. **Costo cero:** Plan Developer gratuito con 250K TPM y 1K RPM.
3. **Calidad suficiente:** Llama 3.1 8B maneja bien español y explicaciones de programación nivel principiante-intermedio.
4. **API simple:** SDK Python oficial con `AsyncGroq`, streaming nativo.

### Gemma 4 como Fallback

1. **Español nativo:** Entrenado en 140+ idiomas. Fluidez superior al español para conceptos complejos.
2. **Razonamiento avanzado:** Mejor en benchmarks de código y razonamiento multi-paso. Ideal para preguntas de nivel avanzado.
3. **Gratuito:** Tier 1 con $250/mes cap (más que suficiente para uso académico).
4. **Cobertura:** Si Groq falla por rate limiting o timeout, Gemma 4 asegura disponibilidad.

### Circuit Breaker

- **Patrón:** 3 fallos consecutivos en Groq → switch a Gemini por 30 segundos
- **Implementación:** `tenacity` con exponential backoff + jitter
- **Transparencia:** El usuario no nota el cambio de proveedor

## Comparativa


| Criterio      | Groq (Llama 3.1 8B) | Gemma 4 (26B A4B)                 |
| ------------- | ------------------- | --------------------------------- |
| Velocidad     | 🥇 560 tps          | ~300-500 tps                      |
| Costo input   | $0.05/1M            | $0.06/1M                          |
| Costo output  | $0.08/1M            | $0.30/1M                          |
| Español       | Bueno               | 🥇 Nativo 140+ idiomas            |
| Código        | Bueno               | 🥇 Mejor razonamiento             |
| Plan gratuito | ✅ Developer         | ✅ Tier 1 (Default Gemini Project) |


## Alternativas Consideradas


| Alternativa           | Rechazada porque                                  |
| --------------------- | ------------------------------------------------- |
| Solo Groq             | Sin fallback si hay outage o rate limit           |
| Solo Gemini           | Más caro en output (5x), más lento                |
| OpenAI                | No tiene plan gratuito real                       |
| Claude                | No tiene plan gratuito                            |
| Modelo local (Ollama) | Requiere infraestructura (Se requiere un buen PC) |


## Consecuencias

- **Positivas:** Alta disponibilidad, costos separados por proveedor, lo mejor de ambos mundos
- **Negativas:** Complejidad de mantener dos integraciones
- **Mitigación:** Pydantic AI abstrae ambos proveedores bajo una misma API

