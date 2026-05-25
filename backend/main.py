from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import ChatRequest, PromptPreviewRequest, PromptPreviewResponse
from app.prompts.builder import build_system_prompt
from app.services.groq_stream import stream_chat_completion

settings = get_settings()
BACKEND_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = BACKEND_ROOT / "static"

app = FastAPI(title="Synapse Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=STATIC_ROOT), name="assets")


@app.get("/health")
async def health() -> dict[str, object]:
    groq_available = bool(settings.groq_api_key)
    return {
        "status": "ok" if groq_available else "degraded",
        "groq": "available" if groq_available else "unavailable",
        "cache_size": 0,
    }


@app.post("/api/prompt/preview", response_model=PromptPreviewResponse)
async def prompt_preview(request: PromptPreviewRequest) -> PromptPreviewResponse:
    """Devuelve el system prompt ensamblado (misma logica que /api/chat)."""
    return PromptPreviewResponse(
        system_prompt=build_system_prompt(request.metadata, request.head_confidences),
    )


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