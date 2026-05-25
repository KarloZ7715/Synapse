from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException

from app.config import Settings
from app.models import ChatRequest
from app.prompts.builder import build_messages

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def sse_event(payload: dict[str, object] | str) -> str:
    if isinstance(payload, str):
        data = payload
    else:
        data = json.dumps(payload, ensure_ascii=False)
    return f"data: {data}\n\n"


async def stream_chat_completion(
    request: ChatRequest,
    settings: Settings,
) -> AsyncIterator[str]:
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    payload = {
        "model": request.options.model_id or settings.groq_model,
        "messages": build_messages(request),
        "temperature": request.options.temperature,
        "top_p": request.options.top_p,
        "max_tokens": request.options.max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    started_at = time.perf_counter()
    usage_emitted = False

    async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
        async with client.stream(
            "POST",
            GROQ_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code >= 400:
                detail = (await response.aread()).decode("utf-8", errors="replace")
                raise HTTPException(status_code=response.status_code, detail=detail[:800])

            async for raw_line in response.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue

                data = line[5:].strip()
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                usage = chunk.get("usage")
                if isinstance(usage, dict):
                    usage_emitted = True
                    yield sse_event(
                        {
                            "type": "usage",
                            "provider": "groq",
                            "tokens_input": usage.get("prompt_tokens", 0),
                            "tokens_output": usage.get("completion_tokens", 0),
                            "latency_ms": round((time.perf_counter() - started_at) * 1000),
                        }
                    )
                    await asyncio.sleep(0)

                choices = chunk.get("choices") or []
                if not choices:
                    continue

                delta = choices[0].get("delta") or {}
                token = delta.get("content")
                if token:
                    yield sse_event({"token": token})
                    await asyncio.sleep(0)

    if not usage_emitted:
        yield sse_event(
            {
                "type": "usage",
                "provider": "groq",
                "tokens_input": 0,
                "tokens_output": 0,
                "latency_ms": round((time.perf_counter() - started_at) * 1000),
            }
        )
