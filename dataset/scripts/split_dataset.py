#!/usr/bin/env python3
"""
Divide dataset/final/dataset.json en train/val/test (70/15/15) con semilla fija.

Estratificación: clave compuesta nivel|urgencia|emocion|dominio (cabezas no supervisadas
aparecen como `_` en la clave). Si alguna combinación tiene <2 ejemplos, se hace split
solo estratificado por `emocion`.

Uso:
  python dataset/scripts/split_dataset.py --input dataset/final/dataset.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).parent.parent.parent
FINAL_DIR = PROJECT_ROOT / "dataset" / "final"

SYNTHETIC_PROGRAMMING_FUENTE = "synthetic_programming_es"
REAL_FUENTES = frozenset({"so_es", "so_es_aug", "goemotions_es"})


def _is_head_supervised(row: Dict[str, Any], head: str) -> bool:
    sup = row.get("supervision")
    if not isinstance(sup, dict):
        return True
    return bool(sup.get(head, True))


def _label_or_none(row: Dict[str, Any], key: str) -> Optional[str]:
    if key == "dominio":
        v = row.get("dominio")
        if v is None or not str(v).strip():
            v = row.get("domain_synapse")
    else:
        v = row.get(key)
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _composite_part(row: Dict[str, Any], head: str) -> str:
    if not _is_head_supervised(row, head):
        return "_"
    lab = _label_or_none(row, head)
    return lab if lab is not None else "_"


def _composite_key(row: Dict[str, Any]) -> str:
    return "|".join(
        [
            _composite_part(row, "nivel_tecnico"),
            _composite_part(row, "urgencia"),
            _composite_part(row, "emocion"),
            _composite_part(row, "dominio"),
        ]
    )


def _validate_row(row: Dict[str, Any], i: int) -> None:
    texto = str(row.get("texto", "")).strip()
    if not texto:
        raise ValueError(f"Fila {i}: falta o vacío 'texto'")
    sup = row.get("supervision")
    for head in ("nivel_tecnico", "urgencia", "emocion", "dominio"):
        active = True
        if isinstance(sup, dict):
            active = bool(sup.get(head, True))
        if not active:
            continue
        if _label_or_none(row, head) is None:
            raise ValueError(
                f"Fila {i}: falta etiqueta '{head}' pero supervision la marca como activa"
            )


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


def move_synthetic_rows_to_train(
    train: List[Dict[str, Any]],
    val: List[Dict[str, Any]],
    test: List[Dict[str, Any]],
    *,
    synthetic_fuente: str,
    rng,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Mueve filas sintéticas de val/test a train y rellena val/test con filas reales desde train."""
    tgt_v = len(val)
    tgt_t = len(test)

    def _is_synth(row: Dict[str, Any]) -> bool:
        return str(row.get("fuente", "")) == synthetic_fuente

    synth_moved = [r for r in val if _is_synth(r)] + [r for r in test if _is_synth(r)]
    val_c = [r for r in val if not _is_synth(r)]
    test_c = [r for r in test if not _is_synth(r)]
    train_w = list(train) + synth_moved

    def _pull_reals_from_train(deficit: int, dest: List[Dict[str, Any]]) -> None:
        if deficit <= 0:
            return
        cand_idx = [i for i, r in enumerate(train_w) if str(r.get("fuente", "")) in REAL_FUENTES]
        if len(cand_idx) < deficit:
            raise ValueError(
                f"No hay suficientes filas reales en train para rellenar val/test "
                f"(necesitas {deficit}, disponibles {len(cand_idx)})."
            )
        rng.shuffle(cand_idx)
        picked = sorted(cand_idx[:deficit], reverse=True)
        for i in picked:
            dest.append(train_w.pop(i))

    _pull_reals_from_train(tgt_v - len(val_c), val_c)
    _pull_reals_from_train(tgt_t - len(test_c), test_c)

    if len(val_c) != tgt_v or len(test_c) != tgt_t:
        raise ValueError(
            f"Tamaños val/test tras mover sintéticos: val {len(val_c)}/{tgt_v}, test {len(test_c)}/{tgt_t}"
        )
    return train_w, val_c, test_c


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
        "stratify_note": "composite nivel|urgencia|emocion|dominio (unsupervised dims as _); fallback emocion",
    }
    with open(args.out_dir / "split_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
