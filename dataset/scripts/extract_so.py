#!/usr/bin/env python3
"""
Extraccion de preguntas de Stack Overflow ES para Fase 3.

Objetivos:
- Incluir cuerpo real de la pregunta (filter=withbody)
- Reducir sesgo por "top votos"
- Mejorar diversidad por dominio
- Mantener un presupuesto de llamadas API
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
from typing import Dict, List, Optional

import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
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
    "security": "seguridad",
    "authentication": "seguridad",
    "encryption": "seguridad",
    "oauth": "seguridad",
    "os": "sistemas",
    "memory": "sistemas",
    "concurrency": "sistemas",
    "threads": "sistemas",
    "process": "sistemas",
    "design-patterns": "ingenieria_software",
    "testing": "ingenieria_software",
    "architecture": "ingenieria_software",
    "solid": "ingenieria_software",
    "git": "general",
    "typescript": "general",
}

DOMAIN_TO_TAGS = {
    "backend": ["python", "javascript", "java", "node.js"],
    "frontend": ["react", "css", "html", "vue.js"],
    "bases_de_datos": ["sql", "mysql", "postgresql", "mongodb"],
    "devops": ["docker", "kubernetes", "aws", "nginx"],
    "movil": ["android", "ios", "flutter", "react-native"],
    "data_science": ["pandas", "numpy", "scikit-learn", "tensorflow"],
    "algoritmos": ["algorithms", "data-structures", "recursion", "sorting"],
    "seguridad": ["security", "authentication", "oauth", "encryption"],
    "sistemas": ["concurrency", "threads", "memory", "os"],
    "ingenieria_software": ["testing", "design-patterns", "architecture", "solid"],
    "general": ["git", "typescript"],
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
) -> Optional[dict]:
    if not budget.can_call():
        return None

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    q = dict(params)
    q["site"] = SITE
    if STACKEXCHANGE_KEY:
        q["key"] = STACKEXCHANGE_KEY

    try:
        response = requests.get(url, params=q, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"  ✗ Error API {endpoint}: {exc}")
        return None

    budget.mark_call(payload.get("quota_remaining"))
    backoff = payload.get("backoff")
    if backoff:
        time.sleep(float(backoff) + 1.0)
    else:
        time.sleep(budget.sleep_seconds)
    return payload


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
    print("\n[1/3] Extraccion por tags y sort mixto...")
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
    print("\n[2/3] Extraccion complementaria de casos urgentes...")
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


def select_balanced_subset(candidates: List[dict], max_questions: int) -> List[dict]:
    by_domain: Dict[str, List[dict]] = defaultdict(list)
    for row in candidates:
        by_domain[row.get("domain_synapse", "general")].append(row)

    domains = [d for d, rows in by_domain.items() if rows]
    if not domains:
        return []

    per_domain_base = max_questions // len(domains)
    remainder = max_questions % len(domains)

    selected: List[dict] = []
    for idx, domain in enumerate(sorted(domains)):
        quota = per_domain_base + (1 if idx < remainder else 0)
        selected.extend(take_domain_diverse(by_domain[domain], quota))

    # Si falta por falta de inventario en un dominio, rellenar globalmente por señal.
    if len(selected) < max_questions:
        used_ids = {row["question_id"] for row in selected}
        leftovers = [x for x in candidates if x["question_id"] not in used_ids]
        leftovers = sorted(
            leftovers,
            key=lambda x: (
                x.get("urgency_signal", 0),
                x.get("advanced_signal", 0),
                int(x.get("creation_date", 0)),
            ),
            reverse=True,
        )
        needed = max_questions - len(selected)
        selected.extend(leftovers[:needed])

    # Dedupe final por seguridad.
    seen = set()
    final = []
    for row in selected:
        qid = row["question_id"]
        if qid in seen:
            continue
        seen.add(qid)
        final.append(row)
    return final[:max_questions]


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

    print("=" * 72)
    print("EXTRACCION STACK OVERFLOW ES (BALANCEADA + QUOTA-SAFE)")
    print("=" * 72)
    print(f"max_questions={args.max_questions}")
    print(f"max_api_calls={args.max_api_calls}")
    print(f"pagesize={args.pagesize}")
    print(f"max_pages_per_tag={args.max_pages_per_tag}")
    print(f"max_tags_per_domain={args.max_tags_per_domain}")
    print(f"use_advanced_search={not args.no_advanced_search}")

    fetch_tag_queries(args, budget, pool)
    fetch_urgency_queries(args, budget, pool)

    print("\n[3/3] Seleccion balanceada final...")
    candidates = list(pool.values())
    selected = select_balanced_subset(candidates, args.max_questions)

    output_path = RAW_DIR / args.output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    print_summary(selected, budget, output_path)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraer preguntas SO ES para Fase 3.")
    parser.add_argument("--max-questions", type=int, default=250)
    parser.add_argument("--output-filename", type=str, default="so_questions.json")
    parser.add_argument("--min-score-votes", type=int, default=0)
    parser.add_argument("--pagesize", type=int, default=100)
    parser.add_argument("--max-pages-per-tag", type=int, default=1)
    parser.add_argument("--max-tags-per-domain", type=int, default=2)
    parser.add_argument("--max-urgent-terms", type=int, default=6)
    parser.add_argument("--max-api-calls", type=int, default=80)
    parser.add_argument("--sleep-seconds", type=float, default=0.7)
    parser.add_argument("--no-advanced-search", action="store_true")

    args = parser.parse_args()
    ok = extract_questions(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
