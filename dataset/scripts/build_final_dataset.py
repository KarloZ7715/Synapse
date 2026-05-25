#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
NN_SCRIPT_DIR = PROJECT_ROOT / "neural_network" / "scripts"
import sys
if str(NN_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(NN_SCRIPT_DIR))

from training_labels import DOMINIO, EMOCION, HEAD_KEYS, NIVEL_TECNICO, URGENCIA

PROCESSED_DIR = PROJECT_ROOT / "dataset" / "processed"
FINAL_DIR = PROJECT_ROOT / "dataset" / "final"
DEFAULT_EXTRA_SYNTHETIC = PROCESSED_DIR / "so_like_synthetic.json"

ACTIVE_DOMAINS_FINAL: Tuple[str, ...] = tuple(DOMINIO)
SYNTHETIC_FUENTE_FINAL = "synthetic_programming_final"

DOMAIN_MAP_FINAL = {
    "backend": "backend",
    "frontend": "frontend",
    "bases_de_datos": "bases_de_datos",
    "movil": "movil",
    "devops": "devops",
    "data_science": "data_science",
    "seguridad": "sistemas_seguridad",
    "sistemas": "sistemas_seguridad",
    "sistemas_seguridad": "sistemas_seguridad",
    "algoritmos": "general",
    "ingenieria_software": "general",
    "general": "general",
}

_TOKEN_RE = re.compile(r"\s+")
_LEAKED_LABEL_RE = re.compile(
    r"(?:\n|\s)*(?:etiquetas:\s*)?"
    r"(?:nivel_tecnico|urgencia|emocion|dominio)\s*[:=]\s*[^,\n]+"
    r"(?:[,\s]+(?:nivel_tecnico|urgencia|emocion|dominio)\s*[:=]\s*[^,\n]+)*\s*$",
    flags=re.IGNORECASE,
)
_LEAKED_TAGS_LABEL_RE = re.compile(
    r"(?:\n|\s)*tags:\s*"
    r"(?:nivel_tecnico|urgencia|emocion|dominio)\s*[:=][\s\S]*$",
    flags=re.IGNORECASE,
)
_LEAKED_LABEL_PREFIX_RE = re.compile(
    r"^\s*(?:etiquetas:\s*)?"
    r"(?:nivel_tecnico|urgencia|emocion|dominio)\s*[:=]\s*[^|\n,]+"
    r"(?:\s*[|,]\s*(?:nivel_tecnico|urgencia|emocion|dominio)\s*[:=]\s*[^|\n,]+)*"
    r"\s*\n+",
    flags=re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    return _TOKEN_RE.sub(" ", str(text).strip().lower())


def strip_leaked_label_footer(text: str) -> str:
    stripped = _LEAKED_LABEL_PREFIX_RE.sub("", str(text or "").strip()).strip()
    stripped = _LEAKED_TAGS_LABEL_RE.sub("", stripped).strip()
    cleaned_lines = []
    label_keys = ("nivel_tecnico", "urgencia", "emocion", "dominio")
    for line in stripped.splitlines():
        normalized = line.lower()
        key_hits = sum(1 for key in label_keys if key in normalized)
        if key_hits >= 2 and (":" in line or "=" in line):
            continue
        if normalized.strip().startswith("etiquetas:"):
            continue
        cleaned_lines.append(line)
    stripped = "\n".join(cleaned_lines).strip()
    return _LEAKED_LABEL_RE.sub("", stripped).strip()


def normalize_domain_final(domain: Any) -> str:
    raw = str(domain or "general").strip()
    return DOMAIN_MAP_FINAL.get(raw, "general")


def supervision_all() -> Dict[str, bool]:
    return {h: True for h in HEAD_KEYS}


def supervision_goe_emotion_only() -> Dict[str, bool]:
    return {h: h == "emocion" for h in HEAD_KEYS}


def label_or_none(row: Dict[str, Any], head: str) -> Optional[str]:
    value = row.get(head)
    if head == "dominio" and (value is None or not str(value).strip()):
        value = row.get("domain_synapse")
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def is_supervised(row: Dict[str, Any], head: str) -> bool:
    sup = row.get("supervision")
    if not isinstance(sup, dict):
        return True
    return bool(sup.get(head, True))


def infer_emotion_from_text(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ("urgente", "examen", "entrega", "produccion", "producción", "deadline")):
        return "ansiedad"
    if any(x in t for x in ("no entiendo", "confus", "perdid", "no se", "no sé")):
        return "confusion"
    if any(x in t for x in ("error", "no funciona", "falla", "frustr", "harto")):
        return "frustracion"
    if any(x in t for x in ("como funciona", "cómo funciona", "por que", "por qué", "diferencia")):
        return "curiosidad"
    if any(x in t for x in ("gracias", "logre", "logré", "funciono", "funcionó")):
        return "motivacion"
    return "neutral"


def so_text(row: Dict[str, Any]) -> str:
    title = str(row.get("title") or "").strip()
    body = str(row.get("body") or "").strip()
    if title and body:
        return f"{title}\n{body}"
    return title or body or str(row.get("texto") or "").strip()


def so_to_final_example(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = so_text(row)
    if not text:
        return None
    nivel = str(row.get("nivel_tecnico") or "intermedio").strip()
    urgencia = str(row.get("urgencia") or "media").strip()
    emocion = str(row.get("emocion") or infer_emotion_from_text(text)).strip()
    dominio = normalize_domain_final(row.get("dominio") or row.get("domain_synapse"))
    if nivel not in NIVEL_TECNICO:
        nivel = "intermedio"
    if urgencia not in URGENCIA:
        urgencia = "media"
    if emocion not in EMOCION:
        emocion = infer_emotion_from_text(text)
    return {
        "texto": text,
        "nivel_tecnico": nivel,
        "urgencia": urgencia,
        "emocion": emocion,
        "dominio": dominio,
        "fuente": "so_es",
        "source_id": f"so:{row.get('question_id') or row.get('source_id') or ''}",
        "supervision": supervision_all(),
    }


def goe_to_final_example(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = str(row.get("text") or row.get("texto") or "").strip()
    if len(text) < 8:
        return None
    emocion = str(row.get("emocion_synapse") or row.get("emocion") or "neutral").strip()
    if emocion not in EMOCION:
        emocion = "neutral"
    return {
        "texto": text,
        "nivel_tecnico": None,
        "urgencia": None,
        "emocion": emocion,
        "dominio": None,
        "fuente": "goemotions_es",
        "source_id": f"goe:{row.get('id') or row.get('source_id') or ''}",
        "emocion_original_goemotions": row.get("emocion_goemotions"),
        "supervision": supervision_goe_emotion_only(),
    }


DOMAIN_TOPICS = {
    "backend": ("API REST", "Django", "Node.js", "autenticacion", "colas de trabajo"),
    "frontend": ("React", "CSS", "estado de componentes", "formularios", "renderizado"),
    "bases_de_datos": ("SQL", "PostgreSQL", "indices", "joins", "migraciones"),
    "movil": ("Flutter", "Android", "notificaciones", "ciclo de vida", "permisos"),
    "devops": ("Docker", "Kubernetes", "CI/CD", "Nginx", "variables de entorno"),
    "data_science": ("pandas", "scikit-learn", "normalizacion", "metricas", "features"),
    "sistemas_seguridad": ("Linux", "concurrencia", "JWT", "permisos", "threads"),
    "general": ("programacion", "depuracion", "estructura del proyecto", "buenas practicas", "testing"),
}

EMOTION_STYLE = {
    "frustracion": ("ya probe varias alternativas y el fallo se repite", "me esta costando aislar la causa"),
    "confusion": ("no tengo claro que parte del flujo estoy interpretando mal", "me pierdo al conectar los conceptos"),
    "curiosidad": ("quiero entender el motivo tecnico antes de decidir", "me interesa comparar las opciones"),
    "ansiedad": ("esto bloquea una entrega cercana", "necesito destrabarlo con prioridad"),
    "motivacion": ("ya avance y quiero dejarlo mejor estructurado", "quiero aprovechar para hacerlo bien"),
    "abrumado": ("hay demasiadas rutas posibles y no se cual elegir", "la cantidad de conceptos me esta saturando"),
    "confiado": ("creo que el enfoque general es correcto", "tengo una hipotesis pero quiero validarla"),
    "desesperado": ("llevo mucho tiempo intentando y no logro avanzar", "cada cambio abre otro error distinto"),
    "neutral": ("busco una explicacion clara con un ejemplo", "quiero una respuesta directa y verificable"),
}

LEVEL_STYLE = {
    "principiante": ("necesito una explicacion paso a paso", "todavia estoy afianzando los fundamentos"),
    "intermedio": ("ya tengo una implementacion parcial", "puedo seguir codigo si me explican el criterio"),
    "avanzado": ("quiero analizar rendimiento, concurrencia o arquitectura", "me preocupan los efectos borde y la mantenibilidad"),
}

URGENCY_STYLE = {
    "baja": ("puedo revisarlo con calma", "no es bloqueante ahora mismo"),
    "media": ("quisiera resolverlo durante esta sesion", "me esta frenando el avance del dia"),
    "alta": ("bloquea una entrega o despliegue", "necesito una ruta de solucion pronto"),
}


APP_CONTEXTS = (
    "un panel administrativo", "una app de cursos", "un modulo de pagos", "un dashboard interno",
    "una API publica", "un sistema de inventario", "una practica universitaria", "un prototipo movil",
    "una tarea de simulacion", "un flujo de autenticacion", "una pantalla de reportes", "un job programado",
    "una integracion con terceros", "un formulario dinamico", "una migracion de datos", "un servicio de notificaciones",
    "un entorno de pruebas", "un despliegue pequeño", "una libreria compartida", "un repositorio heredado",
    "una consulta recurrente", "un componente reutilizable", "un endpoint nuevo", "una tarea de mantenimiento",
    "un pipeline de datos", "una vista responsive", "un monitor de errores", "una configuracion local",
    "un caso de permisos", "una coleccion de pruebas", "un flujo asincrono",
)

TECH_CONSTRAINTS = (
    "con pocos archivos", "sin cambiar demasiado la estructura", "manteniendo compatibilidad",
    "con logs incompletos", "con ejemplos pequenos", "sin depender de servicios externos",
    "cuidando los tiempos de respuesta", "con datos de prueba limitados", "evitando repetir codigo",
    "con validaciones estrictas", "sin romper lo que ya funciona", "con nombres poco claros",
    "con varias capas involucradas", "desde una rama de trabajo", "con errores intermitentes",
    "pensando en una entrega academica", "con configuracion compartida", "usando una version reciente",
    "con documentacion escasa", "con cambios minimos", "comparando dos alternativas",
    "probando primero en local", "revisando una traza larga", "con entradas de usuario",
    "con datos en español", "buscando una solucion reproducible", "separando responsabilidades",
    "con una restriccion de tiempo", "sin perder legibilidad", "con varios casos borde",
    "optimizando solo lo necesario", "con dependencias ya instaladas", "a partir de codigo existente",
)

SYNTHETIC_FAMILIES = (
    "short_question",
    "error_context",
    "academic_assignment",
    "production_bug",
    "conceptual_explanation",
    "comparison",
    "refactor_review",
    "debugging_trace",
    "architecture_decision",
    "minimal_repro",
)


def _pick(options: Tuple[str, ...], i: int, salt: int) -> str:
    return options[(i + salt) % len(options)]


def synthetic_text(i: int, nivel: str, urgencia: str, emocion: str, dominio: str, family: str) -> str:
    topic = _pick(DOMAIN_TOPICS[dominio], i, 3)
    level = _pick(LEVEL_STYLE[nivel], i // 3, 5)
    urgency = _pick(URGENCY_STYLE[urgencia], i // 5, 7)
    emotion = _pick(EMOTION_STYLE[emocion], i // 7, 11)
    app_context = _pick(APP_CONTEXTS, i, 13)
    constraint = _pick(TECH_CONSTRAINTS, i // 2, 17)
    tail = f"El contexto es {app_context}, {constraint}."
    if family == "short_question":
        return f"Tengo una duda de {dominio} con {topic}: {level}. {emotion}. {urgency}. {tail}"
    if family == "error_context":
        return f"Al trabajar con {topic} en {dominio}, aparece un comportamiento inesperado. {level}; {emotion}. {urgency}. {tail}"
    if family == "academic_assignment":
        return f"Para una practica necesito explicar {topic} dentro de {dominio}. {level}. {emotion}, y {urgency}. {tail}"
    if family == "production_bug":
        return f"En un flujo parecido a produccion, {topic} empezo a fallar en {dominio}. {urgency}. {emotion}. {level}. {tail}"
    if family == "conceptual_explanation":
        return f"Quiero entender como se relaciona {topic} con {dominio}. {level}; {emotion}. {urgency}. {tail}"
    if family == "comparison":
        return f"Estoy comparando dos enfoques para {topic} en {dominio}. {level}. {emotion}. {urgency}. {tail}"
    if family == "refactor_review":
        return f"Estoy revisando una solucion de {dominio} basada en {topic}. {level}; {urgency}; {emotion}. {tail}"
    if family == "debugging_trace":
        return f"Tengo trazas y sintomas alrededor de {topic} en {dominio}. {emotion}. {level}. {urgency}. {tail}"
    if family == "architecture_decision":
        return f"Debo decidir como organizar {topic} en un proyecto de {dominio}. {level}. {emotion}. {urgency}. {tail}"
    return f"Necesito un ejemplo minimo sobre {topic} en {dominio}. {level}. {urgency}. {emotion}. {tail}"


def generate_balanced_synthetic_rows(target_rows: int, seed: int = 42) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    niveles = list(NIVEL_TECNICO)
    urgencias = list(URGENCIA)
    emociones = list(EMOCION)
    dominios = list(ACTIVE_DOMAINS_FINAL)
    rows: List[Dict[str, Any]] = []
    offsets = [rng.randrange(10_000) for _ in range(5)]
    for i in range(max(0, target_rows)):
        nivel = niveles[(i + offsets[0]) % len(niveles)]
        urgencia = urgencias[((i // len(niveles)) + offsets[1]) % len(urgencias)]
        dominio = dominios[(i + offsets[3]) % len(dominios)]
        emocion = emociones[((i // len(dominios)) + offsets[2]) % len(emociones)]
        family = SYNTHETIC_FAMILIES[(i + offsets[4]) % len(SYNTHETIC_FAMILIES)]
        rows.append(
            {
                "texto": synthetic_text(i, nivel, urgencia, emocion, dominio, family),
                "nivel_tecnico": nivel,
                "urgencia": urgencia,
                "emocion": emocion,
                "dominio": dominio,
                "fuente": SYNTHETIC_FUENTE_FINAL,
                "source_id": f"syn:final:{seed}:{i}",
                "emocion_source_so": "curated_synthetic_final",
                "synthetic_provenance": {"generator": "diverse_template_final", "seed": seed, "index": i, "family": family},
                "supervision": supervision_all(),
            }
        )
    return rows


def dedupe_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for row in rows:
        text = str(row.get("texto") or "").strip()
        if not text:
            continue
        key = normalize_text(text)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def supervised_counts(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Counter[str]] = {h: Counter() for h in HEAD_KEYS}
    for row in rows:
        for head in HEAD_KEYS:
            if not is_supervised(row, head):
                continue
            label = label_or_none(row, head)
            if head == "dominio" and label is not None:
                label = normalize_domain_final(label)
            if label is not None:
                out[head][label] += 1
    return {h: dict(c) for h, c in out.items()}


def source_counts(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return dict(Counter(str(r.get("fuente") or "unknown") for r in rows))


def duplicate_report(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    keys = [normalize_text(str(r.get("texto") or "")) for r in rows]
    return {"total": len(keys), "unique": len(set(keys)), "duplicates": len(keys) - len(set(keys))}


def gate_thresholds(total_rows: int) -> Dict[str, int]:
    return {
        "full_min_per_label": min(400, max(1, int(total_rows * 0.05))),
        "split_min_per_label": min(80, max(1, int(total_rows * 0.0055))),
    }


def labels_for_head(head: str) -> Tuple[str, ...]:
    if head == "nivel_tecnico":
        return tuple(NIVEL_TECNICO)
    if head == "urgencia":
        return tuple(URGENCIA)
    if head == "emocion":
        return tuple(EMOCION)
    if head == "dominio":
        return tuple(ACTIVE_DOMAINS_FINAL)
    raise KeyError(head)


def gate_counts(counts: Dict[str, Dict[str, int]], min_per_label: int) -> Dict[str, Any]:
    detail: Dict[str, Dict[str, Any]] = {}
    passes = True
    for head in HEAD_KEYS:
        detail[head] = {}
        for label in labels_for_head(head):
            count = int(counts.get(head, {}).get(label, 0))
            ok = count >= min_per_label
            detail[head][label] = {"count": count, "min": min_per_label, "pass": ok}
            passes = passes and ok
    return {"passes": passes, "detail": detail}



def source_mix_gates(source_mix: Dict[str, float]) -> Dict[str, Any]:
    max_train = float(source_mix.get("max_train_synthetic_fraction", 0.70))
    max_eval = float(source_mix.get("max_eval_synthetic_fraction", 0.55))
    checks = {
        f"train_synthetic_fraction_le_{max_train:.2f}": source_mix.get("train_synthetic_fraction", 0.0) <= max_train,
        f"val_synthetic_fraction_le_{max_eval:.2f}": source_mix.get("val_synthetic_fraction", 0.0) <= max_eval,
        f"test_synthetic_fraction_le_{max_eval:.2f}": source_mix.get("test_synthetic_fraction", 0.0) <= max_eval,
    }
    return {"passes": all(checks.values()), "checks": checks}


def compute_quality_report_final(
    rows: Sequence[Dict[str, Any]],
    *,
    train_rows: Optional[Sequence[Dict[str, Any]]] = None,
    val_rows: Optional[Sequence[Dict[str, Any]]] = None,
    test_rows: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    total = len(rows)
    thresholds = gate_thresholds(total)
    counts = supervised_counts(rows)
    source_mix = {
        "all_synthetic_fraction": round(synthetic_fraction(rows), 6),
        **({"train_synthetic_fraction": round(synthetic_fraction(train_rows), 6)} if train_rows is not None else {}),
        **({"val_synthetic_fraction": round(synthetic_fraction(val_rows), 6)} if val_rows is not None else {}),
        **({"test_synthetic_fraction": round(synthetic_fraction(test_rows), 6)} if test_rows is not None else {}),
        **({"max_train_synthetic_fraction": 0.70, "max_eval_synthetic_fraction": 0.55} if train_rows is not None else {}),
    }
    full_gate = gate_counts(counts, thresholds["full_min_per_label"])
    source_gate = source_mix_gates(source_mix)
    split_gate_detail: Dict[str, Any] = {}
    split_passes = True
    for name, subset in (("train", train_rows), ("val", val_rows), ("test", test_rows)):
        if subset is None:
            continue
        min_label = thresholds["split_min_per_label"]
        g = gate_counts(supervised_counts(subset), min_label)
        split_gate_detail[name] = g
        split_passes = split_passes and bool(g["passes"])
    return {
        "total_rows": total,
        "sources": source_counts(rows),
        "counts": counts,
        "duplicates": duplicate_report(rows),
        "source_mix": source_mix,
        "thresholds": thresholds,
        "gates": {
            "full": full_gate,
            "splits": {"passes": split_passes, "detail": split_gate_detail},
            "source_mix": source_gate,
            "all_pass": bool(
                full_gate["passes"]
                and split_passes
                and source_gate["passes"]
                and duplicate_report(rows)["duplicates"] == 0
            ),
        },
    }



def _row_has_label(row: Dict[str, Any], head: str, label: str) -> bool:
    if not is_supervised(row, head):
        return False
    value = label_or_none(row, head)
    if head == "dominio" and value is not None:
        value = normalize_domain_final(value)
    return value == label


def _can_give_row_without_breaking(
    row: Dict[str, Any],
    split_counts: Dict[str, Dict[str, int]],
    min_per_label: int,
) -> bool:
    for head in HEAD_KEYS:
        if not is_supervised(row, head):
            continue
        value = label_or_none(row, head)
        if value is None:
            continue
        if head == "dominio":
            value = normalize_domain_final(value)
        if split_counts.get(head, {}).get(value, 0) <= min_per_label:
            return False
    return True


def _repair_split_support(
    train: List[Dict[str, Any]],
    subset: List[Dict[str, Any]],
    *,
    min_per_label: int,
    max_synthetic_fraction: float,
) -> None:
    changed = True
    while changed:
        changed = False
        counts = supervised_counts(subset)
        for head in HEAD_KEYS:
            for label in labels_for_head(head):
                if counts.get(head, {}).get(label, 0) >= min_per_label:
                    continue
                at_synth_cap = synthetic_fraction(subset) >= max_synthetic_fraction
                donor_idx = next(
                    (
                        i
                        for i, r in enumerate(train)
                        if _row_has_label(r, head, label)
                        and (not at_synth_cap or not is_synthetic_row(r))
                    ),
                    None,
                )
                if donor_idx is None:
                    donor_idx = next((i for i, r in enumerate(train) if _row_has_label(r, head, label)), None)
                if donor_idx is None:
                    continue
                donor = train[donor_idx]
                split_counts = supervised_counts(subset)
                receiver_candidates = [
                    i for i, r in enumerate(subset) if _can_give_row_without_breaking(r, split_counts, min_per_label)
                ]
                if not receiver_candidates:
                    continue
                if not is_synthetic_row(donor):
                    receiver_idx = next((i for i in receiver_candidates if is_synthetic_row(subset[i])), receiver_candidates[0])
                else:
                    receiver_idx = next((i for i in receiver_candidates if not is_synthetic_row(subset[i])), receiver_candidates[0])
                receiver = subset[receiver_idx]
                next_synth = sum(1 for r in subset if is_synthetic_row(r)) - int(is_synthetic_row(receiver)) + int(is_synthetic_row(donor))
                if next_synth / len(subset) > max_synthetic_fraction:
                    continue
                train.pop(donor_idx)
                subset.pop(receiver_idx)
                train.append(receiver)
                subset.append(donor)
                changed = True
                break
            if changed:
                break


def is_synthetic_row(row: Dict[str, Any]) -> bool:
    source = str(row.get("fuente") or "")
    return source == SYNTHETIC_FUENTE_FINAL or source.startswith("synthetic_")


def synthetic_fraction(rows: Sequence[Dict[str, Any]]) -> float:
    return (sum(1 for r in rows if is_synthetic_row(r)) / len(rows)) if rows else 0.0


def _limit_synthetic_fraction(
    train: List[Dict[str, Any]],
    subset: List[Dict[str, Any]],
    *,
    max_fraction: float,
) -> None:
    while subset and synthetic_fraction(subset) > max_fraction:
        synth_idx = next((i for i, r in enumerate(subset) if is_synthetic_row(r)), None)
        real_idx = next((i for i, r in enumerate(train) if not is_synthetic_row(r)), None)
        if synth_idx is None or real_idx is None:
            break
        synth = subset.pop(synth_idx)
        real = train.pop(real_idx)
        subset.append(real)
        train.append(synth)

def split_rows_final(
    rows: Sequence[Dict[str, Any]],
    *,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    max_eval_synthetic_frac: float = 0.35,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not 0 < train_ratio < 1 or not 0 < val_ratio < 1 or train_ratio + val_ratio >= 1:
        raise ValueError("Invalid split ratios")
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(round(n * train_ratio))
    n_val = int(round(n * val_ratio))
    train: List[Dict[str, Any]] = []
    val: List[Dict[str, Any]] = []
    test: List[Dict[str, Any]] = []
    val_slots = max(1, int(round(20 * val_ratio)))
    test_slots = max(1, 20 - int(round(20 * train_ratio)) - val_slots)
    train_cut = 20 - val_slots - test_slots
    val_cut = train_cut + val_slots
    for i, row in enumerate(shuffled):
        slot = i % 20
        if slot < train_cut:
            train.append(row)
        elif slot < val_cut:
            val.append(row)
        else:
            test.append(row)
    _limit_synthetic_fraction(train, val, max_fraction=max_eval_synthetic_frac)
    _limit_synthetic_fraction(train, test, max_fraction=max_eval_synthetic_frac)
    min_split = gate_thresholds(len(rows))["split_min_per_label"]
    _repair_split_support(train, val, min_per_label=min_split, max_synthetic_fraction=max_eval_synthetic_frac)
    _repair_split_support(train, test, min_per_label=min_split, max_synthetic_fraction=max_eval_synthetic_frac)
    return train, val, test


def load_json_array(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return [r for r in data if isinstance(r, dict)]


def load_real_rows_final(
    *,
    labeled_path: Path,
    goemotions_path: Path,
    seed: int,
    max_goemotions: int,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    rows: List[Dict[str, Any]] = []

    if labeled_path.exists():
        for raw in load_json_array(labeled_path):
            ex = so_to_final_example(raw)
            if ex is not None:
                rows.append(ex)

    if goemotions_path.exists() and max_goemotions > 0:
        goe = load_json_array(goemotions_path)
        rng.shuffle(goe)
        picked = 0
        for raw in goe:
            if picked >= max_goemotions:
                break
            ex = goe_to_final_example(raw)
            if ex is not None:
                rows.append(ex)
                picked += 1

    return dedupe_rows(rows)


def extra_synthetic_to_final_example(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = strip_leaked_label_footer(str(row.get("texto") or row.get("text") or "").strip())
    if len(text) < 20:
        return None
    nivel = str(row.get("nivel_tecnico") or "").strip()
    urgencia = str(row.get("urgencia") or "").strip()
    emocion = str(row.get("emocion") or "").strip()
    dominio = normalize_domain_final(row.get("dominio") or row.get("domain_synapse"))
    if nivel not in NIVEL_TECNICO or urgencia not in URGENCIA or emocion not in EMOCION:
        return None
    return {
        "texto": text,
        "nivel_tecnico": nivel,
        "urgencia": urgencia,
        "emocion": emocion,
        "dominio": dominio,
        "fuente": str(row.get("fuente") or "synthetic_so_like"),
        "source_id": str(row.get("source_id") or f"extra:{abs(hash(text))}"),
        "synthetic_provenance": row.get("synthetic_provenance") or {"generator": "external_so_like"},
        "supervision": supervision_all(),
    }


def load_extra_synthetic_rows(path: Optional[Path]) -> List[Dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows = []
    for raw in load_json_array(path):
        ex = extra_synthetic_to_final_example(raw)
        if ex is not None:
            rows.append(ex)
    return dedupe_rows(rows)


def auto_target_rows_from_real(
    real_rows_count: int,
    *,
    default_target_rows: int,
    max_target_rows: int,
    train_ratio: float,
    val_ratio: float,
    max_train_synthetic_frac: float = 0.70,
    max_eval_synthetic_frac: float = 0.55,
) -> int:
    """Largest safe dataset size for the current real/synthetic split gates.

    With a 70/15/15 split, synthetic capacity is the weighted sum of the train
    cap and eval caps. The small epsilon avoids choosing a target that only
    passes due to rounding.
    """
    if real_rows_count <= 0:
        return default_target_rows
    test_ratio = 1.0 - train_ratio - val_ratio
    if train_ratio <= 0 or val_ratio <= 0 or test_ratio <= 0:
        return default_target_rows
    synthetic_capacity = (
        train_ratio * max_train_synthetic_frac
        + (val_ratio + test_ratio) * max_eval_synthetic_frac
    )
    required_real_fraction = max(0.01, 1.0 - synthetic_capacity + 0.005)
    safe_target = int(real_rows_count / required_real_fraction)
    return max(default_target_rows, min(max_target_rows, safe_target))


def build_final_dataset(
    *,
    labeled_path: Path,
    goemotions_path: Path,
    target_rows: int,
    seed: int,
    max_goemotions: int,
    synthetic_rows: Optional[int],
    extra_synthetic_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    rows = load_real_rows_final(
        labeled_path=labeled_path,
        goemotions_path=goemotions_path,
        seed=seed,
        max_goemotions=max_goemotions,
    )
    rows.extend(load_extra_synthetic_rows(extra_synthetic_path))
    rows = dedupe_rows(rows)
    n_synth = synthetic_rows if synthetic_rows is not None else max(0, target_rows - len(rows))
    if n_synth > 0:
        rows.extend(generate_balanced_synthetic_rows(n_synth, seed=seed))
    rows = dedupe_rows(rows)

    if len(rows) > target_rows:
        real = [r for r in rows if not is_synthetic_row(r)]
        synth = [r for r in rows if is_synthetic_row(r)]
        keep_real = real[: min(len(real), target_rows)]
        keep_synth = synth[: max(0, target_rows - len(keep_real))]
        rows = keep_real + keep_synth
    elif len(rows) < target_rows:
        rows.extend(generate_balanced_synthetic_rows(target_rows - len(rows), seed=seed + 1_000_003))
        rows = dedupe_rows(rows)
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Synapse dataset final.")
    parser.add_argument("--labeled", type=Path, default=PROCESSED_DIR / "labeled.json")
    parser.add_argument("--goemotions", type=Path, default=PROCESSED_DIR / "goemotions_mapped.json")
    parser.add_argument("--out-dir", type=Path, default=FINAL_DIR)
    parser.add_argument("--target-rows", type=int, default=10000)
    parser.add_argument("--auto-target-rows", action="store_true")
    parser.add_argument("--max-target-rows", type=int, default=12000)
    parser.add_argument("--max-goemotions", type=int, default=1800)
    parser.add_argument("--extra-synthetic", type=Path, default=DEFAULT_EXTRA_SYNTHETIC)
    parser.add_argument("--synthetic-rows", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train", type=float, default=0.70)
    parser.add_argument("--val", type=float, default=0.15)
    parser.add_argument("--max-eval-synthetic-frac", type=float, default=0.55)
    parser.add_argument("--strict-gates", action="store_true")
    args = parser.parse_args()

    target_rows = args.target_rows
    if args.auto_target_rows:
        real_rows = load_real_rows_final(
            labeled_path=args.labeled,
            goemotions_path=args.goemotions,
            seed=args.seed,
            max_goemotions=args.max_goemotions,
        )
        target_rows = auto_target_rows_from_real(
            len(real_rows),
            default_target_rows=args.target_rows,
            max_target_rows=args.max_target_rows,
            train_ratio=args.train,
            val_ratio=args.val,
            max_eval_synthetic_frac=args.max_eval_synthetic_frac,
        )
        print(f"Auto target rows: real={len(real_rows)} target={target_rows}")

    rows = build_final_dataset(
        labeled_path=args.labeled,
        goemotions_path=args.goemotions,
        target_rows=target_rows,
        seed=args.seed,
        max_goemotions=args.max_goemotions,
        synthetic_rows=args.synthetic_rows,
        extra_synthetic_path=args.extra_synthetic,
    )
    train, val, test = split_rows_final(
        rows,
        seed=args.seed,
        train_ratio=args.train,
        val_ratio=args.val,
        max_eval_synthetic_frac=args.max_eval_synthetic_frac,
    )
    report = compute_quality_report_final(rows, train_rows=train, val_rows=val, test_rows=test)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "dataset.json", rows)
    write_json(args.out_dir / "train.json", train)
    write_json(args.out_dir / "val.json", val)
    write_json(args.out_dir / "test.json", test)
    write_json(args.out_dir / "quality_report.json", report)
    write_json(
        args.out_dir / "split_meta.json",
        {
            "source": str(args.out_dir / "dataset.json"),
            "seed": args.seed,
            "target_rows": target_rows,
            "auto_target_rows": bool(args.auto_target_rows),
            "train": len(train),
            "val": len(val),
            "test": len(test),
            "max_eval_synthetic_frac": args.max_eval_synthetic_frac,
            "stratify_note": "source-aware deterministic split; gates verify per-head support",
        },
    )

    print(f"Escrito {args.out_dir / 'dataset.json'} ({len(rows)} ejemplos)")
    print(f"Fuentes: {report['sources']}")
    print(f"Gates all_pass={report['gates']['all_pass']}")
    if args.strict_gates and not report["gates"]["all_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
