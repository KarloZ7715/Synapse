#!/usr/bin/env python3
"""Etiquetas oficiales Synapse (orden fijo para índices de clase)."""

# Una etiqueta por dimensión por ejemplo (multi-task single-label).

NIVEL_TECNICO = ("principiante", "intermedio", "avanzado")

URGENCIA = ("baja", "media", "alta")

EMOCION = (
    "frustracion",
    "confusion",
    "curiosidad",
    "ansiedad",
    "motivacion",
    "abrumado",
    "confiado",
    "desesperado",
    "neutral",
)

# Taxonomia final colapsada para evitar clases con soporte casi nulo.
DOMINIO = (
    "backend",
    "frontend",
    "bases_de_datos",
    "movil",
    "devops",
    "data_science",
    "sistemas_seguridad",
    "general",
)

LABEL_SPECS = {
    "nivel_tecnico": NIVEL_TECNICO,
    "urgencia": URGENCIA,
    "emocion": EMOCION,
    "dominio": DOMINIO,
}

# Orden fijo de cabezas multitarea (dataset + entrenamiento).
HEAD_KEYS: tuple[str, ...] = ("nivel_tecnico", "urgencia", "emocion", "dominio")

# Índice ignorado en CrossEntropyLoss cuando una fila no supervisa esa cabeza.
IGNORE_LABEL_INDEX = -100


def class_counts() -> dict[str, int]:
    return {k: len(v) for k, v in LABEL_SPECS.items()}


def label_to_idx_maps() -> dict[str, dict[str, int]]:
    return {k: {lab: i for i, lab in enumerate(v)} for k, v in LABEL_SPECS.items()}
