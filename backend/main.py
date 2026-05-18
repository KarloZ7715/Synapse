from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models import ChatRequest
from app.services.groq_stream import stream_chat_completion

settings = get_settings()

app = FastAPI(title="Synapse Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, object]:
    groq_available = bool(settings.groq_api_key)
    return {
        "status": "ok" if groq_available else "degraded",
        "groq": "available" if groq_available else "unavailable",
        "cache_size": 0,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in stream_chat_completion(request, settings):
                yield event
        except HTTPException as exc:
            yield f"data: {json.dumps({'error': 'service_unavailable', 'detail': exc.detail}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # pragma: no cover - defensive streaming fallback
            yield f"data: {json.dumps({'error': 'service_unavailable', 'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )