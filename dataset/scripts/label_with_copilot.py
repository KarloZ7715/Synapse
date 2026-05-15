#!/usr/bin/env python3
"""
Fase 3 - Etiquetado con GitHub Copilot (via copilot-api proxy).

Uso rapido:
1. Iniciar proxy: npx copilot-api@latest start --port 4141
2. Probar modelos disponibles:
   python dataset/scripts/label_with_copilot.py --list-models
3. Etiquetar reanudando desde dataset/processed/labeled.json:
   python dataset/scripts/label_with_copilot.py --max-examples 250
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
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_ROOT / "dataset" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "dataset" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_BASE_URL = os.getenv("COPILOT_BASE_URL", "http://localhost:4141/v1")
DEFAULT_MODELS = ["gpt-5-mini", "gpt-4.1", "gpt-4o"]
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
URGENCY_WEAK_TERMS = [
    "ayuda",
    "auxilio",
    "error",
    "no funciona",
    "no me funciona",
    "falla",
]
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
ADVANCED_WEAK_TERMS = [
    "patrones",
    "rendimiento",
    "profil",
    "benchmark",
]
ADVANCED_HINT_TAGS = {
    "algorithms",
    "data-structures",
    "concurrency",
    "multithreading",
    "kubernetes",
    "rust",
    "go",
}

LABELING_PROMPT = """Analiza esta pregunta de programacion en espanol:

Titulo: {title}
Cuerpo: {body}
Tags: {tags}

Determina unicamente:

1. Nivel tecnico del autor:
   - principiante: conceptos basicos, confusion con fundamentos
   - intermedio: frameworks, patrones, integraciones comunes
   - avanzado: optimizacion no trivial, complejidad algoritmica, concurrencia, arquitectura con tradeoffs

2. Urgencia:
   - baja: curiosidad, sin presion
   - media: necesita resolver pero sin urgencia extrema
   - alta: bloqueado, fecha limite, desesperacion

Reglas:
- Si el problema exige discutir Big-O, optimizacion de rendimiento no trivial o arquitectura compleja, usa "avanzado".
- No uses "avanzado" solo por mencionar una tecnologia popular.
- Usa "alta" solo si hay señales de bloqueo/presion temporal explicita.

Responde SOLO con JSON valido:
{{"nivel_tecnico": "principiante|intermedio|avanzado", "urgencia": "baja|media|alta"}}"""

CALIBRATION_PROMPT = """Re-evalua esta pregunta de programacion en espanol para detectar subestimaciones.

Titulo: {title}
Cuerpo: {body}
Tags: {tags}

Reglas estrictas:
- Marca urgencia="alta" solo si hay señales claras de bloqueo o presion temporal (ej: urgente, entrega, examen, bloqueado, desesperado).
- Marca nivel_tecnico="avanzado" si el problema implica optimizacion no trivial, complejidad algoritmica (Big-O), concurrencia o arquitectura con tradeoffs.
- No marques "alta" solo por la palabra "error" o "ayuda" si no hay contexto de bloqueo real.
- Si no hay evidencia suficiente para "alta" o "avanzado", usa "media/baja" e "intermedio/principiante".

Responde SOLO con JSON valido:
{{"nivel_tecnico": "principiante|intermedio|avanzado", "urgencia": "baja|media|alta"}}"""


def parse_models_arg(raw_models: str) -> List[str]:
    models = [m.strip() for m in raw_models.split(",") if m.strip()]
    return models or list(DEFAULT_MODELS)


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def get_openai_client(base_url: str, api_key: str):
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: falta dependencia 'openai'. Instala con: pip install openai")
        sys.exit(1)
    return OpenAI(api_key=api_key, base_url=normalize_base_url(base_url))


def fetch_available_models(base_url: str, api_key: str) -> List[str]:
    client = get_openai_client(base_url=base_url, api_key=api_key)
    models = client.models.list()
    return [m.id for m in getattr(models, "data", []) if getattr(m, "id", None)]


def resolve_model_id(requested_model: str, available_models: List[str]) -> Optional[str]:
    if requested_model in available_models:
        return requested_model

    prefix_candidates = sorted(
        [m for m in available_models if m.startswith(f"{requested_model}-")]
    )
    if prefix_candidates:
        return prefix_candidates[0]

    return None


def load_model_route_overrides(raw: str) -> Dict[str, str]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--model-route-overrides JSON invalido: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--model-route-overrides debe ser un objeto JSON")
    normalized = {}
    for model_id, url in parsed.items():
        if not isinstance(model_id, str) or not isinstance(url, str):
            raise ValueError("--model-route-overrides solo acepta pares string->string")
        normalized[model_id] = normalize_base_url(url)
    return normalized


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
            return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return None


def validate_labels(raw_result: dict) -> Optional[dict]:
    nivel = str(raw_result.get("nivel_tecnico", "")).strip().lower()
    urgencia = str(raw_result.get("urgencia", "")).strip().lower()
    if nivel not in VALID_NIVELES or urgencia not in VALID_URGENCIAS:
        return None
    return {"nivel_tecnico": nivel, "urgencia": urgencia}


def normalize_spanish_text(text: str) -> str:
    # Normaliza acentos y mayusculas para matching robusto con listas de terminos.
    lowered = (text or "").lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def urgency_signal(text: str) -> bool:
    normalized = normalize_spanish_text(text)
    strong_hits = sum(1 for term in URGENCY_STRONG_TERMS if term in normalized)
    weak_hits = sum(1 for term in URGENCY_WEAK_TERMS if term in normalized)
    return strong_hits >= 1 or weak_hits >= 2


def advanced_signal(text: str, tags: List[str]) -> bool:
    normalized = normalize_spanish_text(text)
    strong_hits = sum(1 for term in ADVANCED_STRONG_TERMS if term in normalized)
    weak_hits = sum(1 for term in ADVANCED_WEAK_TERMS if term in normalized)
    tag_hits = sum(1 for tag in tags if normalize_spanish_text(str(tag)) in ADVANCED_HINT_TAGS)
    return strong_hits >= 1 or weak_hits >= 2 or tag_hits >= 1


def find_candidate_indices_for_calibration(labeled: List[dict], so_questions_by_id: Dict[int, dict]) -> List[int]:
    indices: List[int] = []
    for idx, row in enumerate(labeled):
        qid = row.get("question_id")
        source = so_questions_by_id.get(qid, {})
        title = source.get("title", "") or row.get("title", "")
        body = source.get("body", "")
        tags = source.get("tags", row.get("tags", []))
        text = f"{title} {body} {' '.join(tags)}"

        urgency_candidate = row.get("urgencia") != "alta" and urgency_signal(text)
        advanced_candidate = row.get("nivel_tecnico") != "avanzado" and advanced_signal(text, tags)
        if urgency_candidate or advanced_candidate:
            indices.append(idx)
    return indices


def analyze_calibration_candidates(labeled: List[dict], so_questions_by_id: Dict[int, dict]) -> None:
    urg_candidates = 0
    adv_candidates = 0
    both = 0
    for row in labeled:
        qid = row.get("question_id")
        source = so_questions_by_id.get(qid, {})
        title = source.get("title", "") or row.get("title", "")
        body = source.get("body", "")
        tags = source.get("tags", row.get("tags", []))
        text = f"{title} {body} {' '.join(tags)}"
        u = row.get("urgencia") != "alta" and urgency_signal(text)
        a = row.get("nivel_tecnico") != "avanzado" and advanced_signal(text, tags)
        if u:
            urg_candidates += 1
        if a:
            adv_candidates += 1
        if u and a:
            both += 1
    print("\nAnalisis de candidatos para calibracion:")
    print(f"  urgencia-alta candidatos: {urg_candidates}")
    print(f"  nivel-avanzado candidatos: {adv_candidates}")
    print(f"  interseccion: {both}")


def call_copilot_chat(
    client,
    model: str,
    prompt: str,
    max_retries: int,
    retry_base_seconds: int,
) -> Optional[dict]:
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
            if parsed is None:
                raise ValueError("No se pudo parsear JSON de la respuesta.")
            valid = validate_labels(parsed)
            if valid is None:
                raise ValueError("JSON parseado, pero etiquetas fuera de esquema esperado.")
            return valid
        except Exception as exc:
            msg = str(exc)
            is_retryable = "429" in msg or "rate" in msg.lower() or "timeout" in msg.lower()
            if attempt < max_retries - 1 and is_retryable:
                wait_seconds = retry_base_seconds * (attempt + 1)
                time.sleep(wait_seconds)
                continue
            return None
    return None


def label_questions(args) -> bool:
    api_key = args.api_key or "dummy"
    base_url = normalize_base_url(args.base_url)
    route_overrides = load_model_route_overrides(args.model_route_overrides)
    requested_models = parse_models_arg(args.models)

    print("=" * 72)
    print("FASE 3 - ETIQUETADO DATASET CON COPILOT")
    print("=" * 72)
    print(f"Base URL por defecto: {base_url}")

    if args.list_models:
        available_models = fetch_available_models(base_url=base_url, api_key=api_key)
        print("\nModelos disponibles en /v1/models:")
        for model_id in available_models:
            print(f"  - {model_id}")
        return True

    so_path = RAW_DIR / "so_questions.json"
    if not so_path.exists():
        print("\nError: no existe dataset/raw/so_questions.json")
        return False
    with open(so_path, encoding="utf-8") as f:
        so_questions = json.load(f)
    so_questions = so_questions[: args.max_examples]
    so_questions_by_id = {q.get("question_id"): q for q in so_questions if q.get("question_id") is not None}

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.analyze_calibration:
        if not output_path.exists():
            print(f"Error: no existe archivo de salida para analizar: {output_path}")
            return False
        with open(output_path, encoding="utf-8") as f:
            labeled_for_analysis = json.load(f)
        analyze_calibration_candidates(labeled_for_analysis, so_questions_by_id)
        return True

    available_models = fetch_available_models(base_url=base_url, api_key=api_key)

    resolved_models: List[str] = []
    unresolved_models: List[str] = []
    for model in requested_models:
        resolved = resolve_model_id(model, available_models)
        if resolved:
            resolved_models.append(resolved)
        else:
            unresolved_models.append(model)

    if unresolved_models:
        print(f"\nError: modelos no disponibles: {', '.join(unresolved_models)}")
        print("Sugerencia: ejecuta --list-models para ver IDs reales del proxy.")
        return False

    model_to_base_url = {
        model_id: route_overrides.get(model_id, route_overrides.get(model_id.split("-")[0], base_url))
        for model_id in resolved_models
    }

    # Inicializar clientes por base_url para soportar mezcla de endpoints.
    clients_by_base_url = {}
    for model_id, model_base_url in model_to_base_url.items():
        if model_base_url not in clients_by_base_url:
            clients_by_base_url[model_base_url] = get_openai_client(
                base_url=model_base_url,
                api_key=api_key,
            )

    print(f"Modelos solicitados: {', '.join(requested_models)}")
    print(f"Modelos resueltos: {', '.join(resolved_models)}")

    existing_records = []
    existing_ids = set()
    normalized_existing = False
    if args.resume and output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            existing_records = json.load(f)
        for row in existing_records:
            if "model_used" not in row:
                row["model_used"] = "legacy_existing"
                normalized_existing = True
            if not row.get("body"):
                qid = row.get("question_id")
                source = so_questions_by_id.get(qid, {})
                if source.get("body"):
                    row["body"] = html.unescape(source.get("body", ""))
                    normalized_existing = True
            qid = row.get("question_id")
            if qid is not None:
                existing_ids.add(qid)
        if normalized_existing:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(existing_records, f, ensure_ascii=False, indent=2)

    pending_questions = [q for q in so_questions if q.get("question_id") not in existing_ids]
    print(f"Total objetivo: {len(so_questions)}")
    print(f"Ya etiquetados (resume): {len(existing_records)}")
    print(f"Pendientes en esta corrida: {len(pending_questions)}\n")

    labeled = list(existing_records)
    errors = 0
    by_model = Counter()
    start_time = time.time()

    for idx, question in enumerate(pending_questions, start=1):
        model = resolved_models[(len(labeled) + idx - 1) % len(resolved_models)]
        model_base_url = model_to_base_url[model]
        client = clients_by_base_url[model_base_url]

        title = html.unescape(question.get("title", ""))
        body_full = html.unescape(question.get("body", "") or "")
        body = body_full[:500]
        tags = ", ".join(html.unescape(tag) for tag in question.get("tags", []))

        prompt = LABELING_PROMPT.format(title=title, body=body, tags=tags)
        result = call_copilot_chat(
            client=client,
            model=model,
            prompt=prompt,
            max_retries=args.max_retries,
            retry_base_seconds=args.retry_base_seconds,
        )

        if result is None:
            errors += 1
        else:
            labeled.append(
                {
                    "question_id": question.get("question_id"),
                    "title": title,
                    "body": body_full,
                    "tags": question.get("tags", []),
                    "domain_synapse": question.get("domain_synapse", "general"),
                    "nivel_tecnico": result["nivel_tecnico"],
                    "urgencia": result["urgencia"],
                    "model_used": model,
                }
            )
            by_model[model] += 1

            # Persistencia incremental para poder reanudar sin perder progreso.
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(labeled, f, ensure_ascii=False, indent=2)

        if idx % args.batch_size == 0 or idx == len(pending_questions):
            elapsed = max(1, time.time() - start_time)
            rate = idx / elapsed * 60
            print(
                f"{idx:>4}/{len(pending_questions)} | "
                f"{100 * idx / max(1, len(pending_questions)):>5.1f}% | "
                f"{rate:>5.1f} req/min | errores={errors}"
            )

        time.sleep(args.delay_seconds)

    if args.calibration_pass:
        niveles_now = Counter(row["nivel_tecnico"] for row in labeled if row.get("nivel_tecnico"))
        urgencias_now = Counter(row["urgencia"] for row in labeled if row.get("urgencia"))
        advanced_deficit = max(0, args.target_min_avanzado - niveles_now.get("avanzado", 0))
        high_deficit = max(0, args.target_min_alta - urgencias_now.get("alta", 0))

        if advanced_deficit > 0 or high_deficit > 0:
            print("\nIniciando calibracion dirigida...")
            print(f"  deficit avanzado={advanced_deficit}, deficit alta={high_deficit}")

            candidates = find_candidate_indices_for_calibration(labeled, so_questions_by_id)
            candidates = candidates[: args.max_calibration_candidates]
            strict_model = resolved_models[0]
            strict_client = clients_by_base_url[model_to_base_url[strict_model]]
            changes = 0

            for idx in candidates:
                row = labeled[idx]
                qid = row.get("question_id")
                source = so_questions_by_id.get(qid, {})
                title = html.unescape(source.get("title", row.get("title", "")))
                body = html.unescape((source.get("body", "") or "")[:800])
                tags = ", ".join(source.get("tags", row.get("tags", [])))

                calibration_prompt = CALIBRATION_PROMPT.format(title=title, body=body, tags=tags)
                recalibrated = call_copilot_chat(
                    client=strict_client,
                    model=strict_model,
                    prompt=calibration_prompt,
                    max_retries=args.max_retries,
                    retry_base_seconds=args.retry_base_seconds,
                )
                if recalibrated is None:
                    continue

                prev_nivel = row.get("nivel_tecnico")
                prev_urg = row.get("urgencia")
                new_nivel = recalibrated["nivel_tecnico"]
                new_urg = recalibrated["urgencia"]

                # Solo aceptar cambios que empujen en direccion de cubrir deficits.
                accept_nivel = (
                    new_nivel == "avanzado" and prev_nivel != "avanzado" and advanced_deficit > 0
                )
                accept_urg = new_urg == "alta" and prev_urg != "alta" and high_deficit > 0

                if not accept_nivel and not accept_urg:
                    continue

                if accept_nivel:
                    row["nivel_tecnico"] = "avanzado"
                    advanced_deficit -= 1
                if accept_urg:
                    row["urgencia"] = "alta"
                    high_deficit -= 1
                row["model_used"] = f"{strict_model}:calibrated"
                changes += 1

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(labeled, f, ensure_ascii=False, indent=2)

                if advanced_deficit <= 0 and high_deficit <= 0:
                    break

            print(
                f"Calibracion aplicada: cambios={changes}, "
                f"deficit_final_avanzado={max(0, advanced_deficit)}, "
                f"deficit_final_alta={max(0, high_deficit)}"
            )

    elapsed = max(1, time.time() - start_time)
    niveles = Counter(row["nivel_tecnico"] for row in labeled if row.get("nivel_tecnico"))
    urgencias = Counter(row["urgencia"] for row in labeled if row.get("urgencia"))

    print("\n" + "=" * 72)
    print("RESUMEN")
    print("=" * 72)
    print(f"Archivo salida: {output_path}")
    print(f"Etiquetados totales: {len(labeled)} / {len(so_questions)}")
    print(f"Errores en corrida: {errors}")
    print(f"Tiempo corrida: {elapsed / 60:.1f} min")
    print(f"Velocidad media: {len(pending_questions) / elapsed * 60:.1f} req/min")
    print("\nPor modelo:")
    for model_id, total in by_model.most_common():
        print(f"  {model_id}: {total}")
    print("\nNivel tecnico:")
    for key, total in niveles.most_common():
        print(f"  {key}: {total}")
    print("\nUrgencia:")
    for key, total in urgencias.most_common():
        print(f"  {key}: {total}")

    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fase 3: etiquetar nivel_tecnico y urgencia via Copilot API proxy."
    )
    parser.add_argument("--max-examples", type=int, default=250)
    parser.add_argument("--models", type=str, default=",".join(DEFAULT_MODELS))
    parser.add_argument("--base-url", type=str, default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key", type=str, default=os.getenv("COPILOT_API_KEY", "dummy"))
    parser.add_argument(
        "--model-route-overrides",
        type=str,
        default=os.getenv("COPILOT_MODEL_ROUTE_OVERRIDES", "{}"),
        help='JSON model->base_url. Ej: {"gpt-5-mini":"http://localhost:4141/v1"}',
    )
    parser.add_argument("--output", type=str, default="dataset/processed/labeled.json")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--analyze-calibration", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-base-seconds", type=int, default=10)
    parser.add_argument("--calibration-pass", action="store_true", default=False)
    parser.add_argument("--target-min-avanzado", type=int, default=10)
    parser.add_argument("--target-min-alta", type=int, default=10)
    parser.add_argument("--max-calibration-candidates", type=int, default=120)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    success = label_questions(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
