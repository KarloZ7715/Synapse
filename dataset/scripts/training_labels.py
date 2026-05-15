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

# Alineado con dataset-plan / extract_so (11 dominios).
DOMINIO = (
    "backend",
    "frontend",
    "devops",
    "algoritmos",
    "bases_de_datos",
    "movil",
    "data_science",
    "seguridad",
    "sistemas",
    "ingenieria_software",
    "general",
)

LABEL_SPECS = {
    "nivel_tecnico": NIVEL_TECNICO,
    "urgencia": URGENCIA,
    "emocion": EMOCION,
    "dominio": DOMINIO,
}


def class_counts() -> dict[str, int]:
    return {k: len(v) for k, v in LABEL_SPECS.items()}


def label_to_idx_maps() -> dict[str, dict[str, int]]:
    return {k: {lab: i for i, lab in enumerate(v)} for k, v in LABEL_SPECS.items()}
