from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException

from app.config import Settings
from app.models import ChatRequest, ClassificationMetadata

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

EMOTION_MODIFIER: dict[str, str] = {
    "frustracion": "Adopta un tono empatico y tranquilizador. Simplifica los conceptos al maximo.",
    "confusion": "Estructura la respuesta paso a paso, sin asumir conocimiento previo.",
    "curiosidad": "Aprovecha el interes del usuario y anade un ejemplo adicional corto.",
    "ansiedad": "Empieza calmando. Responde directo y evita alarmismo.",
    "motivacion": "Refuerza el impulso del usuario y termina con un siguiente paso accionable.",
    "abrumado": "Reduce la respuesta a una sola idea por bloque y evita listas largas.",
    "confiado": "Ve directo al punto con tono tecnico y concreto.",
    "desesperado": "Da primero la salida practica y luego la explicacion.",
    "neutral": "Usa un tono profesional y claro.",
}

LEVEL_MODIFIER: dict[str, str] = {
    "principiante": "Evita jerga innecesaria, usa analogias y confirma la intuicion basica.",
    "intermedio": "Asume sintaxis basica y enfatiza el patron conceptual.",
    "avanzado": "Ve al grano y menciona tradeoffs o detalles internos cuando aporten valor.",
}


def sse_event(payload: dict[str, object] | str) -> str:
    if isinstance(payload, str):
        data = payload
    else:
        data = json.dumps(payload, ensure_ascii=False)
    return f"data: {data}\n\n"


def build_system_prompt(metadata: ClassificationMetadata) -> str:
    emotion_rule = EMOTION_MODIFIER.get(metadata.emocion, "Usa un tono claro y profesional.")
    level_rule = LEVEL_MODIFIER.get(metadata.nivel_tecnico, "Adapta la profundidad al usuario.")
    return (
        "Eres Synapse, un tutor de programacion en espanol. "
        f"El usuario tiene nivel {metadata.nivel_tecnico}, urgencia {metadata.urgencia}, "
        f"emocion {metadata.emocion} y dominio {metadata.dominio}. "
        "Responde con enfoque pedagogico, codigo cuando ayude, y termina con un siguiente paso util.\n\n"
        f"REGLAS POR EMOCION: {emotion_rule}\n"
        f"REGLAS POR NIVEL: {level_rule}\n"
        "FORMATO:\n"
        "1. Diagnostico breve.\n"
        "2. Solucion o explicacion principal.\n"
        "3. Siguiente paso accionable."
    )


def build_messages(request: ChatRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(request.metadata)}
    ]
    for item in request.historial:
        messages.append({"role": item.rol, "content": item.contenido})
    messages.append({"role": "user", "content": request.pregunta})
    return messages


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

                choices = chunk.get("choices") or []
                if not choices:
                    continue

                delta = choices[0].get("delta") or {}
                token = delta.get("content")
                if token:
                    yield sse_event({"token": token})

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