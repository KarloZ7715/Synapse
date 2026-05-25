#!/usr/bin/env python3
"""
Etiquetado con GitHub Copilot (via copilot-api proxy).

Uso rapido:
1. Iniciar proxy: npx copilot-api@latest start --port 4141
2. Probar modelos disponibles:
   python dataset/scripts/label_with_copilot.py --list-models
3. Etiquetar reanudando desde dataset/processed/labeled.json:
   python dataset/scripts/label_with_copilot.py
   (por defecto considera hasta 2500 filas de so_questions.json; usar --max-examples si subes más el extract)
4. Opcional: incluir emocion en el JSON del modelo:
   python dataset/scripts/label_with_copilot.py --label-emotion
5. Opcional: pasada de calibración para subir colas de `avanzado`, `alta` y (con `--target-min-baja`) `baja`:
   python dataset/scripts/label_with_copilot.py --calibration-pass --target-min-avanzado 120 --target-min-alta 140 --target-min-baja 160
6. Opcional: backfill solo de emocion en filas existentes:
   python dataset/scripts/label_with_copilot.py --emotion-backfill-only --max-examples 400
"""

import argparse
import html
import json
import os
import sys
import time
import unicodedata
from collections import Counter
from functools import partial
from pathlib import Path
from typing import Callable, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _load_repo_dotenv() -> None:
    """Carga opcional `repo/.env` sin python-dotenv; no pisa variables ya definidas."""
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
NN_SCRIPT_DIR = PROJECT_ROOT / "neural_network" / "scripts"
if str(NN_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(NN_SCRIPT_DIR))
from training_labels import EMOCION
RAW_DIR = PROJECT_ROOT / "dataset" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "dataset" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LABELING_AUDIT_DIR = PROCESSED_DIR / "labeling_audit"

DEFAULT_BASE_URL = os.getenv("COPILOT_BASE_URL", "http://localhost:4141/v1")
DEFAULT_MODELS = ["gpt-5-mini", "gpt-4.1", "gpt-4o"]
VALID_NIVELES = {"principiante", "intermedio", "avanzado"}
VALID_URGENCIAS = {"baja", "media", "alta"}
VALID_EMOCIONES = frozenset(EMOCION)
EMOCIONES_DESC = ", ".join(EMOCION)
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

LOW_URGENCY_HINT_TERMS = [
    "curiosidad",
    "aprender",
    "tutorial",
    "concepto",
    "libro",
    "recomendacion",
    "empezar",
    "diferencia entre",
    "que es",
    "buenas practicas",
    "solo pregunto",
    "por saber",
]


def low_urgency_signal(text: str, _tags: List[str]) -> bool:
    """Texto exploratorio sin señales fuertes de urgencia (candidato a re-etiquetar como baja)."""
    if urgency_signal(text):
        return False
    normalized = normalize_spanish_text(text)
    return any(term in normalized for term in LOW_URGENCY_HINT_TERMS)


LABELING_PROMPT = """Analiza esta pregunta de programacion en español:

Titulo: {title}
Cuerpo: {body}
Tags: {tags}

Determina unicamente:

1. Nivel tecnico del autor:
   - principiante: conceptos basicos, confusion con fundamentos
   - intermedio: frameworks, patrones, integraciones comunes
   - avanzado: SOLO si hay tradeoffs de arquitectura, concurrencia real, optimizacion no trivial, o analisis de complejidad (Big-O). No uses "avanzado" por nombrar un framework popular.

2. Urgencia:
   - baja: curiosidad, sin presion
   - media: necesita resolver pero sin urgencia extrema
   - alta: bloqueo explicito, deadline/entrega/examen, o desesperacion clara

Ejemplos cortos:
- "Necesito entregar el proyecto mañana y el build falla" -> urgencia alta (deadline), nivel intermedio salvo que el fallo sea de concurrencia/arquitectura.
- "Comparar complejidad O(n log n) vs O(n^2) en mi sort" -> nivel avanzado, urgencia media salvo bloqueo declarado.

Reglas:
- No uses "avanzado" solo por mencionar React/Python/Docker.
- Usa "alta" solo si hay señales de bloqueo/presion temporal explicita.

Responde SOLO con JSON valido:
{{"nivel_tecnico": "principiante|intermedio|avanzado", "urgencia": "baja|media|alta"}}"""

LABELING_PROMPT_EMOTION = """Analiza esta pregunta de programacion en español:

Titulo: {title}
Cuerpo: {body}
Tags: {tags}

Determina:

1. Nivel tecnico del autor:
   - principiante: conceptos basicos, confusion con fundamentos
   - intermedio: frameworks, patrones, integraciones comunes
   - avanzado: SOLO tradeoffs de arquitectura, concurrencia real, optimizacion no trivial, o Big-O. No por tecnologia de moda.

2. Urgencia:
   - baja: curiosidad, sin presion
   - media: necesita resolver pero sin urgencia extrema
   - alta: bloqueo explicito, deadline/entrega/examen, o desesperacion clara

3. Emocion predominante del autor (una sola), segun taxonomia Synapse:
   {emociones}

Reglas emocion (mutuamente excluyentes: elige la mas fuerte):
- frustracion: enfado, bloqueo tecnico, algo "no funciona"
- confusion: no entiende el concepto o el error
- curiosidad: exploracion, "como/por que" sin angustia fuerte
- ansiedad: tiempo limitado, examen, entrega, presion
- motivacion: avance, aprendizaje activo, energia positiva (no confianza tranquila)
- abrumado: demasiada informacion, sobrecarga
- confiado: cree tener la solucion correcta, tono seguro, pide validacion de enfoque (ej: "¿va bien si hago X?")
- desesperado: se rinde, "imposible", desolacion
- neutral: tono tecnico plano sin carga emocional clara

Ejemplos:
- "Llevo horas y sigo sin compilar; entrego hoy" -> ansiedad o frustracion, urgencia alta.
- "Creo que mi diseno con colas es correcto, ¿le ves fallos?" -> confiado, urgencia baja/media.

Responde SOLO con JSON valido:
{{"nivel_tecnico": "principiante|intermedio|avanzado", "urgencia": "baja|media|alta", "emocion": "<una de la lista>"}}"""

EMOTION_BACKFILL_PROMPT = """Lee esta pregunta de programacion en español y elige UNA emocion del vocabulario Synapse.

Titulo: {title}
Cuerpo: {body}
Tags: {tags}

Vocabulario permitido (exactamente una): {emociones}

Responde SOLO con JSON valido:
{{"emocion": "<una de la lista>"}}"""

CALIBRATION_PROMPT = """Re-evalua esta pregunta de programacion en español para detectar subestimaciones.

Titulo: {title}
Cuerpo: {body}
Tags: {tags}
Senales detectadas por pre-filtro: {signals}

Reglas estrictas:
- Marca urgencia="alta" solo si hay señales claras de bloqueo o presion temporal (ej: urgente, entrega, examen, bloqueado, desesperado).
- Marca nivel_tecnico="avanzado" si el problema implica optimizacion no trivial, complejidad algoritmica (Big-O), concurrencia, arquitectura con tradeoffs, diagnostico de rendimiento, seguridad no trivial, despliegue/orquestacion complejo o debugging profundo con varias capas.
- No marques "alta" solo por la palabra "error" o "ayuda" si no hay contexto de bloqueo real.
- Si hay tags o texto de arquitectura, concurrencia, complejidad, rendimiento, Kubernetes, seguridad, OAuth/JWT o infraestructura, considera "avanzado" aunque el autor no use vocabulario academico.
- Si no hay evidencia suficiente para "alta" o "avanzado", usa "media/baja" e "intermedio/principiante".

Responde SOLO con JSON valido:
{{"nivel_tecnico": "principiante|intermedio|avanzado", "urgencia": "baja|media|alta"}}"""


def body_snippet_for_llm(
    body_full: str,
    *,
    head_chars: int = 320,
    tail_chars: int = 240,
    hard_cap: int = 1400,
) -> str:
    """Título + cuerpo: conserva inicio y final del body para no perder deadlines al final."""
    t = (body_full or "").strip()
    if not t:
        return ""
    if len(t) <= head_chars + tail_chars + 24:
        return t[:hard_cap]
    head = t[:head_chars].rsplit(" ", 1)[0]
    tail = t[-tail_chars:].split(" ", 1)[-1]
    out = head + "\n...[texto omitido]...\n" + tail
    return out[:hard_cap]


def append_labeling_audit(record: Dict[str, object]) -> None:
    LABELING_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path = LABELING_AUDIT_DIR / "copilot_failures.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


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


def validate_labels(raw_result: dict, *, require_emotion: bool) -> Optional[dict]:
    nivel = str(raw_result.get("nivel_tecnico", "")).strip().lower()
    urgencia = str(raw_result.get("urgencia", "")).strip().lower()
    if nivel not in VALID_NIVELES or urgencia not in VALID_URGENCIAS:
        return None
    out: Dict[str, str] = {"nivel_tecnico": nivel, "urgencia": urgencia}
    if require_emotion:
        emo = str(raw_result.get("emocion", "")).strip().lower()
        if emo not in VALID_EMOCIONES:
            return None
        out["emocion"] = emo
    return out


def validate_emotion_only(raw_result: dict) -> Optional[dict]:
    emo = str(raw_result.get("emocion", "")).strip().lower()
    if emo not in VALID_EMOCIONES:
        return None
    return {"emocion": emo}


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
        baja_candidate = row.get("urgencia") != "baja" and low_urgency_signal(text, tags)
        if urgency_candidate or advanced_candidate or baja_candidate:
            indices.append(idx)
    return indices


def calibration_signals_for_row(row: dict, so_questions_by_id: Dict[int, dict]) -> Dict[str, bool]:
    qid = row.get("question_id")
    source = so_questions_by_id.get(qid, {})
    title = source.get("title", "") or row.get("title", "")
    body = source.get("body", "") or row.get("body", "")
    tags = source.get("tags", row.get("tags", []))
    text = f"{title} {body} {' '.join(tags)}"
    return {
        "advanced": row.get("nivel_tecnico") != "avanzado" and advanced_signal(text, tags),
        "high_urgency": row.get("urgencia") != "alta" and urgency_signal(text),
        "low_urgency": row.get("urgencia") != "baja" and low_urgency_signal(text, tags),
    }


def ranked_candidate_indices_for_calibration(
    labeled: List[dict],
    so_questions_by_id: Dict[int, dict],
    *,
    need_advanced: bool,
    need_high: bool,
    need_low: bool,
) -> List[int]:
    scored: List[tuple[int, int]] = []
    for idx, row in enumerate(labeled):
        signals = calibration_signals_for_row(row, so_questions_by_id)
        score = 0
        if need_advanced and signals["advanced"]:
            score += 100
        if need_high and signals["high_urgency"]:
            score += 50
        if need_low and signals["low_urgency"]:
            score += 30
        if score:
            scored.append((-score, idx))
    return [idx for _, idx in sorted(scored)]


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
    *,
    max_tokens: int = 120,
    validator: Callable[[dict], Optional[dict]],
    audit_context: Optional[Dict[str, object]] = None,
) -> Optional[dict]:
    last_content: Optional[str] = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            last_content = content
            parsed = clean_json(content)
            if parsed is None:
                if audit_context is not None:
                    append_labeling_audit(
                        {
                            **audit_context,
                            "attempt": attempt + 1,
                            "stage": "json_parse",
                            "raw_excerpt": (content or "")[:1200],
                        }
                    )
                raise ValueError("No se pudo parsear JSON de la respuesta.")
            valid = validator(parsed)
            if valid is None:
                if audit_context is not None:
                    append_labeling_audit(
                        {
                            **audit_context,
                            "attempt": attempt + 1,
                            "stage": "schema_validation",
                            "parsed_keys": list(parsed.keys()),
                        }
                    )
                raise ValueError("JSON parseado, pero etiquetas fuera de esquema esperado.")
            return valid
        except Exception as exc:
            msg = str(exc)
            if audit_context is not None and attempt == max_retries - 1:
                append_labeling_audit(
                    {
                        **audit_context,
                        "attempt": attempt + 1,
                        "stage": "final_failure",
                        "message": msg[:800],
                        "raw_excerpt": (last_content or "")[:1200],
                    }
                )
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
        so_full = json.load(f)
    so_by_id_all = {
        q.get("question_id"): q
        for q in so_full
        if q.get("question_id") is not None
    }
    so_questions = so_full[: args.max_examples]

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
        analyze_calibration_candidates(labeled_for_analysis, so_by_id_all)
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

    v_no_emotion = partial(validate_labels, require_emotion=False)
    v_with_emotion = partial(validate_labels, require_emotion=True)

    if args.emotion_backfill_only:
        if not output_path.exists():
            print("Error: --emotion-backfill-only requiere un labeled.json existente.")
            return False
        with open(output_path, encoding="utf-8") as f:
            labeled = json.load(f)
        pending_bf: List[tuple[int, dict]] = []
        for row_idx, row in enumerate(labeled):
            emo = str(row.get("emocion", "")).strip().lower()
            if emo in VALID_EMOCIONES:
                continue
            qid = row.get("question_id")
            if qid is not None and qid in so_by_id_all:
                question = so_by_id_all[qid]
            else:
                title_m = str(row.get("title") or "").strip()
                body_m = str(row.get("body") or "").strip()
                if len(title_m) < 4 or len(body_m) < 20:
                    continue
                tags_raw = row.get("tags") or []
                if isinstance(tags_raw, str):
                    tags_list = [tags_raw]
                else:
                    tags_list = list(tags_raw)
                question = {
                    "question_id": qid,
                    "title": title_m,
                    "body": body_m,
                    "tags": tags_list,
                }
            pending_bf.append((row_idx, question))
        pending_bf = pending_bf[: args.max_examples]
        print(f"Backfill emocion: {len(pending_bf)} filas (tope --max-examples).\n")
        errors = 0
        by_model = Counter()
        start_time = time.time()
        for j, (row_idx, question) in enumerate(pending_bf, start=1):
            model = resolved_models[(j - 1) % len(resolved_models)]
            model_base_url = model_to_base_url[model]
            client = clients_by_base_url[model_base_url]
            title = html.unescape(question.get("title", ""))
            body_full = html.unescape(question.get("body", "") or "")
            body = body_snippet_for_llm(body_full)
            tags = ", ".join(html.unescape(tag) for tag in question.get("tags", []))
            prompt = EMOTION_BACKFILL_PROMPT.format(
                title=title, body=body, tags=tags, emociones=EMOCIONES_DESC
            )
            result = call_copilot_chat(
                client=client,
                model=model,
                prompt=prompt,
                max_retries=args.max_retries,
                retry_base_seconds=args.retry_base_seconds,
                max_tokens=96,
                validator=validate_emotion_only,
                audit_context={
                    "phase": "emotion_backfill",
                    "row_index": row_idx,
                    "question_id": question.get("question_id"),
                    "model": model,
                },
            )
            if result is None:
                errors += 1
            else:
                labeled[row_idx]["emocion"] = result["emocion"]
                prev = str(labeled[row_idx].get("model_used", "") or "")
                suffix = f"{model}:emotion_bf"
                labeled[row_idx]["model_used"] = f"{prev}:{suffix}" if prev else suffix
                by_model[model] += 1
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(labeled, f, ensure_ascii=False, indent=2)
            if j % args.batch_size == 0 or j == len(pending_bf):
                elapsed = max(1, time.time() - start_time)
                rate = j / elapsed * 60
                print(
                    f"{j:>4}/{len(pending_bf)} | "
                    f"{100 * j / max(1, len(pending_bf)):>5.1f}% | "
                    f"{rate:>5.1f} req/min | errores={errors}"
                )
            time.sleep(args.delay_seconds)
        emo_c = Counter(str(r.get("emocion", "")).lower() for r in labeled if r.get("emocion"))
        print("\n" + "=" * 72)
        print("RESUMEN BACKFILL EMOCION")
        print("=" * 72)
        print(f"Archivo salida: {output_path}")
        print(f"Filas procesadas: {len(pending_bf)} | errores: {errors}")
        print("\nEmociones (conteo en archivo completo):")
        for k, v in emo_c.most_common():
            print(f"  {k}: {v}")
        return True

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
                source = so_by_id_all.get(qid, {})
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
    print(f"Pendientes en esta corrida: {len(pending_questions)}")
    if args.label_emotion:
        print("Etiquetado con emocion (LLM): activado (--label-emotion).")
    print()

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
        body = body_snippet_for_llm(body_full)
        tags = ", ".join(html.unescape(tag) for tag in question.get("tags", []))

        if args.label_emotion:
            prompt = LABELING_PROMPT_EMOTION.format(
                title=title, body=body, tags=tags, emociones=EMOCIONES_DESC
            )
            max_tok = 220
            validator = v_with_emotion
        else:
            prompt = LABELING_PROMPT.format(title=title, body=body, tags=tags)
            max_tok = 120
            validator = v_no_emotion
        result = call_copilot_chat(
            client=client,
            model=model,
            prompt=prompt,
            max_retries=args.max_retries,
            retry_base_seconds=args.retry_base_seconds,
            max_tokens=max_tok,
            validator=validator,
            audit_context={
                "phase": "label_primary",
                "question_id": question.get("question_id"),
                "model": model,
                "label_emotion": bool(args.label_emotion),
            },
        )

        if result is None:
            errors += 1
        else:
            new_row: Dict[str, object] = {
                "question_id": question.get("question_id"),
                "title": title,
                "body": body_full,
                "tags": question.get("tags", []),
                "domain_synapse": question.get("domain_synapse", "general"),
                "nivel_tecnico": result["nivel_tecnico"],
                "urgencia": result["urgencia"],
                "model_used": model,
            }
            if args.label_emotion:
                new_row["emocion"] = result["emocion"]
            labeled.append(new_row)
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
        baja_deficit = max(0, args.target_min_baja - urgencias_now.get("baja", 0))

        if advanced_deficit > 0 or high_deficit > 0 or baja_deficit > 0:
            print("\nIniciando calibracion dirigida...")
            print(
                f"  deficit avanzado={advanced_deficit}, deficit alta={high_deficit}, deficit baja={baja_deficit}"
            )

            candidates = ranked_candidate_indices_for_calibration(
                labeled,
                so_by_id_all,
                need_advanced=advanced_deficit > 0,
                need_high=high_deficit > 0,
                need_low=baja_deficit > 0,
            )
            candidates = candidates[: args.max_calibration_candidates]
            strict_model = resolved_models[0]
            strict_client = clients_by_base_url[model_to_base_url[strict_model]]
            changes = 0

            for idx in candidates:
                row = labeled[idx]
                qid = row.get("question_id")
                source = so_by_id_all.get(qid, {})
                title = html.unescape(source.get("title", row.get("title", "")))
                body = body_snippet_for_llm(html.unescape((source.get("body", "") or "")), hard_cap=1600)
                tags = ", ".join(source.get("tags", row.get("tags", [])))

                signals = calibration_signals_for_row(row, so_by_id_all)
                signal_text = ", ".join(k for k, v in signals.items() if v) or "ninguna"
                calibration_prompt = CALIBRATION_PROMPT.format(
                    title=title,
                    body=body,
                    tags=tags,
                    signals=signal_text,
                )
                recalibrated = call_copilot_chat(
                    client=strict_client,
                    model=strict_model,
                    prompt=calibration_prompt,
                    max_retries=args.max_retries,
                    retry_base_seconds=args.retry_base_seconds,
                    max_tokens=120,
                    validator=v_no_emotion,
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
                accept_alta = new_urg == "alta" and prev_urg != "alta" and high_deficit > 0
                accept_baja = new_urg == "baja" and prev_urg != "baja" and baja_deficit > 0

                if not accept_nivel and not accept_alta and not accept_baja:
                    continue

                if accept_nivel:
                    row["nivel_tecnico"] = "avanzado"
                    advanced_deficit -= 1
                if accept_alta:
                    row["urgencia"] = "alta"
                    high_deficit -= 1
                if accept_baja:
                    row["urgencia"] = "baja"
                    baja_deficit -= 1
                row["model_used"] = f"{strict_model}:calibrated"
                changes += 1

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(labeled, f, ensure_ascii=False, indent=2)

                if advanced_deficit <= 0 and high_deficit <= 0 and baja_deficit <= 0:
                    break

            print(
                f"Calibracion aplicada: cambios={changes}, "
                f"deficit_final_avanzado={max(0, advanced_deficit)}, "
                f"deficit_final_alta={max(0, high_deficit)}, "
                f"deficit_final_baja={max(0, baja_deficit)}"
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
    if any(r.get("emocion") for r in labeled):
        emo_c = Counter(str(r.get("emocion", "")).lower() for r in labeled if r.get("emocion"))
        print("\nEmocion (filas con campo):")
        for key, total in emo_c.most_common():
            print(f"  {key}: {total}")

    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fase 3: etiquetar nivel_tecnico, urgencia y (opcional) emocion via Copilot API proxy."
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=2500,
        help="Cuántas filas de so_questions.json considerar (debe cubrir el tope de extract_so; default 2500).",
    )
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
    parser.add_argument(
        "--target-min-baja",
        type=int,
        default=0,
        help="Mínimo de filas con urgencia=baja tras calibración (0=omitir eje baja).",
    )
    parser.add_argument("--max-calibration-candidates", type=int, default=120)
    parser.add_argument(
        "--label-emotion",
        action="store_true",
        help="Incluye emocion Synapse en el JSON del LLM (nivel, urgencia, emocion).",
    )
    parser.add_argument(
        "--emotion-backfill-only",
        action="store_true",
        help="Solo rellena emocion en filas existentes de labeled.json que no la tengan (moderado/cheap).",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    success = label_questions(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
