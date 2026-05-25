"""Ensamblaje del system prompt enriquecido para el LLM."""

from __future__ import annotations

from app.models import ChatRequest, ClassificationMetadata, HeadConfidences
from app.prompts.modifiers import (
    CONFIDENCE_RELIABLE_THRESHOLD,
    DEFAULT_DOMAIN,
    DEFAULT_EMOTION,
    DEFAULT_LEVEL,
    DEFAULT_URGENCY,
    DOMAIN_MODIFIER,
    EMOTION_MODIFIER,
    HEAD_WEAK_THRESHOLD,
    LEVEL_MODIFIER,
    URGENCY_MODIFIER,
)

IDENTITY_PROMPT = """\
Eres Synapse, un tutor de programacion experto, paciente y pedagogico en español.
Tu objetivo es guiar al estudiante: prioriza comprension y razonamiento; entrega codigo \
completo solo cuando acelere el aprendizaje o la urgencia lo exija.
Responde siempre en español. Adapta tono, profundidad y estructura al perfil que se indica abajo."""

PRIORITY_RULE = (
    "PRIORIDAD DE REGLAS: si hay conflicto, aplica en este orden: "
    "urgencia > emocion extrema (desesperado, abrumado, ansiedad) > nivel tecnico > dominio."
)

HEAD_LABELS: dict[str, str] = {
    "nivel_tecnico": "Nivel tecnico",
    "urgencia": "Urgencia",
    "emocion": "Emocion",
    "dominio": "Dominio",
}


def _confidence_percent(confianza: float) -> int:
    raw = confianza * 100 if 0.0 <= confianza <= 1.0 else confianza
    return round(raw)


def _confidence_policy(confianza: float) -> str:
    pct = _confidence_percent(confianza)
    if confianza >= CONFIDENCE_RELIABLE_THRESHOLD:
        return (
            f"CONFIANZA DE CLASIFICACION: {pct}% (fiable). "
            "Puedes adaptar con firmeza el tono y la profundidad a las etiquetas."
        )
    return (
        f"CONFIANZA DE CLASIFICACION: {pct}% (incierta). "
        "No asumas extremos emocionales o de nivel; prioriza claridad, "
        "ofrece una reformulacion breve si la pregunta es ambigua."
    )


def _head_uncertainty_notes(
    metadata: ClassificationMetadata,
    heads: HeadConfidences | None,
) -> list[str]:
    if heads is None:
        return []

    notes: list[str] = []
    mapping: list[tuple[str, str, float]] = [
        ("nivel_tecnico", metadata.nivel_tecnico, heads.nivel_tecnico),
        ("urgencia", metadata.urgencia, heads.urgencia),
        ("emocion", metadata.emocion, heads.emocion),
        ("dominio", metadata.dominio, heads.dominio),
    ]
    for key, label, prob in mapping:
        if prob < HEAD_WEAK_THRESHOLD:
            human = HEAD_LABELS.get(key, key)
            notes.append(
                f"- {human} ({label}): probabilidad baja ({round(prob * 100)}%). "
                f"Trata esta dimension con cautela."
            )
    return notes


def _student_profile_block(metadata: ClassificationMetadata) -> str:
    pct = _confidence_percent(metadata.confianza)
    return f"""\
PERFIL DEL ESTUDIANTE (clasificacion local):
- Nivel tecnico: {metadata.nivel_tecnico}
- Urgencia: {metadata.urgencia}
- Emocion detectada: {metadata.emocion}
- Dominio: {metadata.dominio}
- Confianza global: {pct}%"""


def select_rules(
    metadata: ClassificationMetadata,
    heads: HeadConfidences | None = None,
) -> str:
    """Selecciona reglas por emocion, nivel, urgencia y dominio."""

    def pick(modifiers: dict[str, str], key: str, default: str) -> str:
        return modifiers.get(key, default)

    emotion = pick(EMOTION_MODIFIER, metadata.emocion, DEFAULT_EMOTION)
    level = pick(LEVEL_MODIFIER, metadata.nivel_tecnico, DEFAULT_LEVEL)
    urgency = pick(URGENCY_MODIFIER, metadata.urgencia, DEFAULT_URGENCY)
    domain = pick(DOMAIN_MODIFIER, metadata.dominio, DEFAULT_DOMAIN)

    if heads is not None:
        if heads.emocion < HEAD_WEAK_THRESHOLD:
            emotion = f"{emotion} (senal emocional debil: no exageres el tono.)"
        if heads.nivel_tecnico < HEAD_WEAK_THRESHOLD:
            level = f"{level} (nivel incierto: explica terminos clave.)"
        if heads.urgencia < HEAD_WEAK_THRESHOLD:
            urgency = f"{urgency} (urgencia incierta: prioriza claridad sobre brevedad extrema.)"
        if heads.dominio < HEAD_WEAK_THRESHOLD:
            domain = f"{domain} (dominio incierto: no asumas stack hasta que el usuario lo diga.)"

    return "\n".join(
        [
            f"REGLAS POR EMOCION: {emotion}",
            f"REGLAS POR NIVEL: {level}",
            f"REGLAS POR URGENCIA: {urgency}",
            f"REGLAS POR DOMINIO: {domain}",
        ]
    )


def build_output_format(metadata: ClassificationMetadata) -> str:
    """Plantilla de salida adaptada a urgencia y emocion."""

    urgent = metadata.urgencia == "alta"
    desperate = metadata.emocion in ("desesperado", "ansiedad")
    overwhelmed = metadata.emocion == "abrumado"
    curious = metadata.emocion == "curiosidad"
    low_urgency = metadata.urgencia == "baja"

    if urgent or desperate:
        structure = """\
FORMATO DE RESPUESTA (Markdown valido):
1. **Que hacer ahora** — hasta 3 pasos numerados, solucion practica primero.
2. **Por que funciona** — explicacion breve adaptada al nivel.
3. **Siguiente paso** — una accion concreta para continuar."""
    elif overwhelmed:
        structure = """\
FORMATO DE RESPUESTA (Markdown valido):
1. **Una idea clave** — una sola frase que ancle el concepto.
2. **Un paso** — una unica accion o ejemplo minimo (codigo corto si ayuda).
3. **Siguiente paso** — solo una cosa para hacer despues."""
    elif curious and low_urgency:
        structure = """\
FORMATO DE RESPUESTA (Markdown valido):
1. **Respuesta** — explicacion clara con ejemplo si aporta.
2. **Para profundizar** — recurso, analogia extra o mini-ejercicio opcional.
3. **Pregunta de seguimiento** — una pregunta que verifique comprension."""
    else:
        structure = """\
FORMATO DE RESPUESTA (Markdown valido):
1. **Diagnostico breve** — situacion o concepto en juego (validacion emocional si aplica).
2. **Explicacion o solucion** — listas, tablas o bloques ```idioma cuando ayuden.
3. **Siguiente paso** — accion concreta o pregunta guia para seguir aprendiendo."""

    return (
        f"{structure}\n"
        "Usa encabezados, listas y fences de codigo correctos. "
        "No inventes archivos ni APIs del proyecto del usuario."
    )


def build_system_prompt(
    metadata: ClassificationMetadata,
    head_confidences: HeadConfidences | None = None,
) -> str:
    """Construye el system prompt completo a partir de metadatos de la RN."""

    blocks = [
        IDENTITY_PROMPT,
        _student_profile_block(metadata),
        _confidence_policy(metadata.confianza),
    ]

    uncertainty = _head_uncertainty_notes(metadata, head_confidences)
    if uncertainty:
        blocks.append(
            "SEÑALES DE INCERTIDUMBRE POR CABEZA:\n" + "\n".join(uncertainty)
        )

    blocks.extend(
        [
            select_rules(metadata, head_confidences),
            PRIORITY_RULE,
            build_output_format(metadata),
        ]
    )

    return "\n\n".join(blocks)


def build_messages(request: ChatRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": build_system_prompt(request.metadata, request.head_confidences),
        }
    ]
    for item in request.historial:
        messages.append({"role": item.rol, "content": item.contenido})
    messages.append({"role": "user", "content": request.pregunta})
    return messages
