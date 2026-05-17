#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from torch.utils.data import DataLoader, Dataset

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from textcnn_model import SynapseTextCNN
from training_labels import HEAD_KEYS, IGNORE_LABEL_INDEX, LABEL_SPECS, label_to_idx_maps

KEYS: Tuple[str, ...] = HEAD_KEYS
_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


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
    field_aliases = {"dominio": ("dominio", "domain_synapse")}
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


def normalize_text_for_dup(s: str) -> str:
    t = s.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t[:2000]


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

    def __getitem__(self, i: int) -> Tuple[torch.Tensor, Dict[str, int], str]:
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
        pad = self.word2idx.get("<pad>", 0)
        if len(ids) < self.max_len:
            ids = ids + [pad] * (self.max_len - len(ids))
        else:
            ids = ids[: self.max_len]
        x = torch.tensor(ids, dtype=torch.long)
        y = row_labels_from_row(row, self.maps, self.keys)
        fuente = str(row.get("fuente") or "unknown")
        return x, y, fuente


def collate_fn(
    batch: List[Tuple[torch.Tensor, Dict[str, int], str]], key_order: Tuple[str, ...]
) -> Tuple[torch.Tensor, Dict[str, torch.Tensor], List[str]]:
    xs = [b[0] for b in batch]
    x = torch.stack(xs, dim=0)
    ys: Dict[str, torch.Tensor] = {
        k: torch.tensor([b[1][k] for b in batch], dtype=torch.long) for k in key_order
    }
    fuentes = [b[2] for b in batch]
    return x, ys, fuentes


def head_detail_json(y_true: np.ndarray, y_pred: np.ndarray, label_names: Tuple[str, ...]) -> Dict[str, Any]:
    if len(y_true) == 0:
        return {
            "labels_order": list(label_names),
            "f1_per_class": {},
            "confusion_matrix": [],
            "note": "no_supervised_rows_for_head",
        }
    n = len(label_names)
    labels_idx = np.arange(n)
    _, _, f1_each, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels_idx, average=None, zero_division=0
    )
    f1_arr = np.asarray(f1_each, dtype=np.float64).reshape(-1)
    cm = confusion_matrix(y_true, y_pred, labels=labels_idx)
    return {
        "labels_order": list(label_names),
        "f1_per_class": {label_names[i]: float(f1_arr[i]) for i in range(n)},
        "confusion_matrix": cm.tolist(),
    }


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


@torch.no_grad()
def evaluate_full(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    keys: Tuple[str, ...],
    label_specs: Dict[str, Tuple[str, ...]],
) -> Dict[str, Any]:
    model.eval()
    criterions = {k: nn.CrossEntropyLoss(ignore_index=IGNORE_LABEL_INDEX) for k in keys}
    total_nll = 0.0
    n_batches = 0
    all_true: Dict[str, List[int]] = {k: [] for k in keys}
    all_pred: Dict[str, List[int]] = {k: [] for k in keys}
    all_fuente: List[str] = []

    for xb, yb, fuentes in loader:
        xb = xb.to(device)
        logits = model(xb)
        batch_loss = 0.0
        for k in keys:
            yk = yb[k].to(device)
            if (yk == IGNORE_LABEL_INDEX).all():
                continue
            batch_loss += criterions[k](logits[k], yk).item()
        total_nll += batch_loss
        n_batches += 1
        for k in keys:
            pred = logits[k].argmax(dim=-1).cpu().numpy()
            y_cpu = yb[k].numpy()
            all_pred[k].extend(pred.tolist())
            all_true[k].extend(y_cpu.tolist())
        all_fuente.extend(fuentes)

    y_true_np = {k: np.array(all_true[k]) for k in keys}
    y_pred_np = {k: np.array(all_pred[k]) for k in keys}
    metrics = aggregate_metrics(y_true_np, y_pred_np, keys)
    mean_nll = total_nll / max(n_batches, 1)

    head_detail = {
        k: head_detail_json(y_true_np[k], y_pred_np[k], label_specs[k]) for k in keys
    }

    per_source: Dict[str, Dict[str, Any]] = {}
    src_indices: Dict[str, List[int]] = defaultdict(list)
    for i, f in enumerate(all_fuente):
        src_indices[f].append(i)
    for src, idxs in src_indices.items():
        if len(idxs) < 5:
            per_source[src] = {"note": "skipped_few_rows", "n": len(idxs)}
            continue
        idxs_arr = np.array(idxs)
        yt_s = {k: y_true_np[k][idxs_arr] for k in keys}
        yp_s = {k: y_pred_np[k][idxs_arr] for k in keys}
        per_source[src] = {
            "n": len(idxs),
            "metrics": aggregate_metrics(yt_s, yp_s, keys),
        }

    return {
        "mean_nll_sum_heads": mean_nll,
        "metrics": metrics,
        "head_detail": head_detail,
        "per_source": per_source,
        "y_true": {k: y_true_np[k].tolist() for k in keys},
        "y_pred": {k: y_pred_np[k].tolist() for k in keys},
    }



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


def split_class_counts(rows: List[Dict[str, Any]], maps: Dict[str, Dict[str, int]], keys: Tuple[str, ...]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Counter[str]] = {k: Counter() for k in keys}
    for row in rows:
        y = row_labels_from_row(row, maps, keys)
        for k in keys:
            yi = y[k]
            if yi == IGNORE_LABEL_INDEX:
                continue
            inv = {v: lab for lab, v in maps[k].items()}
            out[k][inv[yi]] += 1
    return {k: dict(v) for k, v in out.items()}


def supervision_coverage_by_split(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Cuenta filas con supervision[head]==True vs False por cabeza (legacy sin supervision => todo True)."""
    heads = ("nivel_tecnico", "urgencia", "emocion", "dominio")
    acc: Dict[str, Dict[str, int]] = {h: {"supervised_rows": 0, "unsupervised_rows": 0} for h in heads}
    for r in rows:
        sup = r.get("supervision")
        for h in heads:
            if not isinstance(sup, dict) or sup.get(h, True):
                acc[h]["supervised_rows"] += 1
            else:
                acc[h]["unsupervised_rows"] += 1
    return acc


def duplicate_overlap_across_splits(
    train_rows: List[Dict[str, Any]], val_rows: List[Dict[str, Any]], test_rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    def keys_set(rows: List[Dict[str, Any]]) -> set[str]:
        s: set[str] = set()
        for r in rows:
            t = r.get("texto") or r.get("text") or ""
            if not t and (r.get("title") or r.get("body")):
                t = (
                    str(r.get("title") or "").strip()
                    + "\n"
                    + str(r.get("body") or "").strip()
                ).strip()
            s.add(normalize_text_for_dup(str(t)))
        return s

    tr = keys_set(train_rows)
    va = keys_set(val_rows)
    te = keys_set(test_rows)
    train_val = len(tr & va)
    train_test = len(tr & te)
    val_test = len(va & te)
    return {
        "train_unique": len(tr),
        "val_unique": len(va),
        "test_unique": len(te),
        "intersection_train_val": train_val,
        "intersection_train_test": train_test,
        "intersection_val_test": val_test,
    }


def bootstrap_f1_mean(
    y_true: Dict[str, np.ndarray], y_pred: Dict[str, np.ndarray], keys: Tuple[str, ...], n_boot: int, seed: int
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    n = len(y_true[keys[0]])
    means: List[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt = {k: y_true[k][idx] for k in keys}
        yp = {k: y_pred[k][idx] for k in keys}
        means.append(aggregate_metrics(yt, yp, keys)["f1_macro_mean"])
    arr = np.array(means)
    return {
        "n_boot": n_boot,
        "f1_macro_mean_mean": float(arr.mean()),
        "f1_macro_mean_std": float(arr.std()),
        "ci95_low": float(np.percentile(arr, 2.5)),
        "ci95_high": float(np.percentile(arr, 97.5)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--vocab", type=Path, required=True)
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--val", type=Path, required=True)
    ap.add_argument("--test", type=Path, required=True)
    ap.add_argument("--max-len", type=int, default=None, help="Por defecto usa max_len guardado en el checkpoint")
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--bootstrap", type=int, default=500)
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    with open(args.vocab, encoding="utf-8") as f:
        vocab_data = json.load(f)
    word2idx: Dict[str, int] = vocab_data["word2idx"]

    with open(args.train, encoding="utf-8") as f:
        train_rows = json.load(f)
    with open(args.val, encoding="utf-8") as f:
        val_rows = json.load(f)
    with open(args.test, encoding="utf-8") as f:
        test_rows = json.load(f)

    keys = KEYS
    maps = label_to_idx_maps()
    num_labels = {k: len(LABEL_SPECS[k]) for k in keys}

    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    max_len = int(args.max_len or ckpt.get("max_len", 96))
    model = SynapseTextCNN(
        vocab_size=len(word2idx),
        num_labels=num_labels,
        embed_dim=300,
        dropout=0.4,
        padding_idx=word2idx.get("<pad>", 0),
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    def make_loader(rows: List[Dict[str, Any]]) -> DataLoader:
        ds = SynapseDataset(rows, word2idx, maps, keys, max_len)

        def _collate(batch: List[Tuple[torch.Tensor, Dict[str, int], str]]) -> Tuple[torch.Tensor, Dict[str, torch.Tensor], List[str]]:
            return collate_fn(batch, keys)

        return DataLoader(ds, batch_size=args.batch_size, shuffle=False, collate_fn=_collate)

    val_loader = make_loader(val_rows)
    test_loader = make_loader(test_rows)

    val_out = evaluate_full(model, val_loader, device, keys, LABEL_SPECS)
    test_out = evaluate_full(model, test_loader, device, keys, LABEL_SPECS)

    dup = duplicate_overlap_across_splits(train_rows, val_rows, test_rows)
    train_counts = split_class_counts(train_rows, maps, keys)
    val_counts = split_class_counts(val_rows, maps, keys)
    test_counts = split_class_counts(test_rows, maps, keys)

    y_true_v = {k: np.array(val_out["y_true"][k], dtype=np.int64) for k in keys}
    y_pred_v_np = {k: np.array(val_out["y_pred"][k], dtype=np.int64) for k in keys}
    y_true_t = {k: np.array(test_out["y_true"][k], dtype=np.int64) for k in keys}
    y_pred_t_np = {k: np.array(test_out["y_pred"][k], dtype=np.int64) for k in keys}
    val_out.pop("y_true", None)
    val_out.pop("y_pred", None)
    test_out.pop("y_true", None)
    test_out.pop("y_pred", None)

    boot_val = bootstrap_f1_mean(y_true_v, y_pred_v_np, keys, args.bootstrap, 42)
    boot_test = bootstrap_f1_mean(y_true_t, y_pred_t_np, keys, args.bootstrap, 43)

    report: Dict[str, Any] = {
        "device": str(device),
        "checkpoint": str(args.checkpoint.resolve()),
        "n_rows": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
        "val": val_out,
        "test": test_out,
        "duplicate_overlap": dup,
        "class_counts": {"train": train_counts, "val": val_counts, "test": test_counts},
        "supervision_coverage": {
            "train": supervision_coverage_by_split(train_rows),
            "val": supervision_coverage_by_split(val_rows),
            "test": supervision_coverage_by_split(test_rows),
        },
        "source_summary": {
            "val": source_metrics_summary(val_out.get("per_source", {})),
            "test": source_metrics_summary(test_out.get("per_source", {})),
        },
        "bootstrap_f1_macro_mean": {"val": boot_val, "test": boot_test},
    }

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Wrote {args.out_json}", flush=True)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
