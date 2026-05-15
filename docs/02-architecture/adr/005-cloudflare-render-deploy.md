# ADR-005: Cloudflare Pages (Frontend) + Render (Backend)

## Contexto

Necesitamos desplegar el frontend (SPA estática) y el backend (FastAPI con streaming) en plataformas gratuitas con deploy automático desde GitHub.

## Decisión

Usaremos **Cloudflare Pages para el frontend** y **Render para el backend**, con **UptimeRobot** para mantener el backend activo.

## Justificación

### Cloudflare Pages (Frontend)

1. **Ilimitado y gratuito:** Ancho de banda ilimitado, 500 builds/mes, sin costo.
2. **300+ edge locations:** Latencia mínima global. La descarga del modelo ONNX (~30MB) se beneficia del CDN.
3. **Git auto-deploy:** Conexión directa con GitHub. Cada push a `main` dispara build y deploy automático.
4. **SPA nativo:** Soporte para Single Page Applications con redirects configurable.

### Render (Backend)

1. **Web Service real:** A diferencia de serverless (Vercel, Cloudflare Workers), Render ejecuta un proceso continuo con Uvicorn. Sin timeout artificial — crítico para streaming de LLM.
2. **750h/mes gratis:** Suficiente para un demo universitario.
3. **Python nativo:** Auto-detecta FastAPI, configura `uvicorn` automáticamente.
4. **Git auto-deploy:** Conexión con GitHub. Cada push redeploya.

### Vercel descartado para backend

Vercel soporta FastAPI pero como **función serverless con timeout de 10s en plan Hobby**. El streaming de LLM frecuentemente excede este límite. Render no tiene esta restricción.

### UptimeRobot

El Web Service de Render entra en idle spin-down tras 15 minutos sin tráfico. UptimeRobot envía un ping `GET /health` cada 5 minutos, manteniéndolo activo 24/7. Ambos gratuitos.

## Tabla Comparativa de Plataformas


| Plataforma       | Frontend SPA | Backend Python | Gratis real     | Timeout streaming |
| ---------------- | ------------ | -------------- | --------------- | ----------------- |
| Cloudflare Pages | ✅ Ilimitado  | ❌              | ✅               | N/A               |
| Render           | ✅ Static     | ✅ Web Service  | ✅ 750h/mes      | ❌ Sin timeout     |
| Vercel           | ✅            | ✅ (serverless) | ✅               | ⚠️ 10s Hobby      |
| Netlify          | ✅            | ❌              | ✅               | N/A               |
| Railway          | ✅            | ✅              | ❌ $5/mes        | ❌ Sin timeout     |
| Fly.io           | ✅            | ✅              | ❌ Sin free tier | ❌ Sin timeout     |


## Consecuencias

- **Positivas:** 100% gratuito. Deploy automático. Sin timeouts.
- **Negativas:** Cold start de ~30s si UptimeRobot falla. Latencia entre frontend (edge) y backend (US/Europe).
- **Mitigación:** UptimeRobot con 2 monitores redundantes. El cold start solo afecta al primer usuario del día.

