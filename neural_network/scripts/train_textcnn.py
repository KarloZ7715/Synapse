#!/usr/bin/env python3
"""
Entrena SynapseTextCNN (PyTorch) en Colab o local.

Pérdida: suma de CrossEntropyLoss sobre 4 cabezas con `ignore_index` para filas sin
supervisión en una cabeza (véase `supervision` en el JSON y `docs/03-data-and-state/dataset-plan.md` §1bis).

Rutas por defecto: (1) si existe `data/train.json` junto a la carpeta `scripts/` (típico en Colab: `/content/data` + `/content/scripts`);
(2) si no, `notebook/data/train.json` bajo el mismo padre que `scripts/` (árbol `neural_network/` en el repo);
(3) si no, `dataset/final/` y `dataset/final/artifacts/` cuando existe final; fallback `dataset/final/`.

Uso (después de split_dataset + build_vocab):
  pip install torch scikit-learn numpy
  python neural_network/scripts/train_textcnn.py \\
    --train dataset/final/train.json \\
    --val dataset/final/val.json \\
    --test dataset/final/test.json \\
    --vocab dataset/final/artifacts/vocab.json \\
    --embedding dataset/final/artifacts/embedding_init.pt \\
    --out-dir dataset/final/checkpoints/textcnn_run1 \\
    --epochs 80 --batch-size 32 --lr 1e-3 --max-len 160 --dropout 0.55 --weight-decay 0.03 --freeze-epochs 3 --patience 8 --early-stop-metric mixed_f1_macro_mean
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, Dataset

SCRIPTS_DIR = Path(__file__).resolve().parent
RUN_ROOT = SCRIPTS_DIR.parent
NB_ROOT = RUN_ROOT / "notebook"


def _project_root() -> Path:
    cand = SCRIPTS_DIR.parent.parent
    if (cand / "dataset").is_dir():
        return cand.resolve()
    return RUN_ROOT.resolve()


PROJECT_ROOT = _project_root()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from textcnn_model import SynapseTextCNN, count_parameters
from training_labels import HEAD_KEYS, IGNORE_LABEL_INDEX, LABEL_SPECS, label_to_idx_maps


def _use_flat_data_runtime() -> bool:
    return (RUN_ROOT / "data" / "train.json").is_file()


def _use_package_notebook_runtime() -> bool:
    return (NB_ROOT / "data" / "train.json").is_file()


def _default_train_path() -> Path:
    if _use_flat_data_runtime():
        return RUN_ROOT / "data" / "train.json"
    if _use_package_notebook_runtime():
        return NB_ROOT / "data" / "train.json"
    final = PROJECT_ROOT / "dataset/final/train.json"
    if final.is_file():
        return final
    return PROJECT_ROOT / "dataset/final/train.json"


def _default_val_path() -> Path:
    if _use_flat_data_runtime():
        return RUN_ROOT / "data" / "val.json"
    if _use_package_notebook_runtime():
        return NB_ROOT / "data" / "val.json"
    final = PROJECT_ROOT / "dataset/final/val.json"
    if final.is_file():
        return final
    return PROJECT_ROOT / "dataset/final/val.json"


def _default_test_path() -> Path:
    if _use_flat_data_runtime():
        return RUN_ROOT / "data" / "test.json"
    if _use_package_notebook_runtime():
        return NB_ROOT / "data" / "test.json"
    final = PROJECT_ROOT / "dataset/final/test.json"
    if final.is_file():
        return final
    return PROJECT_ROOT / "dataset/final/test.json"


def _default_vocab_path() -> Path:
    if _use_flat_data_runtime():
        data_vocab = RUN_ROOT / "data" / "artifacts" / "vocab.json"
        return data_vocab if data_vocab.is_file() else RUN_ROOT / "artifacts" / "vocab.json"
    if _use_package_notebook_runtime():
        data_vocab = NB_ROOT / "data" / "artifacts" / "vocab.json"
        return data_vocab if data_vocab.is_file() else NB_ROOT / "artifacts" / "vocab.json"
    final = PROJECT_ROOT / "dataset/final/artifacts/vocab.json"
    if (PROJECT_ROOT / "dataset/final/train.json").is_file():
        return final
    return PROJECT_ROOT / "dataset/artifacts/vocab.json"


def _default_embedding_path() -> Path:
    if _use_flat_data_runtime():
        data_embedding = RUN_ROOT / "data" / "artifacts" / "embedding_init.pt"
        return data_embedding if data_embedding.is_file() else RUN_ROOT / "artifacts" / "embedding_init.pt"
    if _use_package_notebook_runtime():
        data_embedding = NB_ROOT / "data" / "artifacts" / "embedding_init.pt"
        return data_embedding if data_embedding.is_file() else NB_ROOT / "artifacts" / "embedding_init.pt"
    final = PROJECT_ROOT / "dataset/final/artifacts/embedding_init.pt"
    if (PROJECT_ROOT / "dataset/final/train.json").is_file():
        return final
    return PROJECT_ROOT / "dataset/artifacts/embedding_init.pt"


def _default_out_dir() -> Path:
    if _use_flat_data_runtime():
        data_checkpoints = RUN_ROOT / "data" / "checkpoints"
        return data_checkpoints / "textcnn_default" if data_checkpoints.is_dir() else RUN_ROOT / "checkpoints" / "textcnn_default"
    if _use_package_notebook_runtime():
        data_checkpoints = NB_ROOT / "data" / "checkpoints"
        return data_checkpoints / "textcnn_default" if data_checkpoints.is_dir() else NB_ROOT / "checkpoints" / "textcnn_default"
    if (PROJECT_ROOT / "dataset/final/train.json").is_file():
        return PROJECT_ROOT / "dataset/final/checkpoints/textcnn_default"
    return PROJECT_ROOT / "dataset/checkpoints/textcnn_default"


_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)

KEYS: Tuple[str, ...] = HEAD_KEYS

# DoD gates (validation macro-F1); ver docs/03-data-and-state/runbook.md
DOD_THRESHOLDS = {
    "f1_macro_mean": 0.38,
    "nivel_tecnico": 0.42,
    "urgencia": 0.55,
    "emocion": 0.26,
    "dominio": 0.18,
}

OVERFIT_F1_GAP_WARN = 0.15


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text.lower()) if t.strip()]


def encode_text(text: str, word2idx: Dict[str, int], max_len: int) -> List[int]:
    unk = word2idx.get("<unk>", 1)
    toks = tokenize(text)[:max_len]
    return [word2idx.get(t, unk) for t in toks]


def row_labels_from_row(row: Dict[str, Any], maps: Dict[str, Dict[str, int]], keys: Tuple[str, ...]) -> Dict[str, int]:
    defaults = {
        "nivel_tecnico": "principiante",
        "urgencia": "media",
        "emocion": "neutral",
        "dominio": "general",
    }
    field_aliases = {
        "dominio": ("dominio", "domain_synapse"),
    }
    y: Dict[str, int] = {}
    sup = row.get("supervision")
    for k in keys:
        if isinstance(sup, dict) and sup.get(k) is False:
            y[k] = IGNORE_LABEL_INDEX
            continue
        if k in field_aliases:
            alts = field_aliases[k]
            raw = str(row.get(alts[0]) or row.get(alts[1]) or "").strip()
        else:
            raw = str(row.get(k, "")).strip()
        lab_map = maps[k]
        if raw not in lab_map:
            raw = defaults[k]
        y[k] = lab_map[raw]
    return y


def aggregate_metrics(
    y_true: Dict[str, np.ndarray], y_pred: Dict[str, np.ndarray], keys: Tuple[str, ...]
) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k in keys:
        yt, yp = y_true[k], y_pred[k]
        m = yt != IGNORE_LABEL_INDEX
        yt_m, yp_m = yt[m], yp[m]
        if len(yt_m) == 0:
            out[f"f1_macro_{k}"] = 0.0
            out[f"f1_micro_{k}"] = 0.0
            out[f"acc_{k}"] = 0.0
            continue
        out[f"f1_macro_{k}"] = float(f1_score(yt_m, yp_m, average="macro", zero_division=0))
        out[f"f1_micro_{k}"] = float(f1_score(yt_m, yp_m, average="micro", zero_division=0))
        out[f"acc_{k}"] = float((yt_m == yp_m).mean())
    macro_mean = float(np.mean([out[f"f1_macro_{k}"] for k in keys]))
    out["f1_macro_mean"] = macro_mean
    return out


class SynapseDataset(Dataset):
    def __init__(
        self,
        rows: List[Dict[str, Any]],
        word2idx: Dict[str, int],
        maps: Dict[str, Dict[str, int]],
        keys: Tuple[str, ...],
        max_len: int,
    ) -> None:
        self.rows = rows
        self.word2idx = word2idx
        self.maps = maps
        self.keys = keys
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> Tuple[torch.Tensor, Dict[str, int]]:
        row = self.rows[i]
        text = row.get("texto") or row.get("text") or ""
        text = str(text).strip()
        if not text and (row.get("title") or row.get("body")):
            text = (
                str(row.get("title") or "").strip()
                + "\n"
                + str(row.get("body") or "").strip()
            ).strip()
        ids = encode_text(text, self.word2idx, self.max_len)
        if len(ids) < self.max_len:
            ids = ids + [self.word2idx["<pad>"]] * (self.max_len - len(ids))
        else:
            ids = ids[: self.max_len]
        x = torch.tensor(ids, dtype=torch.long)
        y = row_labels_from_row(row, self.maps, self.keys)
        return x, y


def collate_fn(
    batch: List[Tuple[torch.Tensor, Dict[str, int]]], key_order: Tuple[str, ...]
) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
    xs = [b[0] for b in batch]
    x = torch.stack(xs, dim=0)
    ys: Dict[str, torch.Tensor] = {
        k: torch.tensor([b[1][k] for b in batch], dtype=torch.long) for k in key_order
    }
    return x, ys


def mean_head_accuracy(metrics: Dict[str, float], keys: Tuple[str, ...]) -> float:
    """Media de accuracy por cabeza (comparable a un único `acc` en multitarea)."""
    accs = [metrics[f"acc_{k}"] for k in keys]
    return float(np.mean(accs)) if accs else 0.0


def head_detail_json(
    y_true: np.ndarray, y_pred: np.ndarray, label_names: Tuple[str, ...]
) -> Dict[str, Any]:
    if len(y_true) == 0:
        return {
            "labels_order": list(label_names),
            "f1_per_class": {},
            "confusion_matrix": [],
            "note": "no_supervised_rows_for_head",
        }
    n = len(label_names)
    labels_idx = np.arange(n)
    f1_each = f1_score(y_true, y_pred, average=None, labels=labels_idx, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels_idx)
    return {
        "labels_order": list(label_names),
        "f1_per_class": {label_names[i]: float(f1_each[i]) for i in range(n)},
        "confusion_matrix": cm.tolist(),
    }




def head_details_from_predictions(
    y_true: Dict[str, np.ndarray],
    y_pred: Dict[str, np.ndarray],
    keys: Tuple[str, ...] = KEYS,
) -> Dict[str, Any]:
    return {
        k: head_detail_json(y_true[k], y_pred[k], LABEL_SPECS[k])
        for k in keys
    }


@torch.no_grad()
def collect_head_details(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    keys: Tuple[str, ...],
) -> Dict[str, Any]:
    model.eval()
    y_true: Dict[str, List[int]] = {k: [] for k in keys}
    y_pred: Dict[str, List[int]] = {k: [] for k in keys}
    for xb, yb in loader:
        xb = xb.to(device)
        logits = model(xb)
        for k in keys:
            pred = logits[k].argmax(dim=-1).cpu().numpy()
            truth = yb[k].numpy()
            mask = truth != IGNORE_LABEL_INDEX
            if mask.any():
                y_true[k].extend(truth[mask].astype(int).tolist())
                y_pred[k].extend(pred[mask].astype(int).tolist())
    return head_details_from_predictions(
        {k: np.array(y_true[k], dtype=np.int64) for k in keys},
        {k: np.array(y_pred[k], dtype=np.int64) for k in keys},
        keys,
    )


def is_synthetic_source(source: str) -> bool:
    return source == "synthetic_programming_final" or source == "synthetic_programming_es" or source.startswith("synthetic_")


def source_metrics_summary(per_source: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    real_direct = per_source.get("__real__", {}).get("metrics")
    synth_direct = per_source.get("__synthetic__", {}).get("metrics")
    if isinstance(real_direct, dict) and "f1_macro_mean" in real_direct:
        out["real_f1_macro_mean"] = float(real_direct["f1_macro_mean"])
    if isinstance(synth_direct, dict) and "f1_macro_mean" in synth_direct:
        out["synthetic_f1_macro_mean"] = float(synth_direct["f1_macro_mean"])
    if "real_f1_macro_mean" in out and "synthetic_f1_macro_mean" in out:
        return out

    real_weighted = 0.0
    real_n = 0
    synthetic_weighted = 0.0
    synthetic_n = 0
    for source, payload in per_source.items():
        if str(source).startswith("__"):
            continue
        metrics = payload.get("metrics") if isinstance(payload, dict) else None
        if not isinstance(metrics, dict) or "f1_macro_mean" not in metrics:
            continue
        n = int(payload.get("n", 0))
        if is_synthetic_source(str(source)):
            synthetic_weighted += float(metrics["f1_macro_mean"]) * n
            synthetic_n += n
        else:
            real_weighted += float(metrics["f1_macro_mean"]) * n
            real_n += n
    if real_n and "real_f1_macro_mean" not in out:
        out["real_f1_macro_mean"] = real_weighted / real_n
    if synthetic_n and "synthetic_f1_macro_mean" not in out:
        out["synthetic_f1_macro_mean"] = synthetic_weighted / synthetic_n
    return out


def metric_for_checkpoint(
    metric_name: str,
    mixed_metrics: Dict[str, float],
    real_metrics: Dict[str, float] | None,
) -> float:
    mixed = float(mixed_metrics["f1_macro_mean"])
    if metric_name == "mixed_f1_macro_mean":
        return mixed
    if real_metrics and "f1_macro_mean" in real_metrics:
        real = float(real_metrics["f1_macro_mean"])
        if metric_name == "real_f1_macro_mean":
            return real
        if metric_name == "composite_f1_macro_mean":
            return 0.70 * real + 0.30 * mixed
    return mixed


def rows_by_source(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(str(row.get("fuente") or "unknown"), []).append(row)
    return out


def majority_baseline_macro_f1(y: np.ndarray) -> float:
    if len(y) == 0:
        return 0.0
    values, counts = np.unique(y, return_counts=True)
    maj = int(values[int(np.argmax(counts))])
    pred = np.full_like(y, maj)
    return float(f1_score(y, pred, average="macro", zero_division=0))


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterions: Dict[str, nn.Module],
    device: torch.device,
    keys: Tuple[str, ...],
) -> Tuple[float, Dict[str, float]]:
    model.eval()
    total_loss = 0.0
    n_batches = 0
    all_true: Dict[str, List[int]] = {k: [] for k in keys}
    all_pred: Dict[str, List[int]] = {k: [] for k in keys}

    for xb, yb in loader:
        xb = xb.to(device)
        logits = model(xb)
        batch_loss = 0.0
        for k in keys:
            yk = yb[k].to(device)
            if (yk == IGNORE_LABEL_INDEX).all():
                continue
            batch_loss += criterions[k](logits[k], yk).item()
        total_loss += batch_loss
        n_batches += 1
        for k in keys:
            pred = logits[k].argmax(dim=-1).cpu().numpy()
            y_cpu = yb[k].numpy()
            m = y_cpu != IGNORE_LABEL_INDEX
            if m.any():
                all_pred[k].extend(pred[m].tolist())
                all_true[k].extend(y_cpu[m].tolist())

    metrics = aggregate_metrics(
        {k: np.array(all_true[k]) for k in keys},
        {k: np.array(all_pred[k]) for k in keys},
        keys,
    )
    return total_loss / max(n_batches, 1), metrics



def make_loader_for_rows(
    rows: List[Dict[str, Any]],
    word2idx: Dict[str, int],
    maps: Dict[str, Dict[str, int]],
    keys: Tuple[str, ...],
    max_len: int,
    batch_size: int,
) -> DataLoader:
    ds = SynapseDataset(rows, word2idx, maps, keys, max_len)

    def _collate(batch: List[Tuple[torch.Tensor, Dict[str, int]]]) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        return collate_fn(batch, keys)

    return DataLoader(ds, batch_size=batch_size, shuffle=False, collate_fn=_collate)


@torch.no_grad()
def evaluate_rows(
    model: nn.Module,
    rows: List[Dict[str, Any]],
    word2idx: Dict[str, int],
    maps: Dict[str, Dict[str, int]],
    criterions: Dict[str, nn.Module],
    device: torch.device,
    keys: Tuple[str, ...],
    max_len: int,
    batch_size: int,
) -> Tuple[float, Dict[str, float]]:
    if not rows:
        return 0.0, {}
    loader = make_loader_for_rows(rows, word2idx, maps, keys, max_len, batch_size)
    return evaluate(model, loader, criterions, device, keys)


def evaluate_per_source(
    model: nn.Module,
    rows: List[Dict[str, Any]],
    word2idx: Dict[str, int],
    maps: Dict[str, Dict[str, int]],
    criterions: Dict[str, nn.Module],
    device: torch.device,
    keys: Tuple[str, ...],
    max_len: int,
    batch_size: int,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for source, subset in rows_by_source(rows).items():
        _, metrics = evaluate_rows(model, subset, word2idx, maps, criterions, device, keys, max_len, batch_size)
        out[source] = {"n": len(subset), "metrics": metrics}
    real_subset = [r for r in rows if not is_synthetic_source(str(r.get("fuente") or ""))]
    if real_subset:
        _, metrics = evaluate_rows(model, real_subset, word2idx, maps, criterions, device, keys, max_len, batch_size)
        out["__real__"] = {"n": len(real_subset), "metrics": metrics}
    synth_subset = [r for r in rows if is_synthetic_source(str(r.get("fuente") or ""))]
    if synth_subset:
        _, metrics = evaluate_rows(model, synth_subset, word2idx, maps, criterions, device, keys, max_len, batch_size)
        out["__synthetic__"] = {"n": len(synth_subset), "metrics": metrics}
    return out


def build_class_weights(
    train_rows: List[Dict[str, Any]],
    maps: Dict[str, Dict[str, int]],
    keys: Tuple[str, ...],
    num_labels: Dict[str, int],
    device: torch.device,
) -> Dict[str, torch.Tensor]:
    out: Dict[str, torch.Tensor] = {}
    for k in keys:
        ys_list = [row_labels_from_row(r, maps, keys)[k] for r in train_rows]
        ys_list = [yi for yi in ys_list if yi != IGNORE_LABEL_INDEX]
        ys = np.array(ys_list, dtype=np.int64)
        n_cls = num_labels[k]
        if len(ys) == 0:
            out[k] = torch.ones(n_cls, dtype=torch.float32, device=device)
            continue
        present = np.unique(ys)
        cw = compute_class_weight(class_weight="balanced", classes=present, y=ys)
        full = np.ones(n_cls, dtype=np.float64)
        for cls, w in zip(present, cw):
            full[int(cls)] = float(w)
        out[k] = torch.tensor(full, dtype=torch.float32, device=device)
    return out


def make_criterions(
    keys: Tuple[str, ...],
    device: torch.device,
    class_weights: Dict[str, torch.Tensor] | None,
) -> Dict[str, nn.Module]:
    criterions: Dict[str, nn.Module] = {}
    for k in keys:
        w = class_weights[k] if class_weights is not None else None
        criterions[k] = nn.CrossEntropyLoss(weight=w, ignore_index=IGNORE_LABEL_INDEX)
    return criterions


def evaluate_dod(metrics: Dict[str, float], keys: Tuple[str, ...]) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    mean_ok = metrics["f1_macro_mean"] >= DOD_THRESHOLDS["f1_macro_mean"]
    checks["f1_macro_mean"] = {
        "pass": mean_ok,
        "value": metrics["f1_macro_mean"],
        "min": DOD_THRESHOLDS["f1_macro_mean"],
    }
    all_pass = mean_ok
    for k in keys:
        key = f"f1_macro_{k}"
        val = metrics[key]
        thr = DOD_THRESHOLDS[k]
        ok = val >= thr
        checks[k] = {"pass": ok, "value": val, "min": thr}
        all_pass = all_pass and ok
    return {"all_pass": all_pass, "checks": checks}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_history(out_dir: Path, row: Dict[str, Any], history: List[Dict[str, Any]]) -> None:
    history.append(row)
    save_json(out_dir / "history.json", history)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=_default_train_path())
    ap.add_argument("--val", type=Path, default=_default_val_path())
    ap.add_argument("--test", type=Path, default=_default_test_path())
    ap.add_argument("--vocab", type=Path, default=_default_vocab_path())
    ap.add_argument("--embedding", type=Path, default=_default_embedding_path())
    ap.add_argument("--out-dir", type=Path, default=_default_out_dir())
    ap.add_argument("--max-len", type=int, default=160)
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=0.03)
    ap.add_argument("--dropout", type=float, default=0.55)
    ap.add_argument("--freeze-epochs", type=int, default=3, help="Congelar embeddings las primeras N epochs")
    ap.add_argument("--patience", type=int, default=8, help="Early stopping según la métrica seleccionada")
    ap.add_argument(
        "--early-stop-metric",
        choices=("mixed_f1_macro_mean", "real_f1_macro_mean", "composite_f1_macro_mean"),
        default="mixed_f1_macro_mean",
        help="Métrica para guardar best.pt; composite = 0.70*real + 0.30*mixed cuando hay filas reales.",
    )
    ap.add_argument("--seed", type=int, default=42)
    cw = ap.add_mutually_exclusive_group()
    cw.add_argument(
        "--class-weights",
        dest="class_weights",
        action="store_true",
        help="Activa CrossEntropyLoss con pesos balanceados por cabeza (es el comportamiento por defecto).",
    )
    cw.add_argument(
        "--no-class-weights",
        dest="class_weights",
        action="store_false",
        help="Desactiva pesos por cabeza (pérdida uniforme; útil solo para A/B vs pesos balanceados).",
    )
    ap.set_defaults(class_weights=True)
    args = ap.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    keys = KEYS
    num_labels = {k: len(LABEL_SPECS[k]) for k in keys}
    maps = label_to_idx_maps()

    if not args.vocab.exists() or not args.embedding.exists():
        print("Faltan vocab.json o embedding_init.pt. Ejecuta build_vocab.py.", file=sys.stderr)
        return 1
    with open(args.vocab, encoding="utf-8") as f:
        vocab_data = json.load(f)
    word2idx: Dict[str, int] = vocab_data["word2idx"]

    with open(args.train, encoding="utf-8") as f:
        train_rows = json.load(f)
    with open(args.val, encoding="utf-8") as f:
        val_rows = json.load(f)

    train_ds = SynapseDataset(train_rows, word2idx, maps, keys, args.max_len)
    val_ds = SynapseDataset(val_rows, word2idx, maps, keys, args.max_len)

    def _collate(batch: List[Tuple[torch.Tensor, Dict[str, int]]]) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        return collate_fn(batch, keys)

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=_collate
    )
    train_eval_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=False, collate_fn=_collate
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=_collate
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    emb_kw: Dict[str, Any] = {"map_location": "cpu"}
    try:
        emb_cpu = torch.load(args.embedding, **emb_kw, weights_only=True)
    except TypeError:
        emb_cpu = torch.load(args.embedding, map_location="cpu")

    if not isinstance(emb_cpu, torch.Tensor):
        print("Error: embedding_init.pt debe ser un torch.Tensor [vocab, dim]", file=sys.stderr)
        return 1
    embed_dim = emb_cpu.shape[1]

    model = SynapseTextCNN(
        vocab_size=len(word2idx),
        num_labels=num_labels,
        embed_dim=embed_dim,
        dropout=args.dropout,
        padding_idx=word2idx.get("<pad>", 0),
    ).to(device)

    model.init_embedding_from_matrix(emb_cpu.to(device), freeze=True)
    print(f"Parámetros entrenables (inicial): {count_parameters(model)}", flush=True)

    class_weights_cpu: Dict[str, torch.Tensor] | None = None
    if args.class_weights:
        class_weights_cpu = build_class_weights(train_rows, maps, keys, num_labels, torch.device("cpu"))

    cw_dev_init = (
        {k: class_weights_cpu[k].to(device) for k in keys} if class_weights_cpu is not None else None
    )
    criterions = make_criterions(keys, device, cw_dev_init)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    run_config: Dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "device": str(device),
        "seed": args.seed,
        "paths": {
            "train": str(args.train.resolve()),
            "val": str(args.val.resolve()),
            "test": str(args.test.resolve()),
            "vocab": str(args.vocab.resolve()),
            "embedding": str(args.embedding.resolve()),
            "out_dir": str(args.out_dir.resolve()),
        },
        "hyperparameters": {
            "max_len": args.max_len,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "weight_decay": args.weight_decay,
            "dropout": args.dropout,
            "freeze_epochs": args.freeze_epochs,
            "patience": args.patience,
            "class_weights": args.class_weights,
            "early_stop_metric": args.early_stop_metric,
        },
        "num_labels": num_labels,
    }
    save_json(args.out_dir / "run_config.json", run_config)

    baselines: Dict[str, float] = {}
    for k in keys:
        ys_list = [row_labels_from_row(r, maps, keys)[k] for r in train_rows]
        ys_list = [y for y in ys_list if y != IGNORE_LABEL_INDEX]
        ys = np.array(ys_list, dtype=np.int64)
        baselines[k] = majority_baseline_macro_f1(ys)
    save_json(args.out_dir / "majority_baselines.json", baselines)

    history: List[Dict[str, Any]] = []

    best_score = -1.0
    stale = 0
    best_epoch = 0
    best_train_metrics: Dict[str, float] = {}

    for epoch in range(1, args.epochs + 1):
        if epoch == args.freeze_epochs + 1:
            model.embedding.weight.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr * 0.5, weight_decay=args.weight_decay)
            print(
                f"Epoch {epoch}: embeddings descongelados, lr -> {args.lr * 0.5}",
                flush=True,
            )

        model.train()
        train_loss_sum = 0.0
        train_batches = 0
        for xb, yb in train_loader:
            xb = xb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            head_losses: List[torch.Tensor] = []
            for k in keys:
                yk = yb[k].to(device)
                if (yk == IGNORE_LABEL_INDEX).all():
                    continue
                head_losses.append(criterions[k](logits[k], yk))
            if not head_losses:
                loss = logits[keys[0]].sum() * 0.0
            else:
                loss = sum(head_losses)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss_sum += float(loss.item())
            train_batches += 1

        train_loss = train_loss_sum / max(train_batches, 1)
        tr_loss_eval, train_metrics = evaluate(model, train_eval_loader, criterions, device, keys)
        val_loss, val_metrics = evaluate(model, val_loader, criterions, device, keys)

        val_per_source = evaluate_per_source(
            model, val_rows, word2idx, maps, criterions, device, keys, args.max_len, args.batch_size
        )
        real_metrics = val_per_source.get("__real__", {}).get("metrics")
        score_for_best = metric_for_checkpoint(args.early_stop_metric, val_metrics, real_metrics)
        f1m = val_metrics["f1_macro_mean"]
        train_acc = mean_head_accuracy(train_metrics, keys)
        val_acc = mean_head_accuracy(val_metrics, keys)
        real_f1_txt = ""
        if isinstance(real_metrics, dict) and "f1_macro_mean" in real_metrics:
            real_f1_txt = f" val_real_f1={real_metrics['f1_macro_mean']:.4f}"
        print(
            f"Epoch {epoch}: train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} "
            f"f1_macro_mean(val)={f1m:.4f}{real_f1_txt} best_metric={score_for_best:.4f} "
            + " ".join(f"val:{k}={val_metrics[f'f1_macro_{k}']:.3f}" for k in keys),
            flush=True,
        )

        append_history(
            args.out_dir,
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_loss_eval": tr_loss_eval,
                "val_loss": val_loss,
                "metrics_train": train_metrics,
                "metrics_val": val_metrics,
                "metrics_val_by_source": val_per_source,
                "checkpoint_metric": {"name": args.early_stop_metric, "value": score_for_best},
            },
            history,
        )

        if score_for_best > best_score:
            best_score = score_for_best
            stale = 0
            best_epoch = epoch
            best_train_metrics = dict(train_metrics)
            ckpt = {
                "model_state": model.state_dict(),
                "num_labels": num_labels,
                "max_len": args.max_len,
                "word2idx": word2idx,
                "keys": list(keys),
                "epoch": epoch,
                "metrics_val": val_metrics,
                "metrics_val_by_source": val_per_source,
                "checkpoint_metric": {"name": args.early_stop_metric, "value": score_for_best},
                "metrics_train": train_metrics,
            }
            torch.save(ckpt, args.out_dir / "best.pt")
            save_json(args.out_dir / "best_metrics.json", {
                "mixed": val_metrics,
                "by_source": val_per_source,
                "checkpoint_metric": {"name": args.early_stop_metric, "value": score_for_best},
            })

            val_tmp = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=_collate)
            save_json(args.out_dir / "val_head_detail.json", collect_head_details(model, val_tmp, device, keys))
        else:
            stale += 1
            if stale >= args.patience:
                print(
                    f"Early stopping en epoch {epoch} (mejor {args.early_stop_metric}={best_score:.4f})",
                    flush=True,
                )
                break

    print(f"Mejor checkpoint: {args.out_dir / 'best.pt'} (epoch {best_epoch}, {args.early_stop_metric}={best_score:.4f})", flush=True)

    ckpt_path = args.out_dir / "best.pt"
    if not ckpt_path.exists():
        print("Error: no se generó best.pt", file=sys.stderr)
        return 1

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    cw_dev = {k: class_weights_cpu[k].to(device) for k in keys} if class_weights_cpu is not None else None
    criterions = make_criterions(keys, device, cw_dev)

    val_loss_final, val_metrics_final = evaluate(model, val_loader, criterions, device, keys)
    val_per_source_final = evaluate_per_source(
        model, val_rows, word2idx, maps, criterions, device, keys, args.max_len, args.batch_size
    )
    save_json(args.out_dir / "val_source_metrics.json", {
        "mixed": val_metrics_final,
        "by_source": val_per_source_final,
        "source_summary": source_metrics_summary(val_per_source_final),
    })

    test_metrics: Dict[str, Any] = {"skipped": True}
    if args.test.exists():
        with open(args.test, encoding="utf-8") as f:
            test_rows = json.load(f)
        test_ds = SynapseDataset(test_rows, word2idx, maps, keys, args.max_len)
        test_loader = DataLoader(
            test_ds, batch_size=args.batch_size, shuffle=False, collate_fn=_collate
        )
        test_loss, test_metrics_raw = evaluate(model, test_loader, criterions, device, keys)
        test_per_source = evaluate_per_source(
            model, test_rows, word2idx, maps, criterions, device, keys, args.max_len, args.batch_size
        )
        test_metrics = {
            "skipped": False,
            "test_loss": test_loss,
            "metrics": test_metrics_raw,
            "by_source": test_per_source,
            "source_summary": source_metrics_summary(test_per_source),
            "head_detail": collect_head_details(model, test_loader, device, keys),
        }
    else:
        print(f"Aviso: no existe {args.test}, se omite evaluación test.", file=sys.stderr)

    save_json(args.out_dir / "test_metrics.json", test_metrics)

    dod = evaluate_dod(val_metrics_final, keys)
    majority_ok = True
    majority_detail: Dict[str, Any] = {}
    for k in keys:
        mk = f"f1_macro_{k}"
        ok = val_metrics_final[mk] > baselines[k]
        majority_detail[k] = {
            "model_macro_f1": val_metrics_final[mk],
            "majority_baseline_macro_f1": baselines[k],
            "pass": ok,
        }
        majority_ok = majority_ok and ok
    dod["majority_baseline_all_pass"] = majority_ok
    dod["majority_baseline"] = majority_detail

    gap_nivel = best_train_metrics.get("f1_macro_nivel_tecnico", 0.0) - val_metrics_final.get(
        "f1_macro_nivel_tecnico", 0.0
    )
    gap_urg = best_train_metrics.get("f1_macro_urgencia", 0.0) - val_metrics_final.get(
        "f1_macro_urgencia", 0.0
    )
    dod["overfit_warnings"] = {
        "nivel_tecnico_train_val_macro_f1_gap": float(gap_nivel),
        "urgencia_train_val_macro_f1_gap": float(gap_urg),
        "unstable_nivel": gap_nivel > OVERFIT_F1_GAP_WARN,
        "unstable_urgencia": gap_urg > OVERFIT_F1_GAP_WARN,
    }
    dod["best_epoch"] = best_epoch
    dod["checkpoint_metric"] = {"name": args.early_stop_metric, "value": float(best_score)}
    dod["val_source_summary"] = source_metrics_summary(val_per_source_final)
    save_json(args.out_dir / "dod_report.json", dod)

    print(
        f"DoD (val): all_pass={dod['all_pass']}, majority_baseline_all_pass={majority_ok}, "
        f"unstable_nivel={dod['overfit_warnings']['unstable_nivel']}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
