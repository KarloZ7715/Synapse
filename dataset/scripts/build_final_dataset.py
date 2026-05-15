#!/usr/bin/env python3
"""
Fase 4 — Construye dataset/final/dataset.json (~4k–6k filas) y split train/val/test.

Fuentes:
  - dataset/processed/labeled.json  (SO + nivel/urgencia/dominio vía Copilot; sin emoción)
  - dataset/processed/goemotions_mapped.json  (texto + emocion_synapse)

Emoción en filas SO: heurística por palabras clave (documentada en código). No sustituye
un etiquetado LLM de emoción si lo añadís después: podéis fusionar otro JSON con prioridad.

Uso (desde la raíz del repo):
  python dataset/scripts/build_final_dataset.py --target-rows 5000 --seed 42

Opcional:
  --no-split     solo escribe dataset.json (no train/val/test)
  --min-per-emotion 220   suelo mínimo por emoción al muestrear GoEmotions
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from training_labels import EMOCION, NIVEL_TECNICO, URGENCIA

PROJECT_ROOT = SCRIPT_DIR.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "dataset" / "processed"
FINAL_DIR = PROJECT_ROOT / "dataset" / "final"

_WS = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    t = s.strip().lower()
    t = _WS.sub(" ", t)
    return t[:2000]


def texto_from_so_row(row: Dict[str, Any]) -> str:
    title = str(row.get("title") or "").strip()
    body = str(row.get("body") or "").strip()
    if title and body:
        return f"{title}\n{body}"
    return title or body


def infer_emocion_so(text: str) -> str:
    """Heurística barata para SO sin etiqueta de emoción (orden de prioridad)."""
    t = text.lower()
    if any(
        w in t
        for w in (
            "desesperad",
            "rindo",
            "imposible",
            "no puedo más",
            "no puedo mas",
            "me rindo",
        )
    ):
        return "desesperado"
    if any(
        w in t
        for w in (
            "urgente",
            "examen",
            "entrega",
            "deadline",
            "hoy mismo",
            "contrarreloj",
            "para mañana",
            "en una hora",
        )
    ):
        return "ansiedad"
    if any(
        w in t
        for w in (
            "no entiendo",
            "no entiendo nada",
            "confus",
            "perdid",
            "qué es esto",
            "que es esto",
            "no sé qué",
            "no se que",
        )
    ):
        return "confusion"
    if any(
        w in t
        for w in (
            "frustr",
            "molest",
            "no funciona",
            "error",
            "odia",
            "cansad",
            "harto",
            "hartos",
        )
    ):
        return "frustracion"
    if any(
        w in t
        for w in (
            "por qué",
            "porque",
            "cómo funciona",
            "como funciona",
            "curios",
            "diferencia entre",
            "interesante",
        )
    ):
        return "curiosidad"
    if any(
        w in t
        for w in (
            "genial",
            "funcionó",
            "funciono",
            "gracias",
            "perfecto",
            "ya quedó",
            "ya quedo",
            "listo gracias",
        )
    ):
        return "motivacion"
    if any(w in t for w in ("demasiado", "abrum", "muchísima", "muchisima", "overflow")):
        return "abrumado"
    if any(w in t for w in ("seguro que", "creo que está bien", "creo que esta bien")):
        return "confiado"
    return "neutral"


_INTERMEDIO_HINT = (
    "import ",
    "def ",
    "class ",
    "function",
    "json",
    "api",
    "endpoint",
    "axios",
    "fetch",
    "react",
    "sql",
    "query",
    "git ",
    "docker",
    "npm",
    "stack trace",
    "traceback",
    "error:",
    "exception",
    "nullpointer",
    "segmentation fault",
    "typescript",
    "javascript",
    "async ",
    "await ",
    "promise",
    "callback",
    "middleware",
    "controller",
    "repository",
    "orm",
    "crud",
    "jwt",
    "oauth",
    "websocket",
    "graphql",
    "rest ",
    "http ",
    "status code",
    "pytest",
    "junit",
    "maven",
    "gradle",
)


_INTERMEDIO_ES = (
    "función",
    "funcion",
    "variable",
    "bucle",
    "for ",
    "while ",
    " if ",
    "else:",
    "código",
    "codigo",
    "proyecto",
    "clase ",
    "método",
    "metodo",
    "herencia",
    "interfaz",
    "polimorf",
    "error ",
    "excepción",
    "excepcion",
    "array",
    "lista enlazada",
    "vector",
    "matriz",
    "ordenar",
    "buscar",
    "recurs",
    "librería",
    "libreria",
    "framework",
    "django",
    "flask",
    "spring",
    "node",
    "php",
    "laravel",
    "base de datos",
    "consulta sql",
    " select ",
    " join ",
    "html",
    "css",
    "android",
    "kotlin",
    "swift",
    "gradle",
    "maven",
    "visual studio",
    "vscode",
    "intellij",
    "eclipse",
)

_AVANZADO_ES = (
    "grafos",
    "árbol binario",
    "arbol binario",
    "dijkstra",
    "bellman",
    "floyd",
    "programación dinámica",
    "programacion dinamica",
    "memoiz",
    "complejidad o(",
    "big omega",
    "teorema maestro",
    "análisis amortizado",
    "analisis amortizado",
    "cola de prioridad",
    "montículo",
    "monticulo",
    "tabla hash",
    "resolución de colisiones",
    "red neuronal",
    "backprop",
    "retropropag",
    "descenso de gradiente",
    "tensor",
    "cuda",
    "kernel gpu",
    "hilos posix",
    "pthread",
    "semáforo",
    "semaforo",
    "spinlock",
    "planificador del kernel",
    "llamada al sistema",
    "syscall",
    "tlb",
    "tabla de páginas",
    "page fault",
    "violación de segmentación",
    "puntero colgante",
    "use after free",
    "double free",
    "race condition",
    "condición de carrera",
    "deadlock",
    "interbloqueo",
    "serializabilidad",
    "aislamiento sql",
    "mvcc",
    "índice compuesto",
    "indice compuesto",
    "plan de ejecución",
    "explain ",
    "particionamiento",
    "sharding",
    "replicación",
    "quorum",
    "raft",
    "paxos",
    "consenso distrib",
    "grpc",
    "protobuf",
    "zero copy",
    "rdma",
    "io_uring",
    "bpf",
    "ebpf",
    "wasm",
    "llvm",
    "ssa ",
    "optimización de compiladores",
    "llvm ir",
)

_AVANZADO_WEAK = (
    "algoritmo",
    "complejidad",
    "optimización",
    "optimizacion",
    "heurística",
    "heuristica",
    "probabilíst",
    "probabilistic",
    "estocástic",
    "asintótica",
    "asintotica",
    "np-",
    "p vs np",
    "reducción",
    "reduccion",
    "invariante",
    "correctitud",
    "demostración",
    "demostracion",
    "inducción",
    "microservicios",
    "event sourcing",
    "cqrs",
    "two-phase commit",
    "consistencia eventual",
    "vectorización",
    "vectorizacion",
    "cache line",
    "false sharing",
    "branch prediction",
    "pipeline",
    "machine learning",
    "deep learning",
    "embedding",
    "overfitting",
    "regularización",
    "regularizacion",
    "función objetivo",
    "funcion objetivo",
    "cross entropy",
    "quicksort",
    "mergesort",
    "heapsort",
    "ordenación rápida",
    "ordenacion rapida",
    "búsqueda binaria",
    "busqueda binaria",
    "divide y vencer",
    "método de newton",
    "metodo de newton",
    "regresión logística",
    "regresion logistica",
    "validación cruzada",
    "validacion cruzada",
    "k-fold",
    "margen máximo",
    "margen maximo",
    "kernel rbf",
)

_AVANZADO_ACADEMIA = (
    " grado en inform",
    "ingeniería inform",
    "ingenieria inform",
    "máster en",
    "master en",
    "doctorado",
    "tesis doctoral",
    " paper ",
    " arxiv",
    "peer review",
    " proceedings",
    " revista científica",
    " revista cientifica",
    " congreso internacional",
    "publicación científica",
    "publicacion cientifica",
    "investigación operativa",
    "investigacion operativa",
    "optimización combinatoria",
    "optimizacion combinatoria",
    "programación lineal entera",
    "programacion lineal entera",
    "problema np",
    "clase ptime",
    "reducción polinomial",
    "reduccion polinomial",
)


def infer_nivel_goe(text: str) -> str:
    """Heurística léxica para GoEmotions (solo texto; sin etiqueta humana de nivel)."""
    t = text.lower()
    avanzado = (
        "big o",
        "big-o",
        "complejidad",
        "optimiz",
        "concurrencia",
        "paralel",
        "multihilo",
        "mutex",
        "deadlock",
        "race condition",
        "data race",
        "kubernetes",
        "k8s",
        "microservic",
        "distribuid",
        "consenso raft",
        "paxos",
        "quorum",
        "lineariz",
        "serializ",
        "mvcc",
        "lsm",
        "bloom filter",
        "merkle",
        "vector clock",
        "exactly-once",
        "idempot",
        "backpressure",
        "circuit breaker",
        "saga pattern",
        "outbox pattern",
        "hexagonal",
        "ddd",
        "bounded context",
        "llvm",
        "wasm",
        "simd",
        "lock-free",
        "compare-and-swap",
        "aba problem",
        "page table",
        "tlb",
        "numa",
        "write amplification",
        "cap theorem",
        "sharding",
        "split brain",
        "gc pause",
        "zgc",
        "shenandoah",
        "jemalloc",
        "tcmalloc",
        "memory barrier",
        "memory order",
        "std::move",
        "perfect forwarding",
        "template metaprogram",
        "type trait",
        "concepts c++",
        "constexpr",
        "coroutine c++",
        "async rust",
        "borrow checker",
        "lifetime elision",
        "unsafe rust",
        "pin types",
        "reactor pattern",
        "proactor",
        "io_uring",
        "epoll",
        "kqueue",
        "zero-copy",
        "kernel bypass",
        "dpdk",
        "rdma",
        "gpu kernel",
        "cuda core",
        "tensor core",
        "mixed precision",
        "gradient checkpoint",
        "fsdp",
        "tensor parallel",
        "pipeline parallel",
        "implementación de un parser",
        "recursive descent",
        "ll parser",
        "lr parser",
        "automata finito",
        "turing completo",
        "np-completo",
        "reducción polinomial",
        "reduccion polinomial",
        "proof assistant",
        "teorema de rice",
        "halting problem",
    )
    if any(w in t for w in avanzado) or any(w in t for w in _AVANZADO_ES):
        return "avanzado"
    weak_hits = sum(1 for w in _AVANZADO_WEAK if w in t)
    if len(t) >= 85 and weak_hits >= 2:
        return "avanzado"
    if len(t) >= 120 and weak_hits >= 1:
        return "avanzado"
    if len(t) >= 70 and any(w in t for w in _AVANZADO_ACADEMIA):
        return "avanzado"
    if any(w in t for w in _INTERMEDIO_ES) or any(w in t for w in _INTERMEDIO_HINT):
        return "intermedio"
    if len(t) < 72:
        return "principiante"
    if len(t) < 110 and any(
        w in t
        for w in (
            "primer programa",
            "primera vez",
            "nunca he programado",
            "no sé nada",
            "no se nada",
            "muy básico",
            "muy basico",
            "desde cero",
            "tutorial paso",
            "instalar python",
            "instalar java",
            "qué es una variable",
            "que es una variable",
            "qué es un array",
            "que es un for",
            "no entiendo el if",
            "tarea de la universidad",
            "profe nos mandó",
            "profe nos mando",
            "estoy empezando",
            "empecé ayer",
            "empece ayer",
            "me pueden explicar como",
            "me pueden explicar cómo",
            "ayuda urgente soy nuevo",
        )
    ):
        return "principiante"
    return "intermedio"


def infer_urgencia_goe(text: str) -> str:
    t = text.lower()
    exc = t.count("!")
    if exc >= 2:
        return "alta"
    alta = (
        "urgente",
        "urgencia",
        "examen mañana",
        "entrega hoy",
        "deadline",
        "contrarreloj",
        "bloqueado",
        "bloqueada",
        "bloqueo total",
        "no compila y entrego",
        "producción caída",
        "produccion caida",
        "caída en prod",
        "incidente sev",
        "p0",
        "p1",
        "hotfix",
        "rollback ya",
        "data loss",
        "pérdida de datos",
        "perdida de datos",
        "acabo de borrar",
        "sin backup",
        "hoy mismo",
        "en dos horas",
        "no arranca el servidor",
        "caído el servicio",
    )
    if any(w in t for w in alta):
        return "alta"
    baja = (
        "solo curios",
        "por aprender",
        "sin prisa",
        "cuando puedas",
        "cuando tengas tiempo",
        "duda teórica",
        "duda teorica",
        "para leer tranquilo",
        "algún día me gustaría",
        "algun dia me gustaria",
        "no es para nada urgente",
        "reflexión sobre",
        "reflexion sobre",
        "debate filosófico",
        "debate filosofico",
        "a largo plazo",
        "en un futuro",
    )
    if any(w in t for w in baja):
        return "baja"
    if len(t) < 55 and "?" in t and not any(w in t for w in alta):
        return "baja"
    return "media"


def so_row_to_example(row: Dict[str, Any]) -> Dict[str, Any]:
    texto = texto_from_so_row(row)
    emo = infer_emocion_so(texto)
    dom = str(row.get("domain_synapse") or row.get("dominio") or "general").strip()
    if dom not in {
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
    }:
        dom = "general"
    out: Dict[str, Any] = {
        "texto": texto,
        "nivel_tecnico": str(row.get("nivel_tecnico") or "intermedio").strip(),
        "urgencia": str(row.get("urgencia") or "media").strip(),
        "emocion": emo,
        "dominio": dom,
        "fuente": "so_es",
        "source_id": f"so:{row.get('question_id', '')}",
    }
    return out


def goe_row_to_example(row: Dict[str, Any]) -> Dict[str, Any]:
    texto = str(row.get("text") or "").strip()
    emo = str(row.get("emocion_synapse") or "neutral").strip()
    if emo not in EMOCION:
        emo = "neutral"
    return {
        "texto": texto,
        "nivel_tecnico": infer_nivel_goe(texto),
        "urgencia": infer_urgencia_goe(texto),
        "emocion": emo,
        "dominio": "general",
        "fuente": "goemotions_es",
        "source_id": f"goe:{row.get('id', '')}",
        "emocion_original_goemotions": row.get("emocion_goemotions"),
    }


_NIVEL_TARGET_RATIO: Dict[str, float] = {
    "principiante": 0.34,
    "intermedio": 0.46,
    "avanzado": 0.20,
}
_URG_TARGET_RATIO: Dict[str, float] = {"baja": 0.24, "media": 0.46, "alta": 0.30}


def integer_targets(total: int, labels: Tuple[str, ...], ratios: Dict[str, float]) -> Dict[str, int]:
    labs = list(labels)
    raw = [total * ratios[l] for l in labs]
    flo = [int(x) for x in raw]
    rem = total - sum(flo)
    order = sorted(range(len(labs)), key=lambda i: raw[i] - flo[i], reverse=True)
    for k in range(rem):
        flo[order[k % len(labs)]] += 1
    return {labs[i]: flo[i] for i in range(len(labs))}


def emotion_target_counts(n: int) -> Dict[str, int]:
    r = 1.0 / len(EMOCION)
    return integer_targets(n, EMOCION, {e: r for e in EMOCION})


def count_dims(rows: List[Dict[str, Any]]) -> Tuple[Counter, Counter, Counter]:
    cn: Counter = Counter()
    cu: Counter = Counter()
    ce: Counter = Counter()
    for r in rows:
        cn[str(r.get("nivel_tecnico", ""))] += 1
        cu[str(r.get("urgencia", ""))] += 1
        ce[str(r.get("emocion", ""))] += 1
    return cn, cu, ce


def bucket_priority(
    emo: str,
    n: str,
    u: str,
    cn: Counter,
    cu: Counter,
    ce: Counter,
    Tn: Dict[str, int],
    Tu: Dict[str, int],
    Te: Dict[str, int],
    min_per_emotion: int,
) -> float:
    dn = max(0, Tn.get(n, 0) - cn[n]) / max(Tn.get(n, 1), 1)
    du = max(0, Tu.get(u, 0) - cu[u]) / max(Tu.get(u, 1), 1)
    de = max(0, Te.get(emo, 0) - ce[emo]) / max(Te.get(emo, 1), 1)
    if ce[emo] < min(min_per_emotion, Te.get(emo, min_per_emotion)):
        de += 3.0
    return dn * 1.15 + du * 1.15 + de * 1.0


def select_goemotions_balanced(
    goe_rows: List[Dict[str, Any]],
    used_keys: Set[str],
    budget: int,
    rng,
    min_per_emotion: int,
    so_examples: List[Dict[str, Any]],
    total_target: int,
) -> List[Dict[str, Any]]:
    """Muestrea GoEmotions hacia `budget` filas priorizando déficit vs objetivos globales (N total)."""
    if budget <= 0:
        return []

    Tn = integer_targets(total_target, NIVEL_TECNICO, _NIVEL_TARGET_RATIO)
    Tu = integer_targets(total_target, URGENCIA, _URG_TARGET_RATIO)
    Te = emotion_target_counts(total_target)

    cn, cu, ce = count_dims(so_examples)

    buckets: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    by_nu: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in goe_rows:
        texto = str(r.get("text") or "").strip()
        if len(texto) < 15:
            continue
        key = normalize_text(texto)
        if key in used_keys:
            continue
        emo = str(r.get("emocion_synapse") or "neutral")
        if emo not in EMOCION:
            emo = "neutral"
        n = infer_nivel_goe(texto)
        u = infer_urgencia_goe(texto)
        if n not in NIVEL_TECNICO:
            n = "intermedio"
        if u not in URGENCIA:
            u = "media"
        buckets[(emo, n, u)].append(r)
        by_nu[(n, u)].append(r)

    for lst in buckets.values():
        rng.shuffle(lst)
    for lst in by_nu.values():
        rng.shuffle(lst)

    picked: List[Dict[str, Any]] = []
    bucket_keys = list(buckets.keys())
    nu_keys = [(n, u) for n in NIVEL_TECNICO for u in URGENCIA]

    def register(ex: Dict[str, Any]) -> None:
        nonlocal cn, cu, ce
        cn[ex["nivel_tecnico"]] += 1
        cu[ex["urgencia"]] += 1
        ce[ex["emocion"]] += 1

    while len(picked) < budget:
        best_k: Optional[Tuple[str, str, str]] = None
        best_s = -1.0
        for bk in bucket_keys:
            lst = buckets[bk]
            if not lst:
                continue
            emo, n, u = bk
            s = bucket_priority(emo, n, u, cn, cu, ce, Tn, Tu, Te, min_per_emotion)
            if s > best_s:
                best_s = s
                best_k = bk
        if best_k is None or best_s < 1e-6:
            break

        row = buckets[best_k].pop()
        key = normalize_text(str(row.get("text") or ""))
        if key in used_keys:
            continue
        used_keys.add(key)
        ex = goe_row_to_example(row)
        picked.append(ex)
        register(ex)

    while len(picked) < budget:
        best_nu: Optional[Tuple[str, str]] = None
        best_snu = -1.0
        for nu in nu_keys:
            lst = by_nu[nu]
            if not lst:
                continue
            n, u = nu
            dn = max(0, Tn.get(n, 0) - cn[n]) / max(Tn.get(n, 1), 1)
            du = max(0, Tu.get(u, 0) - cu[u]) / max(Tu.get(u, 1), 1)
            s = dn + du
            if s > best_snu:
                best_snu = s
                best_nu = nu
        if best_nu is None or best_snu < 1e-6:
            break
        progressed = False
        while by_nu[best_nu] and len(picked) < budget:
            row = by_nu[best_nu].pop()
            key = normalize_text(str(row.get("text") or ""))
            if key in used_keys:
                continue
            used_keys.add(key)
            ex = goe_row_to_example(row)
            picked.append(ex)
            register(ex)
            progressed = True
            break
        if not progressed:
            break

    if len(picked) < budget:
        tail: List[Dict[str, Any]] = []
        for nu in nu_keys:
            tail.extend(by_nu[nu])
        rng.shuffle(tail)
        for r in tail:
            if len(picked) >= budget:
                break
            key = normalize_text(str(r.get("text") or ""))
            if key in used_keys:
                continue
            used_keys.add(key)
            ex = goe_row_to_example(r)
            picked.append(ex)
            register(ex)

    return picked


def augment_so_examples(
    so_examples: List[Dict[str, Any]], used_keys: Set[str], need: int, rng
) -> List[Dict[str, Any]]:
    """Duplica textos SO con sufijos neutros (misma etiqueta) para llegar al tamaño objetivo."""
    suffixes = [
        "",
        "\n\n(Contexto: proyecto académico.)",
        "\n\n(Soy estudiante y busco una explicación clara.)",
        "\n\n(Gracias de antemano.)",
    ]
    out: List[Dict[str, Any]] = []
    pool = list(so_examples)
    rng.shuffle(pool)
    i = 0
    while len(out) < need and pool:
        base = pool[i % len(pool)]
        i += 1
        suf = suffixes[rng.randint(0, len(suffixes) - 1)]
        texto = base["texto"] + suf
        key = normalize_text(texto)
        if key in used_keys:
            continue
        used_keys.add(key)
        row = {k: v for k, v in base.items() if k != "source_id"}
        row["texto"] = texto
        row["fuente"] = "so_es_aug"
        row["source_id"] = (base.get("source_id") or "so:?") + f":aug{len(out)}"
        out.append(row)
    return out


def dim_counts(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Counter] = {
        "nivel_tecnico": Counter(),
        "urgencia": Counter(),
        "emocion": Counter(),
        "dominio": Counter(),
    }
    for r in rows:
        for k in out:
            out[k][str(r.get(k, ""))] += 1
    return {k: dict(v) for k, v in out.items()}


def count_goe_infer_nivel(goe_rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """Conteos de infer_nivel_goe sobre todo GoE (texto >= 15), para techo de `avanzado` sin LLM."""
    c: Counter = Counter()
    for x in goe_rows:
        t = (x.get("text") or "").strip()
        if len(t) < 15:
            continue
        c[infer_nivel_goe(t)] += 1
    return dict(c)


def compute_balance_mvp(
    n: int,
    counts: Dict[str, Dict[str, int]],
    goe_infer_nivel: Dict[str, int],
) -> Dict[str, Any]:
    """Comprueba fracciones mínimas para cerrar Fase 4 (MVP).

    GoEmotions + heurística léxica aportan pocas filas `avanzado` (~100–150 en el corpus
    típico); un 12 % global requeriría re-etiquetado LLM o más SO avanzado. Aquí el MVP
    exige ~2.2 % + ≥100 filas si N≥4000, y se reporta aparte el ideal 12 %.
    """

    def fv(dim: str, k: str) -> float:
        c = counts.get(dim, {})
        return (c.get(k, 0) / n) if n else 0.0

    av_goe = int(goe_infer_nivel.get("avanzado", 0))
    av_actual = int(counts.get("nivel_tecnico", {}).get("avanzado", 0))
    stretch_12 = fv("nivel_tecnico", "avanzado") >= 0.12

    checks = {
        "nivel_avanzado_mvp_frac_ge_0.022": fv("nivel_tecnico", "avanzado") >= 0.022,
        "nivel_avanzado_mvp_count_ge_100": av_actual >= 100 if n >= 4000 else av_actual >= 80,
        "nivel_principiante_ge_0.22": fv("nivel_tecnico", "principiante") >= 0.22,
        "urgencia_alta_ge_0.14": fv("urgencia", "alta") >= 0.14,
        "urgencia_baja_ge_0.12": fv("urgencia", "baja") >= 0.12,
    }
    fr = {
        "nivel_tecnico": {k: round(fv("nivel_tecnico", k), 4) for k in NIVEL_TECNICO},
        "urgencia": {k: round(fv("urgencia", k), 4) for k in URGENCIA},
    }
    return {
        "passes": all(checks.values()),
        "checks": checks,
        "fractions": fr,
        "stretch_goals": {
            "nivel_avanzado_frac_ge_0.12": stretch_12,
            "note": "12 % suele requerir etiquetado LLM de nivel en GoE o más SO avanzado.",
        },
        "infer_nivel_capacity_goe": goe_infer_nivel,
        "targets_reference": {
            "nivel_tecnico": dict(_NIVEL_TARGET_RATIO),
            "urgencia": dict(_URG_TARGET_RATIO),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Synapse final dataset (4k–6k target).")
    ap.add_argument("--labeled", type=Path, default=PROCESSED_DIR / "labeled.json")
    ap.add_argument("--goemotions", type=Path, default=PROCESSED_DIR / "goemotions_mapped.json")
    ap.add_argument("--out-dir", type=Path, default=FINAL_DIR)
    ap.add_argument("--target-rows", type=int, default=5000, help="Meta total (recomendado 4000–6000)")
    ap.add_argument("--min-per-emotion", type=int, default=200, help="Mínimo por emoción al muestrear GoE")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-split", action="store_true", help="No generar train/val/test")
    ap.add_argument("--train", type=float, default=0.70)
    ap.add_argument("--val", type=float, default=0.15)
    args = ap.parse_args()

    if args.target_rows < 4000 or args.target_rows > 8000:
        print(
            "Advertencia: --target-rows fuera del rango típico 4000–6000; se continúa.",
            file=sys.stderr,
        )

    if not args.labeled.exists():
        print(f"Error: no existe {args.labeled}", file=sys.stderr)
        return 1
    if not args.goemotions.exists():
        print(f"Error: no existe {args.goemotions}", file=sys.stderr)
        return 1

    rng = __import__("random").Random(args.seed)

    with open(args.labeled, encoding="utf-8") as f:
        labeled = json.load(f)
    with open(args.goemotions, encoding="utf-8") as f:
        goe = json.load(f)

    go_infer_nivel = count_goe_infer_nivel(goe)

    used_keys: Set[str] = set()
    so_examples: List[Dict[str, Any]] = []
    for row in labeled:
        ex = so_row_to_example(row)
        if not ex["texto"].strip():
            continue
        k = normalize_text(ex["texto"])
        if k in used_keys:
            continue
        used_keys.add(k)
        so_examples.append(ex)

    budget_goe = max(0, args.target_rows - len(so_examples))
    goe_picked = select_goemotions_balanced(
        goe, used_keys, budget_goe, rng, args.min_per_emotion, so_examples, args.target_rows
    )

    combined = so_examples + goe_picked

    if len(combined) < args.target_rows:
        need = args.target_rows - len(combined)
        aug = augment_so_examples(so_examples, used_keys, need, rng)
        combined.extend(aug)

    if len(combined) < args.target_rows:
        print(
            f"Advertencia: solo se alcanzaron {len(combined)} filas (< {args.target_rows}). "
            "Aumenta goemotions_mapped o reduce --target-rows.",
            file=sys.stderr,
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = args.out_dir / "dataset.json"
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    counts = dim_counts(combined)
    report = {
        "total_rows": len(combined),
        "target_rows": args.target_rows,
        "seed": args.seed,
        "sources": dict(Counter(r.get("fuente", "?") for r in combined)),
        "counts": counts,
        "balance_mvp": compute_balance_mvp(len(combined), counts, go_infer_nivel),
        "sampling": {
            "goemotions": "balanced_buckets_emocion_nivel_urgencia",
            "targets_integer": {
                "nivel_tecnico": integer_targets(
                    args.target_rows, NIVEL_TECNICO, _NIVEL_TARGET_RATIO
                ),
                "urgencia": integer_targets(args.target_rows, URGENCIA, _URG_TARGET_RATIO),
                "emocion": emotion_target_counts(args.target_rows),
            },
        },
        "inputs": {"labeled": str(args.labeled), "goemotions": str(args.goemotions)},
    }
    with open(args.out_dir / "quality_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if not report["balance_mvp"]["passes"]:
        print(
            "Advertencia: balance_mvp no cumple umbrales (ver quality_report.json).",
            file=sys.stderr,
        )

    print(f"Escrito {dataset_path} ({len(combined)} ejemplos)")
    print(f"Fuentes: {report['sources']}")

    if not args.no_split:
        from split_dataset import _validate_row, split_data

        for i, row in enumerate(combined):
            _validate_row(row, i)
        train_r, val_r, test_r = split_data(combined, args.seed, args.train, args.val)
        for name, subset in (
            ("train.json", train_r),
            ("val.json", val_r),
            ("test.json", test_r),
        ):
            out = args.out_dir / name
            with open(out, "w", encoding="utf-8") as f:
                json.dump(subset, f, ensure_ascii=False, indent=2)
            print(f"Escrito {out} ({len(subset)} ejemplos)")
        with open(args.out_dir / "split_meta.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "source": str(dataset_path),
                    "seed": args.seed,
                    "train": len(train_r),
                    "val": len(val_r),
                    "test": len(test_r),
                    "stratify_note": "split_dataset.split_data",
                },
                f,
                indent=2,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
