#!/usr/bin/env python3
"""
Divide dataset/final/dataset.json en train/val/test (70/15/15) con semilla fija.

Estratificación: clave compuesta nivel|urgencia|emocion|dominio.
Si alguna combinación tiene <2 ejemplos, se hace split solo estratificado por `emocion`.

Uso:
  python dataset/scripts/split_dataset.py --input dataset/final/dataset.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).parent.parent.parent
FINAL_DIR = PROJECT_ROOT / "dataset" / "final"


def _composite_key(row: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("nivel_tecnico", "")),
            str(row.get("urgencia", "")),
            str(row.get("emocion", "")),
            str(row.get("dominio", "")),
        ]
    )


def _validate_row(row: Dict[str, Any], i: int) -> None:
    required = ("texto", "nivel_tecnico", "urgencia", "emocion", "dominio")
    for k in required:
        if k not in row or row[k] in (None, ""):
            raise ValueError(f"Fila {i}: falta o vacío '{k}'")


def split_data(
    rows: List[Dict[str, Any]],
    seed: int,
    train_ratio: float,
    val_ratio: float,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    test_ratio = 1.0 - train_ratio - val_ratio
    if test_ratio <= 0:
        raise ValueError("train_ratio + val_ratio debe ser < 1")

    strat = [_composite_key(r) for r in rows]
    counts = {}
    for s in strat:
        counts[s] = counts.get(s, 0) + 1
    use_combo = all(c >= 2 for c in counts.values()) and len(rows) >= 10
    stratify = strat if use_combo else [str(r.get("emocion", "unknown")) for r in rows]
    try:
        train_idx, temp_idx = train_test_split(
            range(len(rows)),
            test_size=(val_ratio + test_ratio),
            random_state=seed,
            stratify=stratify,
        )
        rel_test = test_ratio / (val_ratio + test_ratio)
        strat_temp = [stratify[i] for i in temp_idx]
        val_idx, test_idx = train_test_split(
            temp_idx,
            test_size=rel_test,
            random_state=seed,
            stratify=strat_temp,
        )
    except ValueError:
        train_idx, temp_idx = train_test_split(
            range(len(rows)),
            test_size=(val_ratio + test_ratio),
            random_state=seed,
        )
        rel_test = test_ratio / (val_ratio + test_ratio)
        val_idx, test_idx = train_test_split(
            temp_idx,
            test_size=rel_test,
            random_state=seed,
        )

    train_ = [rows[i] for i in sorted(train_idx)]
    val_ = [rows[i] for i in sorted(val_idx)]
    test_ = [rows[i] for i in sorted(test_idx)]
    return train_, val_, test_


def main() -> int:
    ap = argparse.ArgumentParser(description="Split Synapse dataset (train/val/test).")
    ap.add_argument(
        "--input",
        type=Path,
        default=FINAL_DIR / "dataset.json",
        help="JSON array de ejemplos Synapse",
    )
    ap.add_argument("--out-dir", type=Path, default=FINAL_DIR)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--train", type=float, default=0.70)
    ap.add_argument("--val", type=float, default=0.15)
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"Error: no existe {path}", file=sys.stderr)
        return 1

    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        print("Error: el JSON debe ser un array", file=sys.stderr)
        return 1

    for i, row in enumerate(rows):
        _validate_row(row, i)

    train_r, val_r, test_r = split_data(rows, args.seed, args.train, args.val)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for name, subset in (
        ("train.json", train_r),
        ("val.json", val_r),
        ("test.json", test_r),
    ):
        out = args.out_dir / name
        with open(out, "w", encoding="utf-8") as f:
            json.dump(subset, f, ensure_ascii=False, indent=2)
        print(f"Escrito {out} ({len(subset)} ejemplos)")

    meta = {
        "source": str(path),
        "seed": args.seed,
        "train": len(train_r),
        "val": len(val_r),
        "test": len(test_r),
        "stratify_note": "composite nivel|urgencia|emocion|dominio si todas las clases tienen >=2; si no, por emocion",
    }
    with open(args.out_dir / "split_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
