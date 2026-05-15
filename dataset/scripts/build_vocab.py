#!/usr/bin/env python3
"""
Construye vocabulario desde train.json y matriz de embeddings alineada con FastText .vec.

Salidas en dataset/artifacts/ (o --out-dir):
  - vocab.json         word2idx, idx2word, meta
  - embedding_init.pt  torch.Tensor [vocab_size, embed_dim]

El índice 0 es <pad> (embeddings a ceros), 1 es <unk>.

Uso:
  python dataset/scripts/build_vocab.py \\
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
from typing import Dict, List, Tuple

import torch

PROJECT_ROOT = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "dataset" / "artifacts"

_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text.lower()) if t.strip()]


def load_fasttext_vec(path: Path) -> Tuple[Dict[str, List[float]], int]:
    """Lee .vec (primera línea opcional: n_tokens dim)."""
    vectors: Dict[str, List[float]] = {}
    dim: int | None = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        first = f.readline().strip().split()
        if len(first) == 2 and first[0].isdigit() and first[1].isdigit():
            dim = int(first[1])
        else:
            f.seek(0)
        for line in f:
            parts = line.rstrip().split()
            if len(parts) < 2:
                continue
            if dim is None:
                dim = len(parts) - 1
            word = parts[0]
            nums = parts[1 : 1 + dim]
            if len(nums) != dim:
                continue
            try:
                vectors[word] = [float(x) for x in nums]
            except ValueError:
                continue
    return vectors, dim or 300


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=PROJECT_ROOT / "dataset/final/train.json")
    ap.add_argument("--fasttext", type=Path, required=True, help="Ruta a fasttext .vec")
    ap.add_argument("--out-dir", type=Path, default=ARTIFACTS_DIR)
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
        text = row.get("texto") or row.get("text") or ""
        for tok in tokenize(str(text)):
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

    print(f"Cargando FastText {args.fasttext} ...")
    ft_vec, dim = load_fasttext_vec(args.fasttext)
    if not ft_vec:
        print("Error: no se leyeron vectores FastText", file=sys.stderr)
        return 1

    vocab_size = len(idx2word)
    matrix = torch.zeros(vocab_size, dim)
    found = 0
    for w, i in word2idx.items():
        if w in ("<pad>", "<unk>"):
            continue
        v = ft_vec.get(w)
        if v is not None:
            matrix[i] = torch.tensor(v, dtype=torch.float32)
            found += 1
        else:
            matrix[i].normal_(0, 0.1)
    print(f"Vocab tokens (sin pad/unk): {vocab_size - 2}, con vector FastText: {found}, dim={dim}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "train_file": str(args.train),
        "fasttext": str(args.fasttext),
        "embed_dim": dim,
        "vocab_size": vocab_size,
        "min_freq": args.min_freq,
        "seed": args.seed,
    }
    with open(args.out_dir / "vocab.json", "w", encoding="utf-8") as f:
        json.dump({"word2idx": word2idx, "idx2word": idx2word, "meta": meta}, f, ensure_ascii=False)

    torch.save(matrix, args.out_dir / "embedding_init.pt")
    print(f"Escrito {args.out_dir / 'vocab.json'} y embedding_init.pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
