#!/usr/bin/env python3
"""
Refinamiento de Fase 3 por consenso multi-modelo.

Objetivo:
- Mejorar etiquetas "avanzado" y "alta" sin generar datos sintéticos.
- Aplicar cambios solo cuando haya acuerdo entre modelos.
"""

import argparse
import html
import json
import os
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_PATH = PROJECT_ROOT / "dataset" / "raw" / "so_questions.json"
DEFAULT_INPUT = PROJECT_ROOT / "dataset" / "processed" / "labeled.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "dataset" / "processed" / "labeled.v2.json"
DEFAULT_AUDIT = PROJECT_ROOT / "dataset" / "processed" / "phase3_consensus_audit.jsonl"

VALID_NIVELES = {"principiante", "intermedio", "avanzado"}
VALID_URGENCIAS = {"baja", "media", "alta"}

URGENCY_STRONG_TERMS = [
    "urgente",
    "bloqueado",
    "bloqueada",
    "bloqueo",
    "desesperado",
    "desesperada",
    "desesperacion",
    "deadline",
    "entrega",
    "examen",
    "contrarreloj",
]
URGENCY_WEAK_TERMS = ["ayuda", "auxilio", "error", "no funciona", "no me funciona", "falla"]
ADVANCED_STRONG_TERMS = [
    "complejidad",
    "big o",
    "optimizacion",
    "optimizar",
    "optimizado",
    "concurrencia",
    "arquitectura",
    "escalabilidad",
    "latencia",
    "throughput",
]
ADVANCED_WEAK_TERMS = ["patrones", "rendimiento", "profil", "benchmark"]
ADVANCED_HINT_TAGS = {
    "algorithms",
    "data-structures",
    "concurrency",
    "multithreading",
    "kubernetes",
    "rust",
    "go",
}

CONSENSUS_PROMPT = """Analiza esta pregunta de programación en español.

Título: {title}
Cuerpo: {body}
Tags: {tags}

Clasifica:
1) nivel_tecnico: principiante/intermedio/avanzado
2) urgencia: baja/media/alta

Rubrica:
- "avanzado" si requiere optimización no trivial, complejidad algorítmica (Big-O), concurrencia, sistemas distribuidos, Kubernetes/DevOps de producción o arquitectura SSR/microfrontends con tradeoffs.
- "alta" solo si hay bloqueo real o presión temporal explícita.
- No marques "alta" solo por aparecer la palabra "error" o "ayuda".

Responde SOLO JSON válido:
{{"nivel_tecnico":"principiante|intermedio|avanzado","urgencia":"baja|media|alta"}}"""


def normalize_spanish_text(text: str) -> str:
    lowered = (text or "").lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def urgency_signal(text: str) -> bool:
    norm = normalize_spanish_text(text)
    strong_hits = sum(1 for term in URGENCY_STRONG_TERMS if term in norm)
    weak_hits = sum(1 for term in URGENCY_WEAK_TERMS if term in norm)
    return strong_hits >= 1 or weak_hits >= 2


def advanced_signal(text: str, tags: List[str]) -> bool:
    norm = normalize_spanish_text(text)
    strong_hits = sum(1 for term in ADVANCED_STRONG_TERMS if term in norm)
    weak_hits = sum(1 for term in ADVANCED_WEAK_TERMS if term in norm)
    tag_hits = sum(1 for tag in tags if normalize_spanish_text(str(tag)) in ADVANCED_HINT_TAGS)
    return strong_hits >= 1 or weak_hits >= 2 or tag_hits >= 1


def clean_json(text: str) -> Optional[dict]:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(text[start : end + 1])
            nivel = str(parsed.get("nivel_tecnico", "")).strip().lower()
            urg = str(parsed.get("urgencia", "")).strip().lower()
            if nivel in VALID_NIVELES and urg in VALID_URGENCIAS:
                return {"nivel_tecnico": nivel, "urgencia": urg}
    except Exception:
        return None
    return None


def get_client(base_url: str, api_key: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))


def call_model(client, model: str, prompt: str, max_retries: int, retry_base_seconds: int) -> Optional[dict]:
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=120,
            )
            content = response.choices[0].message.content
            parsed = clean_json(content)
            if parsed:
                return parsed
        except Exception as exc:
            msg = str(exc).lower()
            retryable = "429" in msg or "rate" in msg or "timeout" in msg
            if retryable and attempt < max_retries - 1:
                time.sleep(retry_base_seconds * (attempt + 1))
                continue
            return None
    return None


def pick_candidates(
    labeled_rows: List[dict],
    source_by_id: Dict[int, dict],
    max_candidates: int,
) -> List[Tuple[int, dict, dict, bool]]:
    ranked = []
    for idx, row in enumerate(labeled_rows):
        qid = row.get("question_id")
        src = source_by_id.get(qid)
        if not src:
            continue
        title = src.get("title", row.get("title", ""))
        body = src.get("body", row.get("body", ""))
        tags = src.get("tags", row.get("tags", []))
        text = f"{title} {body} {' '.join(tags)}"
        u_sig = urgency_signal(text)
        a_sig = advanced_signal(text, tags)
        if row.get("nivel_tecnico") == "avanzado" and row.get("urgencia") == "alta":
            continue
        # Priorizamos candidatos donde haya señal y aún no estén en la etiqueta objetivo.
        need_adv = row.get("nivel_tecnico") != "avanzado"
        need_high = row.get("urgencia") != "alta"
        if (need_adv and a_sig) or (need_high and u_sig):
            rank = (
                int(a_sig and need_adv),
                int(u_sig and need_high),
                min(10, int(src.get("score", 0))),
                int(src.get("creation_date", 0)),
            )
            ranked.append((rank, idx, row, src, a_sig))
    ranked.sort(reverse=True, key=lambda x: x[0])
    return [(idx, row, src, a_sig) for _, idx, row, src, a_sig in ranked[:max_candidates]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Refinar labels de Fase 3 por consenso.")
    parser.add_argument("--input", type=str, default=str(DEFAULT_INPUT))
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--audit", type=str, default=str(DEFAULT_AUDIT))
    parser.add_argument("--base-url", type=str, default=os.getenv("COPILOT_BASE_URL", "http://localhost:4141/v1"))
    parser.add_argument("--api-key", type=str, default=os.getenv("COPILOT_API_KEY", "dummy"))
    parser.add_argument("--models", type=str, default="gpt-4.1,gpt-5-mini,gpt-4o")
    parser.add_argument("--max-candidates", type=int, default=80)
    parser.add_argument("--target-min-avanzado", type=int, default=12)
    parser.add_argument("--target-min-alta", type=int, default=24)
    parser.add_argument("--min-votes-avanzado", type=int, default=2)
    parser.add_argument("--min-votes-alta", type=int, default=2)
    parser.add_argument(
        "--advanced-decision-mode",
        type=str,
        default="strict_consensus",
        choices=["strict_consensus", "expert_plus_signal"],
    )
    parser.add_argument("--expert-model", type=str, default="gpt-4.1")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-base-seconds", type=int, default=8)
    parser.add_argument("--delay-seconds", type=float, default=0.6)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    audit_path = Path(args.audit)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if len(models) < 2:
        print("Error: usa al menos 2 modelos para consenso.")
        sys.exit(1)

    labeled_rows = json.loads(input_path.read_text(encoding="utf-8"))
    source_rows = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    source_by_id = {r["question_id"]: r for r in source_rows if "question_id" in r}

    niveles = Counter(r.get("nivel_tecnico", "") for r in labeled_rows)
    urgs = Counter(r.get("urgencia", "") for r in labeled_rows)
    adv_deficit = max(0, args.target_min_avanzado - niveles.get("avanzado", 0))
    high_deficit = max(0, args.target_min_alta - urgs.get("alta", 0))

    print("=" * 72)
    print("PHASE 3 CONSENSUS REFINEMENT")
    print("=" * 72)
    print(f"input={input_path}")
    print(f"modelos={models}")
    print(f"deficit_avanzado={adv_deficit} | deficit_alta={high_deficit}")

    if adv_deficit == 0 and high_deficit == 0:
        print("Sin deficits. No hay cambios necesarios.")
        if not args.dry_run:
            output_path.write_text(json.dumps(labeled_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit(0)

    candidates = pick_candidates(labeled_rows, source_by_id, args.max_candidates)
    print(f"candidatos={len(candidates)}")

    client = get_client(args.base_url, args.api_key)
    changes = 0
    model_calls = 0

    if not args.dry_run:
        audit_path.parent.mkdir(parents=True, exist_ok=True)

    for idx, row, src, candidate_has_advanced_signal in candidates:
        if adv_deficit <= 0 and high_deficit <= 0:
            break

        title = html.unescape(src.get("title", row.get("title", "")))
        body = html.unescape((src.get("body", row.get("body", "")) or "")[:1200])
        tags = ", ".join(src.get("tags", row.get("tags", [])))
        prompt = CONSENSUS_PROMPT.format(title=title, body=body, tags=tags)

        votes = []
        for model in models:
            out = call_model(
                client=client,
                model=model,
                prompt=prompt,
                max_retries=args.max_retries,
                retry_base_seconds=args.retry_base_seconds,
            )
            model_calls += 1
            if out is not None:
                votes.append((model, out))
            time.sleep(args.delay_seconds)

        if len(votes) < 2:
            continue

        adv_votes = sum(1 for _, v in votes if v["nivel_tecnico"] == "avanzado")
        high_votes = sum(1 for _, v in votes if v["urgencia"] == "alta")
        new_level = row.get("nivel_tecnico")
        new_urg = row.get("urgencia")
        changed = False

        promote_advanced = False
        if adv_deficit > 0 and row.get("nivel_tecnico") != "avanzado":
            if args.advanced_decision_mode == "strict_consensus":
                promote_advanced = adv_votes >= args.min_votes_avanzado
            else:
                expert_vote = any(m == args.expert_model and v["nivel_tecnico"] == "avanzado" for m, v in votes)
                promote_advanced = candidate_has_advanced_signal and expert_vote
            if promote_advanced:
                new_level = "avanzado"
                adv_deficit -= 1
                changed = True

        if high_deficit > 0 and row.get("urgencia") != "alta" and high_votes >= args.min_votes_alta:
            new_urg = "alta"
            high_deficit -= 1
            changed = True

        if not changed:
            continue

        event = {
            "question_id": row.get("question_id"),
            "before": {"nivel_tecnico": row.get("nivel_tecnico"), "urgencia": row.get("urgencia")},
            "after": {"nivel_tecnico": new_level, "urgencia": new_urg},
            "advanced_decision_mode": args.advanced_decision_mode,
            "votes": [{"model": m, "nivel_tecnico": v["nivel_tecnico"], "urgencia": v["urgencia"]} for m, v in votes],
        }

        row["nivel_tecnico"] = new_level
        row["urgencia"] = new_urg
        row["model_used"] = f"consensus:{'|'.join(models)}"
        row["body"] = html.unescape(src.get("body", row.get("body", "")) or "")
        changes += 1

        if not args.dry_run:
            with open(audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

    niveles_after = Counter(r.get("nivel_tecnico", "") for r in labeled_rows)
    urgs_after = Counter(r.get("urgencia", "") for r in labeled_rows)

    print(f"changes={changes} | model_calls={model_calls}")
    print(f"nivel_after={dict(niveles_after)}")
    print(f"urgencia_after={dict(urgs_after)}")
    print(f"remaining_deficit_avanzado={max(0, args.target_min_avanzado - niveles_after.get('avanzado', 0))}")
    print(f"remaining_deficit_alta={max(0, args.target_min_alta - urgs_after.get('alta', 0))}")

    if not args.dry_run:
        output_path.write_text(json.dumps(labeled_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved={output_path}")
        print(f"audit={audit_path}")


if __name__ == "__main__":
    main()
