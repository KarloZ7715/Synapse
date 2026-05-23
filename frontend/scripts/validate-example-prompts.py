#!/usr/bin/env python3
"""
Valida que cada ejemplo del carrusel obtenga buena confianza con synapse_textcnn.onnx.

Requisitos:
  pip install onnxruntime numpy
  pnpm sync:model  (copia ONNX + vocab a frontend/public/models)

Uso:
  python3 frontend/scripts/validate-example-prompts.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_PATH = FRONTEND_ROOT / "src/config/examplePrompts.json"
VOCAB_PATH = FRONTEND_ROOT / "public/models/vocab.json"
ONNX_PATH = FRONTEND_ROOT / "public/models/synapse_textcnn.onnx"

MIN_CONFIDENCE = 0.88
MIN_HEAD_CONFIDENCE = 0.65

_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)

LABELS = {
    "nivel_tecnico": ["principiante", "intermedio", "avanzado"],
    "urgencia": ["baja", "media", "alta"],
    "emocion": [
        "frustracion",
        "confusion",
        "curiosidad",
        "ansiedad",
        "motivacion",
        "abrumado",
        "confiado",
        "desesperado",
        "neutral",
    ],
    "dominio": [
        "backend",
        "frontend",
        "bases_de_datos",
        "movil",
        "devops",
        "data_science",
        "sistemas_seguridad",
        "general",
    ],
}
HEAD_ORDER = ("nivel_tecnico", "urgencia", "emocion", "dominio")
ONNX_OUT = (
    "logits_nivel_tecnico",
    "logits_urgencia",
    "logits_emocion",
    "logits_dominio",
)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text.lower()) if t.strip()]


def encode_text(text: str, word2idx: dict[str, int], max_len: int) -> list[int]:
    unk = word2idx.get("<unk>", 1)
    return [word2idx.get(t, unk) for t in tokenize(text)[:max_len]]


def softmax(logits: np.ndarray) -> np.ndarray:
    x = logits - logits.max()
    e = np.exp(x)
    return e / e.sum()


def classify(sess, word2idx: dict[str, int], max_len: int, pad_id: int, text: str):
    ids = encode_text(text, word2idx, max_len)
    ids = ids[:max_len] + [pad_id] * (max_len - len(ids))
    outs = sess.run(None, {"input_ids": np.array([ids], dtype=np.int64)})
    omap = dict(zip([o.name for o in sess.get_outputs()], outs))
    head_conf: dict[str, float] = {}
    labels: dict[str, str] = {}
    for i, head in enumerate(HEAD_ORDER):
        logits = np.asarray(omap[ONNX_OUT[i]], dtype=np.float32).reshape(-1)
        probs = softmax(logits)
        idx = int(probs.argmax())
        labels[head] = LABELS[head][idx]
        head_conf[head] = float(probs[idx])
    conf = math.prod(head_conf.values()) ** 0.25
    return labels, head_conf, conf


def main() -> int:
    try:
        import onnxruntime as ort
    except ImportError:
        print("Instala onnxruntime: pip install onnxruntime", file=sys.stderr)
        return 1

    if not PROMPTS_PATH.is_file():
        print(f"No existe {PROMPTS_PATH}", file=sys.stderr)
        return 1
    if not VOCAB_PATH.is_file() or not ONNX_PATH.is_file():
        print("Ejecuta `pnpm sync:model` antes de validar.", file=sys.stderr)
        return 1

    prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    vocab = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
    word2idx = vocab["word2idx"]
    max_len = int(vocab.get("max_len", 160))
    pad_id = int(word2idx["<pad>"])

    sess = ort.InferenceSession(str(ONNX_PATH), providers=["CPUExecutionProvider"])

    failed = 0
    print(f"Validando {len(prompts)} ejemplos (umbral confianza >= {MIN_CONFIDENCE:.0%}, cabeza min >= {MIN_HEAD_CONFIDENCE:.0%})\n")

    for item in prompts:
        text = item["text"]
        expected_domain = item["domain"]
        labels, head_conf, conf = classify(sess, word2idx, max_len, pad_id, text)
        min_head = min(head_conf.values())
        domain_ok = labels["dominio"] == expected_domain
        conf_ok = conf >= MIN_CONFIDENCE
        head_ok = min_head >= MIN_HEAD_CONFIDENCE
        ok = domain_ok and conf_ok and head_ok

        status = "OK" if ok else "FAIL"
        print(
            f"[{status}] {item['id']}: conf={conf * 100:.1f}% "
            f"min_head={min_head * 100:.0f}% pred_dom={labels['dominio']} "
            f"(esperado {expected_domain})"
        )
        if not ok:
            failed += 1
            if not domain_ok:
                print("       Dominio predicho no coincide con el esperado.")
            if not conf_ok:
                print(f"       Confianza {conf:.3f} por debajo de {MIN_CONFIDENCE}.")
            if not head_ok:
                print(f"       Cabeza más débil {min_head:.3f} por debajo de {MIN_HEAD_CONFIDENCE}.")

    if failed:
        print(f"\n{failed} ejemplo(s) no cumplen el umbral.", file=sys.stderr)
        return 1

    print(f"\nTodos los ejemplos pasan validación ({len(prompts)}/{len(prompts)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
