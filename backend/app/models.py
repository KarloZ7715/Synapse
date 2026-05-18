from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class ChatMessage(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str = Field(min_length=1, max_length=4000)


class ChatOptions(BaseModel):
    model_id: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=64, le=4096)


class ChatRequest(BaseModel):
    pregunta: str = Field(min_length=1, max_length=4000)
    metadata: ClassificationMetadata
    historial: list[ChatMessage] = Field(default_factory=list, max_length=10)
    options: ChatOptions = Field(default_factory=ChatOptions)