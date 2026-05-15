#!/usr/bin/env python3
"""
Reporte de calidad de Fase 3 (pre-Fase 4).
"""

import argparse
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_PATH = PROJECT_ROOT / "dataset" / "raw" / "so_questions.json"
LABELED_PATH = PROJECT_ROOT / "dataset" / "processed" / "labeled.json"
OUTPUT_PATH = PROJECT_ROOT / "dataset" / "processed" / "phase3_quality_report.json"


def pct(part: int, total: int) -> float:
    return (part / total * 100.0) if total else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera reporte de calidad de Fase 3.")
    parser.add_argument("--raw", type=str, default=str(RAW_PATH))
    parser.add_argument("--labeled", type=str, default=str(LABELED_PATH))
    parser.add_argument("--output", type=str, default=str(OUTPUT_PATH))
    parser.add_argument("--min-urgencia-alta-pct", type=float, default=8.0)
    parser.add_argument("--min-nivel-avanzado-pct", type=float, default=4.0)
    parser.add_argument("--min-domain-count", type=int, default=5)
    args = parser.parse_args()

    raw_rows = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    labeled_rows = json.loads(Path(args.labeled).read_text(encoding="utf-8"))

    total_raw = len(raw_rows)
    total_labeled = len(labeled_rows)
    by_id_raw = {r.get("question_id"): r for r in raw_rows}
    ids_labeled = [r.get("question_id") for r in labeled_rows]
    unique_labeled = len(set(ids_labeled))

    body_empty_raw = sum(1 for r in raw_rows if not (r.get("body") or "").strip())
    body_empty_labeled = sum(1 for r in labeled_rows if not (r.get("body") or "").strip())

    domain_counts_raw = Counter(r.get("domain_synapse", "general") for r in raw_rows)
    nivel_counts = Counter(r.get("nivel_tecnico", "") for r in labeled_rows)
    urg_counts = Counter(r.get("urgencia", "") for r in labeled_rows)
    model_counts = Counter(r.get("model_used", "na") for r in labeled_rows)

    advanced_count = nivel_counts.get("avanzado", 0)
    alta_count = urg_counts.get("alta", 0)
    advanced_pct = pct(advanced_count, total_labeled)
    alta_pct = pct(alta_count, total_labeled)

    schema_ok = 0
    for row in labeled_rows:
        has_core = all(
            key in row for key in ("question_id", "title", "body", "tags", "domain_synapse", "nivel_tecnico", "urgencia")
        )
        if has_core:
            schema_ok += 1

    gates = {
        "gate_rows_match_raw": total_labeled == total_raw,
        "gate_unique_question_ids": unique_labeled == total_labeled,
        "gate_raw_body_non_empty": body_empty_raw == 0,
        "gate_labeled_body_non_empty": body_empty_labeled == 0,
        "gate_schema_coverage_100pct": schema_ok == total_labeled,
        "gate_urgencia_alta_min_pct": alta_pct >= args.min_urgencia_alta_pct,
        "gate_nivel_avanzado_min_pct": advanced_pct >= args.min_nivel_avanzado_pct,
        "gate_domain_floor": all(v >= args.min_domain_count for v in domain_counts_raw.values()),
    }

    report = {
        "totals": {
            "raw_rows": total_raw,
            "labeled_rows": total_labeled,
            "unique_labeled_ids": unique_labeled,
            "schema_ok_rows": schema_ok,
        },
        "empties": {
            "raw_body_empty": body_empty_raw,
            "labeled_body_empty": body_empty_labeled,
        },
        "distributions": {
            "domain_raw": dict(domain_counts_raw),
            "nivel_tecnico": dict(nivel_counts),
            "urgencia": dict(urg_counts),
            "model_used": dict(model_counts),
        },
        "rates": {
            "nivel_avanzado_pct": round(advanced_pct, 2),
            "urgencia_alta_pct": round(alta_pct, 2),
        },
        "thresholds": {
            "min_urgencia_alta_pct": args.min_urgencia_alta_pct,
            "min_nivel_avanzado_pct": args.min_nivel_avanzado_pct,
            "min_domain_count": args.min_domain_count,
        },
        "gates": gates,
        "overall_ready_for_phase4": all(gates.values()),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    print("PHASE 3 QUALITY REPORT")
    print("=" * 72)
    print(f"output={out_path}")
    print(f"overall_ready_for_phase4={report['overall_ready_for_phase4']}")
    for k, v in gates.items():
        print(f"{k}={v}")


if __name__ == "__main__":
    main()
