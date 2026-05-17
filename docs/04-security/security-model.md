# Modelo de Seguridad — Synapse

## Principios

1. **Zero trust:** Ningún dato del usuario sale del navegador sin necesidad.
2. **Secrets never in frontend:** Las API keys de Groq y Google Gemini solo existen en el backend.
3. **Minimal data collection:** No se almacena información personal. No hay cookies de tracking.
4. **Defense in depth:** Seguridad en cada capa (frontend, backend, deploy).

## Capas de Seguridad

### 1. Frontend

| Medida       | Implementación                              |
| ------------ | ------------------------------------------- |
| CSP Headers  | Configurados en Cloudflare Pages            |
| CORS         | Solo permite requests al backend autorizado |
| Sin eval()   | Política CSP `script-src 'self'`            |
| SRI          | Subresource Integrity para CDN externos     |
| Sin secretos | Las API keys NUNCA en el código frontend    |
| HTTPS        | Forzado por Cloudflare (redirect 301)       |

### 2. Comunicación Frontend → Backend

| Medida              | Implementación                      |
| ------------------- | ----------------------------------- |
| CORS restrictivo    | Solo origen de Cloudflare Pages     |
| HTTPS               | Cloudflare → Render con TLS         |
| Rate limiting       | 20 req/min por IP en el backend     |
| Validación de input | Zod (frontend) + Pydantic (backend) |

### 3. Backend (FastAPI)

| Medida          | Implementación                                                       |
| --------------- | -------------------------------------------------------------------- |
| API keys        | `GROQ_API_KEY` y `GEMINI_API_KEY` via variables de entorno en Render |
| No hardcoding   | Configuración desde `.env` (dev) y Render dashboard (prod)           |
| Rate limiting   | `slowapi` con límite por IP                                          |
| Timeout         | 30s máximo por request al LLM                                        |
| Circuit breaker | Previene cascada de fallos                                           |
| Logging mínimo  | Sin loggear preguntas de usuarios (solo metadatos)                   |

### 4. Gestión de Secretos

**Desarrollo:**

- `.env` — no se commitea (en `.gitignore`)
- `GROQ_API_KEY=gsk_xxx`
- `GEMINI_API_KEY=AIzaxxx`

**Producción (Render):**

- Variables de entorno configuradas en el dashboard de Render
- `GROQ_API_KEY=gsk_xxx`
- `GEMINI_API_KEY=AIzaxxx`

### 5. Cloudflare Pages

| Medida  | Implementación                      |
| ------- | ----------------------------------- |
| HTTPS   | Siempre activado                    |
| Headers | `_headers` file en raíz             |
| CSP     | Content-Security-Policy configurado |
| HSTS    | max-age=31536000; includeSubDomains |

### 6. GitHub

| Medida                 | Implementación                        |
| ---------------------- | ------------------------------------- |
| Sin secretos en repo   | `.env` en `.gitignore`                |
| Dependencias auditadas | `pnpm audit` + `socket.dev`           |
| Biome security rules   | Linting de seguridad en CI            |
| Pre-commit hooks       | lefthook bloquea commits con secretos |

## Headers de Seguridad

```yaml
# Cloudflare Pages _headers
  Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' https://cdn.jsdelivr.net https://synapse-api.onrender.com; style-src 'self' 'unsafe-inline'
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()

# CORS — Backend FastAPI
origins = ["https://synapse.pages.dev"]
```

## Verificación Pre-Deploy

- `.env` en `.gitignore`
- Sin strings que parezcan API keys en el código (`grep -r "gsk_\|AIza" src/`)
- CSP headers configurados en Cloudflare
- CORS solo permite el dominio de producción
- Rate limiting activo en backend
