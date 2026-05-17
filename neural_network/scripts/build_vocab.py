#!/usr/bin/env python3
"""
Construye vocabulario desde train.json y matriz de embeddings alineada con FastText .vec.

Salidas:
- Si existe `data/train.json` junto a `scripts/` (p. ej. Colab en `/content`): `artifacts/` en esa misma raíz.
- Si existe `notebook/data/train.json` (árbol `neural_network/` en el repo): `notebook/artifacts/`.
- Si no: `dataset/final/artifacts/` si existe dataset final; fallback `dataset/artifacts/`.

Ficheros: `vocab.json` (word2idx, idx2word, meta) y `embedding_init.pt` (`torch.Tensor` [vocab_size, embed_dim]).

El índice 0 es <pad> (embeddings a ceros), 1 es <unk>.

Lectura FastText en una sola pasada por el .vec: solo materializa vectores para tokens del
vocabulario (memoria O(|vocab|)), sin cargar el fichero completo en RAM.

Uso (desde la raíz del repositorio):
  python neural_network/scripts/build_vocab.py \\
    --train dataset/final/train.json \\
    --fasttext /path/to/cc.es.300.vec \\
    --min-freq 2 \\
    --max-vocab 40000

Descarga típica FastText español:
  https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.es.300.vec.gz
  (descomprimir antes)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import torch

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_ROOT = SCRIPTS_DIR.parent
NB_ROOT = RUN_ROOT / "notebook"


def _project_root() -> Path:
    """Raíz del repo Synapse si el script vive en `<repo>/neural_network/scripts/`; si no, RUN_ROOT."""
    cand = SCRIPTS_DIR.parent.parent
    if (cand / "dataset").is_dir():
        return cand.resolve()
    return RUN_ROOT.resolve()


PROJECT_ROOT = _project_root()


def _default_train_path() -> Path:
    if (RUN_ROOT / "data" / "train.json").is_file():
        return RUN_ROOT / "data" / "train.json"
    if (NB_ROOT / "data" / "train.json").is_file():
        return NB_ROOT / "data" / "train.json"
    final_train = PROJECT_ROOT / "dataset" / "final" / "train.json"
    if final_train.is_file():
        return final_train
    return PROJECT_ROOT / "dataset" / "final" / "train.json"


def _default_artifacts_dir() -> Path:
    if (RUN_ROOT / "data" / "train.json").is_file():
        data_artifacts = RUN_ROOT / "data" / "artifacts"
        return data_artifacts if data_artifacts.is_dir() else RUN_ROOT / "artifacts"
    if (NB_ROOT / "data" / "train.json").is_file():
        data_artifacts = NB_ROOT / "data" / "artifacts"
        return data_artifacts if data_artifacts.is_dir() else NB_ROOT / "artifacts"
    if (PROJECT_ROOT / "dataset" / "final" / "train.json").is_file():
        return PROJECT_ROOT / "dataset" / "final" / "artifacts"
    return PROJECT_ROOT / "dataset" / "artifacts"

_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text.lower()) if t.strip()]


def row_text_for_vocab(row: dict) -> str:
    """Misma prioridad que SynapseDataset en train_textcnn (texto vs title+body)."""
    text = row.get("texto") or row.get("text") or ""
    text = str(text).strip()
    if not text and (row.get("title") or row.get("body")):
        text = (
            str(row.get("title") or "").strip()
            + "\n"
            + str(row.get("body") or "").strip()
        ).strip()
    return text


def _infer_fasttext_dim(path: Path) -> int:
    """Lee solo el encabezado o la primera fila de vector para conocer la dimensión."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        first = f.readline().strip().split()
        if len(first) == 2 and first[0].isdigit() and first[1].isdigit():
            return int(first[1])
        f.seek(0)
        for line in f:
            parts = line.rstrip().split()
            if len(parts) >= 2:
                return len(parts) - 1
    return 300


def fill_embeddings_from_fasttext_stream(
    path: Path,
    word2idx: Dict[str, int],
    vocab_size: int,
    dim: int,
) -> Tuple[torch.Tensor, int, Set[int]]:
    """
    Una pasada por el .vec: copia vectores solo para palabras presentes en word2idx.
    Returns (matrix [vocab_size, dim], n_found_in_file, filled_row_indices).
    """
    needed_words: Set[str] = {
        w for w in word2idx if w not in ("<pad>", "<unk>")
    }
    matrix = torch.zeros(vocab_size, dim, dtype=torch.float32)
    filled_rows: Set[int] = set()
    found = 0

    with open(path, encoding="utf-8", errors="ignore") as f:
        first = f.readline().strip().split()
        if len(first) == 2 and first[0].isdigit() and first[1].isdigit():
            line_iter = f
        else:
            f.seek(0)
            line_iter = f

        for line in line_iter:
            if not needed_words:
                break
            parts = line.rstrip().split()
            if len(parts) < 2:
                continue
            if len(parts) - 1 != dim:
                continue
            word = parts[0]
            if word not in needed_words:
                continue
            nums = parts[1 : 1 + dim]
            try:
                vec = torch.tensor([float(x) for x in nums], dtype=torch.float32)
            except ValueError:
                continue
            idx = word2idx[word]
            matrix[idx] = vec
            filled_rows.add(idx)
            needed_words.discard(word)
            found += 1

    return matrix, found, filled_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=_default_train_path())
    ap.add_argument("--fasttext", type=Path, required=True, help="Ruta a fasttext .vec")
    ap.add_argument("--out-dir", type=Path, default=_default_artifacts_dir())
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("--max-vocab", type=int, default=40_000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not args.train.exists():
        print(f"Error: no existe {args.train}. Ejecuta split_dataset.py antes.", file=sys.stderr)
        return 1
    if not args.fasttext.exists():
        print(f"Error: no existe {args.fasttext}", file=sys.stderr)
        return 1

    with open(args.train, encoding="utf-8") as f:
        train_rows = json.load(f)

    freq: Dict[str, int] = {}
    for row in train_rows:
        for tok in tokenize(row_text_for_vocab(row)):
            freq[tok] = freq.get(tok, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    words = [
        w
        for w, c in sorted_words
        if c >= args.min_freq and w not in ("<pad>", "<unk>")
    ][: args.max_vocab]

    word2idx: Dict[str, int] = {"<pad>": 0, "<unk>": 1}
    idx2word = ["<pad>", "<unk>"]
    for w in words:
        word2idx[w] = len(idx2word)
        idx2word.append(w)

    print(f"Leyendo FastText (streaming) {args.fasttext} ...")
    vocab_size = len(idx2word)
    dim = _infer_fasttext_dim(args.fasttext)
    matrix, found, filled_rows = fill_embeddings_from_fasttext_stream(
        args.fasttext, word2idx, vocab_size, dim
    )

    torch.manual_seed(args.seed)
    for w, i in word2idx.items():
        if w in ("<pad>", "<unk>"):
            continue
        if i not in filled_rows:
            matrix[i].normal_(0, 0.1)

    print(
        f"Vocab tokens (sin pad/unk): {vocab_size - 2}, "
        f"con vector FastText en fichero: {found}, dim={dim}"
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "train_file": str(args.train),
        "fasttext": str(args.fasttext),
        "embed_dim": dim,
        "vocab_size": vocab_size,
        "min_freq": args.min_freq,
        "seed": args.seed,
        "fasttext_hits_in_vocab": found,
    }
    with open(args.out_dir / "vocab.json", "w", encoding="utf-8") as f:
        json.dump({"word2idx": word2idx, "idx2word": idx2word, "meta": meta}, f, ensure_ascii=False)

    torch.save(matrix, args.out_dir / "embedding_init.pt")
    print(f"Escrito {args.out_dir / 'vocab.json'} y embedding_init.pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
