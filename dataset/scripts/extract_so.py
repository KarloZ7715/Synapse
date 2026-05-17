#!/usr/bin/env python3
"""
Extraccion de preguntas de Stack Overflow ES.

Objetivos:
- Incluir cuerpo real de la pregunta (filter=withbody)
- Reducir sesgo por "top votos"
- Mejorar diversidad por dominio
- Mantener un presupuesto de llamadas API
- Emitir `dataset/raw/extraction_audit.json` con conteos por dominio, tags y señales urgent/advanced
"""

import argparse
import html
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _load_repo_dotenv() -> None:
    path = PROJECT_ROOT / ".env"
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key not in os.environ:
            os.environ[key] = val


_load_repo_dotenv()
RAW_DIR = PROJECT_ROOT / "dataset" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SITE = "es.stackoverflow"
BASE_URL = "https://api.stackexchange.com/2.3"
STACKEXCHANGE_KEY = os.getenv("STACKEXCHANGE_KEY", "").strip()

TAG_TO_DOMAIN = {
    "python": "backend",
    "javascript": "backend",
    "java": "backend",
    "php": "backend",
    "c#": "backend",
    "node.js": "backend",
    "spring": "backend",
    "spring-boot": "backend",
    "laravel": "backend",
    "go": "backend",
    "rust": "backend",
    "ruby": "backend",
    "react": "frontend",
    "vue.js": "frontend",
    "angular": "frontend",
    "css": "frontend",
    "html": "frontend",
    "svelte": "frontend",
    "nextjs": "frontend",
    "sql": "bases_de_datos",
    "mysql": "bases_de_datos",
    "postgresql": "bases_de_datos",
    "mongodb": "bases_de_datos",
    "redis": "bases_de_datos",
    "docker": "devops",
    "kubernetes": "devops",
    "aws": "devops",
    "gcp": "devops",
    "nginx": "devops",
    "ci/cd": "devops",
    "android": "movil",
    "ios": "movil",
    "flutter": "movil",
    "react-native": "movil",
    "swift": "movil",
    "kotlin": "movil",
    "pandas": "data_science",
    "numpy": "data_science",
    "scikit-learn": "data_science",
    "tensorflow": "data_science",
    "pytorch": "data_science",
    "sorting": "algoritmos",
    "algorithms": "algoritmos",
    "data-structures": "algoritmos",
    "recursion": "algoritmos",
    "graph-theory": "algoritmos",
    "security": "seguridad",
    "authentication": "seguridad",
    "encryption": "seguridad",
    "oauth": "seguridad",
    "jwt": "seguridad",
    "xss": "seguridad",
    "csrf": "seguridad",
    "tls": "seguridad",
    "penetration-testing": "seguridad",
    "os": "sistemas",
    "linux": "sistemas",
    "bash": "sistemas",
    "posix": "sistemas",
    "filesystem": "sistemas",
    "memory": "sistemas",
    "concurrency": "sistemas",
    "threads": "sistemas",
    "process": "sistemas",
    "design-patterns": "ingenieria_software",
    "testing": "ingenieria_software",
    "tdd": "ingenieria_software",
    "junit": "ingenieria_software",
    "refactoring": "ingenieria_software",
    "architecture": "ingenieria_software",
    "solid": "ingenieria_software",
    "git": "general",
    "typescript": "general",
}

DOMAIN_TO_TAGS = {
    "backend": ["python", "javascript", "java", "node.js", "spring", "php", "go"],
    "frontend": ["react", "css", "html", "vue.js", "angular", "typescript"],
    "bases_de_datos": ["sql", "mysql", "postgresql", "mongodb", "redis"],
    "devops": ["docker", "kubernetes", "aws", "nginx", "gcp"],
    "movil": ["android", "ios", "flutter", "react-native", "kotlin", "swift"],
    "data_science": ["pandas", "numpy", "scikit-learn", "tensorflow", "pytorch"],
    "algoritmos": ["algorithms", "data-structures", "recursion", "sorting", "graph-theory"],
    "seguridad": ["security", "authentication", "oauth", "encryption", "jwt", "xss", "csrf", "tls"],
    "sistemas": ["concurrency", "threads", "memory", "os", "linux", "bash", "posix"],
    "ingenieria_software": ["testing", "design-patterns", "architecture", "solid", "tdd", "junit", "refactoring"],
    "general": ["git"],
}

# Pisos algo mayores en dominios débiles (algoritmos/seguridad/sistemas/ingeniería) para no
# quedar siempre por debajo de COMBINED_MIN_TO_GATE_DOMAIN tras el build final.
DEFAULT_DOMAIN_MIN_QUOTA: Dict[str, int] = {
    "backend": 44,
    "frontend": 34,
    "bases_de_datos": 22,
    "devops": 22,
    "movil": 18,
    "data_science": 18,
    "algoritmos": 28,
    "seguridad": 26,
    "sistemas": 24,
    "ingenieria_software": 26,
    "general": 0,
}

URGENCY_TERMS = [
    "urgente",
    "ayuda",
    "bloqueado",
    "desesperado",
    "deadline",
    "entrega",
    "examen",
    "error",
]

ADVANCED_TERMS = [
    "complejidad",
    "big o",
    "optimiz",
    "concurrencia",
    "arquitectura",
    "patrones",
    "rendimiento",
    "escalabilidad",
]

ADVANCED_SEARCH_TERMS = [
    "concurrencia",
    "complejidad",
    "arquitectura",
    "rendimiento",
    "optimiz",
]

ADVANCED_SEARCH_TERMS_AGGRESSIVE_EXTRA = [
    "big-o",
    "mutex",
    "deadlock",
    "race condition",
    "complejidad temporal",
    "cache",
    "profiling",
    "escalabilidad",
]

LOW_URGENCY_SEARCH_TERMS = [
    "diferencia entre",
    "que es",
    "concepto",
    "tutorial",
    "aprender",
    "buenas practicas",
    "recomendacion",
    "solo curiosidad",
    "libro",
    "empezar con",
]

AGGRESSIVE_DOMAIN_MIN_QUOTA: Dict[str, int] = {
    "backend": 36,
    "frontend": 28,
    "bases_de_datos": 22,
    "devops": 22,
    "movil": 18,
    "data_science": 32,
    "algoritmos": 45,
    "seguridad": 42,
    "sistemas": 38,
    "ingenieria_software": 40,
    "general": 0,
}


class ApiBudget:
    def __init__(self, max_calls: int, sleep_seconds: float):
        self.max_calls = max_calls
        self.sleep_seconds = sleep_seconds
        self.calls = 0
        self.quota_remaining = None

    def can_call(self) -> bool:
        return self.calls < self.max_calls

    def mark_call(self, quota_remaining: Optional[int]) -> None:
        self.calls += 1
        if quota_remaining is not None:
            self.quota_remaining = quota_remaining


def get_domain_from_tags(tags: List[str]) -> str:
    counts: Dict[str, int] = {}
    for tag in tags:
        domain = TAG_TO_DOMAIN.get(tag.lower())
        if domain:
            counts[domain] = counts.get(domain, 0) + 1
    if not counts:
        return "general"
    return max(counts, key=counts.get)


def html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def estimate_urgency_signal(text: str) -> int:
    t = text.lower()
    score = 0
    for term in URGENCY_TERMS:
        if term in t:
            score += 1
    return score


def estimate_advanced_signal(text: str, tags: List[str]) -> int:
    t = text.lower()
    score = 0
    for term in ADVANCED_TERMS:
        if term in t:
            score += 1
    if any(tag.lower() in {"rust", "go", "kubernetes", "concurrency", "algorithms"} for tag in tags):
        score += 1
    return score


def stack_request(
    budget: ApiBudget,
    endpoint: str,
    params: dict,
    max_429_retries: int = 8,
) -> Optional[dict]:
    if not budget.can_call():
        return None

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    q = dict(params)
    q["site"] = SITE
    if STACKEXCHANGE_KEY:
        q["key"] = STACKEXCHANGE_KEY

    attempt = 0
    while attempt < max_429_retries:
        if not budget.can_call():
            return None
        try:
            response = requests.get(url, params=q, timeout=45)
            if response.status_code == 429:
                backoff = 90.0
                try:
                    err_payload = response.json()
                    backoff = float(err_payload.get("backoff", backoff))
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
                wait_s = min(600.0, max(20.0, backoff) + 2.0 * (attempt + 1))
                print(
                    f"  (429 throttled) esperando {wait_s:.0f}s "
                    f"(reintento {attempt + 1}/{max_429_retries})..."
                )
                time.sleep(wait_s)
                attempt += 1
                continue
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            print(f"  ✗ Error API {endpoint}: {exc}")
            return None

        budget.mark_call(payload.get("quota_remaining"))
        backoff = payload.get("backoff")
        if backoff:
            time.sleep(float(backoff) + 1.0)
        else:
            time.sleep(budget.sleep_seconds)
        return payload

    print(f"  ✗ Error API {endpoint}: 429 tras {max_429_retries} reintentos")
    return None


def seed_pool_from_existing_file(pool: Dict[int, dict], path: Path) -> int:
    """
    Inserta en `pool` filas ya presentes en so_questions.json (misma forma que el pool interno).
    Así una nueva extracción amplía candidatos sin descartar el corpus SO ya curado/etiquetado.
    """
    if not path.exists():
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  (seed) No se pudo leer {path}: {exc}")
        return 0
    if not isinstance(data, list):
        return 0
    added = 0
    for row in data:
        if not isinstance(row, dict):
            continue
        qid = row.get("question_id")
        if qid is None or qid in pool:
            continue
        title = html.unescape(str(row.get("title", "") or ""))
        body_raw = row.get("body", "") or ""
        body_str = body_raw if isinstance(body_raw, str) else str(body_raw)
        body_text = html_to_text(body_str) if "<" in body_str else body_str.strip()
        tags_raw = row.get("tags") or []
        if isinstance(tags_raw, str):
            tags_list = [tags_raw]
        else:
            tags_list = list(tags_raw)
        tags = [html.unescape(str(t)) for t in tags_list]
        if len(title.strip()) < 8 or len(body_text.strip()) < 20:
            continue
        combined = f"{title} {body_text}"
        urg = row.get("urgency_signal")
        adv = row.get("advanced_signal")
        if urg is None:
            urg = estimate_urgency_signal(combined)
        if adv is None:
            adv = estimate_advanced_signal(combined, tags)
        dom = str(row.get("domain_synapse") or "").strip() or get_domain_from_tags(tags)
        src = str(row.get("source_strategy") or "seed:existing_json")
        pool[int(qid)] = {
            "question_id": int(qid),
            "title": title,
            "body": body_text,
            "tags": tags,
            "score": int(row.get("score", 0) or 0),
            "view_count": int(row.get("view_count", 0) or 0),
            "answer_count": int(row.get("answer_count", 0) or 0),
            "creation_date": row.get("creation_date"),
            "link": row.get("link"),
            "domain_synapse": dom,
            "urgency_signal": int(urg),
            "advanced_signal": int(adv),
            "source_strategy": src,
        }
        added += 1
    return added


def add_candidates_from_items(pool: Dict[int, dict], items: List[dict], source: str) -> None:
    for q in items:
        qid = q.get("question_id")
        if qid is None:
            continue
        if qid in pool:
            continue

        title = html.unescape(q.get("title", "") or "")
        body_html = q.get("body", "") or ""
        body_text = html_to_text(body_html)
        tags = [html.unescape(t) for t in q.get("tags", [])]

        if len(title.strip()) < 8:
            continue
        if len(body_text.strip()) < 20:
            # Sin cuerpo util, pierde mucha señal para urgencia/nivel.
            continue

        combined_text = f"{title} {body_text}"
        pool[qid] = {
            "question_id": qid,
            "title": title,
            "body": body_text,
            "tags": tags,
            "score": q.get("score", 0),
            "view_count": q.get("view_count", 0),
            "answer_count": q.get("answer_count", 0),
            "creation_date": q.get("creation_date"),
            "link": q.get("link"),
            "domain_synapse": get_domain_from_tags(tags),
            "urgency_signal": estimate_urgency_signal(combined_text),
            "advanced_signal": estimate_advanced_signal(combined_text, tags),
            "source_strategy": source,
        }


def fetch_tag_queries(args, budget: ApiBudget, pool: Dict[int, dict]) -> None:
    print("\n[1/4] Extraccion por tags y sort mixto...")
    for domain, tags in DOMAIN_TO_TAGS.items():
        for tag in tags[: args.max_tags_per_domain]:
            for sort in ("votes", "creation"):
                for page in range(1, args.max_pages_per_tag + 1):
                    if not budget.can_call():
                        return

                    params = {
                        "page": page,
                        "pagesize": args.pagesize,
                        "order": "desc",
                        "sort": sort,
                        "tagged": tag,
                        "filter": "withbody",
                    }
                    if sort == "votes":
                        params["min"] = args.min_score_votes

                    payload = stack_request(budget, "questions", params)
                    if not payload:
                        break
                    items = payload.get("items", [])
                    if not items:
                        break
                    add_candidates_from_items(
                        pool=pool,
                        items=items,
                        source=f"questions:{sort}:tag={tag}",
                    )
                    if not payload.get("has_more", False):
                        break


def fetch_urgency_queries(args, budget: ApiBudget, pool: Dict[int, dict]) -> None:
    if args.no_advanced_search:
        return
    print("\n[2/4] Extraccion complementaria de casos urgentes...")
    tags_union = ";".join(sorted({t for tags in DOMAIN_TO_TAGS.values() for t in tags}))
    for term in URGENCY_TERMS[: args.max_urgent_terms]:
        if not budget.can_call():
            return
        params = {
            "page": 1,
            "pagesize": min(args.pagesize, 50),
            "order": "desc",
            "sort": "relevance",
            "q": term,
            "tagged": tags_union,
            "filter": "withbody",
        }
        payload = stack_request(budget, "search/advanced", params)
        if not payload:
            continue
        add_candidates_from_items(
            pool=pool,
            items=payload.get("items", []),
            source=f"advanced:q={term}",
        )


def fetch_advanced_queries(args, budget: ApiBudget, pool: Dict[int, dict]) -> None:
    if args.no_advanced_search:
        return
    print("\n[3/4] Extraccion complementaria de candidatos avanzados (y baja urgencia si aggressive)...")
    tags_union = ";".join(sorted({t for tags in DOMAIN_TO_TAGS.values() for t in tags}))
    adv_terms = list(ADVANCED_SEARCH_TERMS)
    if args.rebalance_profile == "aggressive":
        adv_terms.extend(ADVANCED_SEARCH_TERMS_AGGRESSIVE_EXTRA)
    for term in adv_terms[: args.max_advanced_terms]:
        if not budget.can_call():
            return
        params = {
            "page": 1,
            "pagesize": min(args.pagesize, 50),
            "order": "desc",
            "sort": "relevance",
            "q": term,
            "tagged": tags_union,
            "filter": "withbody",
        }
        payload = stack_request(budget, "search/advanced", params)
        if not payload:
            continue
        add_candidates_from_items(
            pool=pool,
            items=payload.get("items", []),
            source=f"advanced:adv={term}",
        )
    if args.rebalance_profile == "aggressive":
        for term in LOW_URGENCY_SEARCH_TERMS[: args.max_low_urgency_terms]:
            if not budget.can_call():
                return
            params = {
                "page": 1,
                "pagesize": min(args.pagesize, 50),
                "order": "desc",
                "sort": "relevance",
                "q": term,
                "tagged": tags_union,
                "filter": "withbody",
            }
            payload = stack_request(budget, "search/advanced", params)
            if not payload:
                continue
            add_candidates_from_items(
                pool=pool,
                items=payload.get("items", []),
                source=f"advanced:lowurg={term}",
            )


def take_domain_diverse(items: List[dict], quota: int) -> List[dict]:
    if quota <= 0 or not items:
        return []
    # Priorizamos señales de urgencia/avanzado, pero sin quedarnos solo en top-votes.
    scored = sorted(
        items,
        key=lambda x: (
            x.get("urgency_signal", 0),
            x.get("advanced_signal", 0),
            min(10, max(-2, int(x.get("score", 0)))),  # cap para no sesgar por outliers
            int(x.get("creation_date", 0)),
        ),
        reverse=True,
    )
    low_med = [x for x in scored if int(x.get("score", 0)) <= 10]
    high = [x for x in scored if int(x.get("score", 0)) > 10]

    out: List[dict] = []
    i_low, i_high = 0, 0
    while len(out) < quota and (i_low < len(low_med) or i_high < len(high)):
        # Regla 2:1 a favor de low/med para descanonicalizar el set.
        for _ in range(2):
            if len(out) >= quota:
                break
            if i_low < len(low_med):
                out.append(low_med[i_low])
                i_low += 1
        if len(out) >= quota:
            break
        if i_high < len(high):
            out.append(high[i_high])
            i_high += 1
    return out[:quota]


def load_domain_min_quota(path: Optional[str], *, profile: str) -> Dict[str, int]:
    """Carga pisos por dominio; base según perfil de rebalanceo."""
    base = AGGRESSIVE_DOMAIN_MIN_QUOTA if profile == "aggressive" else DEFAULT_DOMAIN_MIN_QUOTA
    merged = dict(base)
    if not path:
        return merged
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    with open(p, encoding="utf-8") as f:
        overrides = json.load(f)
    if not isinstance(overrides, dict):
        raise ValueError("--domain-min-json debe ser un objeto JSON {dominio: entero}")
    for key, val in overrides.items():
        if isinstance(key, str) and isinstance(val, int) and val >= 0:
            merged[key] = val
    return merged


def select_balanced_subset(
    candidates: List[dict],
    max_questions: int,
    domain_min_quota: Optional[Dict[str, int]] = None,
) -> List[dict]:
    """Selecciona hasta `max_questions` priorizando pisos por dominio y luego relleno global."""
    by_domain: Dict[str, List[dict]] = defaultdict(list)
    for row in candidates:
        by_domain[row.get("domain_synapse", "general")].append(row)

    if not candidates:
        return []

    quotas_src = dict(domain_min_quota or DEFAULT_DOMAIN_MIN_QUOTA)
    reserve = max(12, max_questions // 30)
    floor_budget = max(0, max_questions - reserve)

    raw_want: Dict[str, int] = {}
    for domain, rows in by_domain.items():
        raw_want[domain] = min(quotas_src.get(domain, 0), len(rows))

    total_want = sum(raw_want.values())
    alloc: Dict[str, int] = {}
    if total_want <= floor_budget or total_want == 0:
        alloc = dict(raw_want)
    else:
        scale = floor_budget / total_want
        for domain in raw_want:
            alloc[domain] = max(0, int(raw_want[domain] * scale))

    selected: List[dict] = []
    used_ids: Set[int] = set()

    domain_order = sorted(
        (d for d in by_domain if d != "general"),
        key=lambda d: (-alloc.get(d, 0), d),
    )
    if "general" in by_domain:
        domain_order.append("general")

    for domain in domain_order:
        if len(selected) >= max_questions:
            break
        want = alloc.get(domain, 0)
        pool = [r for r in by_domain[domain] if r["question_id"] not in used_ids]
        take_count = min(want, len(pool), max_questions - len(selected))
        chosen = take_domain_diverse(pool, take_count)
        for r in chosen:
            used_ids.add(r["question_id"])
            selected.append(r)

    if len(selected) < max_questions:
        leftovers = [x for x in candidates if x["question_id"] not in used_ids]
        leftovers.sort(
            key=lambda x: (
                x.get("urgency_signal", 0),
                x.get("advanced_signal", 0),
                int(x.get("creation_date", 0)),
            ),
            reverse=True,
        )
        needed = max_questions - len(selected)
        for x in leftovers[:needed]:
            if x["question_id"] in used_ids:
                continue
            used_ids.add(x["question_id"])
            selected.append(x)

    seen: Set[int] = set()
    final: List[dict] = []
    for row in selected:
        qid = row["question_id"]
        if qid in seen:
            continue
        seen.add(qid)
        final.append(row)
    return final[:max_questions]


def build_extraction_audit(
    selected: List[dict], candidates: List[dict], budget: ApiBudget, args: Any
) -> Dict[str, Any]:
    tag_ctr: Counter = Counter()
    prefix_ctr: Counter = Counter()
    for r in selected:
        src = str(r.get("source_strategy", "") or "")
        prefix_ctr[src.split(":")[0]] += 1
        for t in r.get("tags") or []:
            tag_ctr[str(t).lower()] += 1
    return {
        "max_questions": args.max_questions,
        "max_api_calls": args.max_api_calls,
        "rebalance_profile": getattr(args, "rebalance_profile", "default"),
        "api_calls_used": budget.calls,
        "candidates_pool_size": len(candidates),
        "selected_n": len(selected),
        "domain_counts": dict(Counter(r.get("domain_synapse", "general") for r in selected)),
        "top_tags_in_selected": dict(tag_ctr.most_common(24)),
        "source_strategy_prefix_counts": dict(prefix_ctr),
        "signals": {
            "urgency_signal_gt0": sum(1 for r in selected if int(r.get("urgency_signal", 0) or 0) > 0),
            "advanced_signal_gt0": sum(1 for r in selected if int(r.get("advanced_signal", 0) or 0) > 0),
        },
    }


def print_summary(rows: List[dict], budget: ApiBudget, output_path: Path) -> None:
    print("\n" + "=" * 72)
    print("RESUMEN EXTRACCION")
    print("=" * 72)
    print(f"Llamadas API usadas: {budget.calls}/{budget.max_calls}")
    if budget.quota_remaining is not None:
        print(f"Quota remaining reportada por API: {budget.quota_remaining}")
    print(f"Preguntas finales: {len(rows)}")
    print(f"Archivo: {output_path}")

    domain_counts = Counter(r["domain_synapse"] for r in rows)
    print("\nDistribucion por dominio:")
    for domain, total in sorted(domain_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {domain}: {total}")

    urg_signal = Counter("high_signal" if r["urgency_signal"] > 0 else "no_signal" for r in rows)
    adv_signal = Counter("high_signal" if r["advanced_signal"] > 0 else "no_signal" for r in rows)
    avg_body = sum(len(r.get("body", "")) for r in rows) / max(1, len(rows))
    print(f"\nBody promedio (chars): {avg_body:.1f}")
    print(f"Urgency signal >0: {urg_signal['high_signal']} / {len(rows)}")
    print(f"Advanced signal >0: {adv_signal['high_signal']} / {len(rows)}")


def extract_questions(args) -> bool:
    budget = ApiBudget(max_calls=args.max_api_calls, sleep_seconds=args.sleep_seconds)
    pool: Dict[int, dict] = {}
    output_path = RAW_DIR / args.output_filename

    if args.seed_existing:
        seeded = seed_pool_from_existing_file(pool, output_path)
        print(f"\n[0/4] Semilla desde JSON existente ({output_path.name}): {seeded} candidatos")

    print("=" * 72)
    print("EXTRACCION STACK OVERFLOW ES (BALANCEADA + QUOTA-SAFE)")
    print("=" * 72)
    if not STACKEXCHANGE_KEY:
        print(
            "AVISO: STACKEXCHANGE_KEY no definida; la API limita a ~300 req/día por IP "
            "y verás 429. Define la clave (stackapps.com) antes de extracciones grandes.\n"
        )
    print(f"max_questions={args.max_questions}")
    print(f"max_api_calls={args.max_api_calls}")
    print(f"pagesize={args.pagesize}")
    print(f"max_pages_per_tag={args.max_pages_per_tag}")
    print(f"max_tags_per_domain={args.max_tags_per_domain}")
    print(f"use_advanced_search={not args.no_advanced_search}")
    print(f"rebalance_profile={args.rebalance_profile}")
    print(f"domain_min_quota={args.domain_min_json or ('aggressive' if args.rebalance_profile == 'aggressive' else 'default')}")

    fetch_tag_queries(args, budget, pool)
    fetch_urgency_queries(args, budget, pool)
    fetch_advanced_queries(args, budget, pool)

    print("\n[4/4] Seleccion balanceada final...")
    candidates = list(pool.values())
    domain_mins = load_domain_min_quota(args.domain_min_json, profile=args.rebalance_profile)
    selected = select_balanced_subset(candidates, args.max_questions, domain_mins)

    audit = build_extraction_audit(selected, candidates, budget, args)
    with open(RAW_DIR / "extraction_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    print_summary(selected, budget, output_path)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraer preguntas SO ES para Fase 3.")
    parser.add_argument(
        "--max-questions",
        type=int,
        default=1600,
        help="Tope de preguntas seleccionadas (default 1600).",
    )
    parser.add_argument("--output-filename", type=str, default="so_questions.json")
    parser.add_argument("--min-score-votes", type=int, default=0)
    parser.add_argument("--pagesize", type=int, default=100)
    parser.add_argument(
        "--max-pages-per-tag",
        type=int,
        default=4,
        help="Paginación por tag (más páginas = más diversidad si el presupuesto API lo permite).",
    )
    parser.add_argument(
        "--max-tags-per-domain",
        type=int,
        default=5,
        help="Cuántos tags por dominio recorrer en la fase por tags.",
    )
    parser.add_argument("--max-urgent-terms", type=int, default=6)
    parser.add_argument("--max-advanced-terms", type=int, default=5)
    parser.add_argument(
        "--max-api-calls",
        type=int,
        default=960,
        help="Presupuesto de llamadas Stack Exchange (subir con --max-questions).",
    )
    parser.add_argument(
        "--seed-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Antes de la API, cargar candidatos desde el JSON de salida si ya existe (no pierdes SO previo).",
    )
    parser.add_argument("--sleep-seconds", type=float, default=1.05)
    parser.add_argument("--no-advanced-search", action="store_true")
    parser.add_argument(
        "--rebalance-profile",
        choices=("default", "aggressive"),
        default="default",
        help="aggressive: pisos mayores en dominios débiles, más términos advanced/low-urgency en búsqueda.",
    )
    parser.add_argument(
        "--max-low-urgency-terms",
        type=int,
        default=8,
        help="Cuántos términos LOW_URGENCY usar en perfil aggressive (dentro del paso advanced).",
    )
    parser.add_argument(
        "--domain-min-json",
        type=str,
        default="",
        help="JSON opcional {dominio: int} con pisos mínimos por dominio antes del relleno global.",
    )

    args = parser.parse_args()
    if args.rebalance_profile == "aggressive":
        if args.max_advanced_terms <= 5:
            args.max_advanced_terms = 14
        if args.max_urgent_terms <= 6:
            args.max_urgent_terms = 9

    ok = extract_questions(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
