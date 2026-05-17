#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from textcnn_model import SynapseTextCNN
from training_labels import HEAD_KEYS, IGNORE_LABEL_INDEX, LABEL_SPECS, label_to_idx_maps

_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(str(text).lower()) if t.strip()]


def row_text(row: Dict[str, Any]) -> str:
    text = str(row.get("texto") or row.get("text") or "").strip()
    if not text and (row.get("title") or row.get("body")):
        text = (str(row.get("title") or "").strip() + "\n" + str(row.get("body") or "").strip()).strip()
    return text


def token_windows(tokens: List[str], max_len: int, views: str) -> List[List[str]]:
    if views == "head":
        return [tokens[:max_len]]
    out = [tokens[:max_len]]
    if len(tokens) > max_len:
        out.append(tokens[-max_len:])
        half = max(1, max_len // 2)
        out.append((tokens[:half] + tokens[-(max_len - half):])[:max_len])
    if views == "head_tail":
        return out
    # score mode: add a middle window for long SO bodies.
    if len(tokens) > max_len * 2:
        mid = len(tokens) // 2
        start = max(0, mid - max_len // 2)
        out.append(tokens[start : start + max_len])
    return out


def encode_window(tokens: List[str], word2idx: Dict[str, int], max_len: int) -> List[int]:
    unk = word2idx.get("<unk>", 1)
    pad = word2idx.get("<pad>", 0)
    ids = [word2idx.get(t, unk) for t in tokens[:max_len]]
    return ids + [pad] * (max_len - len(ids))


def row_labels(row: Dict[str, Any], maps: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    defaults = {"nivel_tecnico": "principiante", "urgencia": "media", "emocion": "neutral", "dominio": "general"}
    y: Dict[str, int] = {}
    sup = row.get("supervision")
    for head in HEAD_KEYS:
        if isinstance(sup, dict) and sup.get(head) is False:
            y[head] = IGNORE_LABEL_INDEX
            continue
        raw = row.get(head)
        if head == "dominio" and not raw:
            raw = row.get("domain_synapse")
        label = str(raw or defaults[head]).strip()
        y[head] = maps[head].get(label, maps[head][defaults[head]])
    return y


class TTADataset(Dataset):
    def __init__(self, rows: List[Dict[str, Any]], word2idx: Dict[str, int], max_len: int, views: str) -> None:
        self.rows = rows
        self.word2idx = word2idx
        self.max_len = max_len
        self.views = views
        self.maps = label_to_idx_maps()

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, int]]:
        row = self.rows[idx]
        toks = tokenize(row_text(row))
        windows = token_windows(toks, self.max_len, self.views)
        encoded = [encode_window(w, self.word2idx, self.max_len) for w in windows]
        return torch.tensor(encoded, dtype=torch.long), row_labels(row, self.maps)


def collate(batch: List[Tuple[torch.Tensor, Dict[str, int]]]) -> Tuple[torch.Tensor, Dict[str, torch.Tensor], torch.Tensor]:
    max_views = max(x.shape[0] for x, _ in batch)
    max_len = batch[0][0].shape[1]
    pad_id = 0
    xs = []
    mask = []
    ys = {h: [] for h in HEAD_KEYS}
    for x, y in batch:
        n = x.shape[0]
        if n < max_views:
            pad = torch.full((max_views - n, max_len), pad_id, dtype=torch.long)
            x = torch.cat([x, pad], dim=0)
        xs.append(x)
        mask.append([1] * n + [0] * (max_views - n))
        for h in HEAD_KEYS:
            ys[h].append(y[h])
    return torch.stack(xs, dim=0), {h: torch.tensor(v, dtype=torch.long) for h, v in ys.items()}, torch.tensor(mask, dtype=torch.float32)


@torch.no_grad()
def collect_logits(
    model: nn.Module,
    rows: List[Dict[str, Any]],
    word2idx: Dict[str, int],
    max_len: int,
    views: str,
    batch_size: int,
    device: torch.device,
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    loader = DataLoader(TTADataset(rows, word2idx, max_len, views), batch_size=batch_size, shuffle=False, collate_fn=collate)
    logits_out = {h: [] for h in HEAD_KEYS}
    y_out = {h: [] for h in HEAD_KEYS}
    model.eval()
    for xb, yb, view_mask in loader:
        bsz, nviews, seq_len = xb.shape
        flat = xb.reshape(bsz * nviews, seq_len).to(device)
        pred = model(flat)
        weights = view_mask.to(device).reshape(bsz, nviews, 1)
        denom = weights.sum(dim=1).clamp_min(1.0)
        for h in HEAD_KEYS:
            n_labels = pred[h].shape[-1]
            logits = pred[h].reshape(bsz, nviews, n_labels)
            avg = (logits * weights).sum(dim=1) / denom
            logits_out[h].append(avg.cpu().numpy())
            y_out[h].append(yb[h].numpy())
    return (
        {h: np.concatenate(logits_out[h], axis=0) for h in HEAD_KEYS},
        {h: np.concatenate(y_out[h], axis=0) for h in HEAD_KEYS},
    )


def macro_f1_for_logits(logits: np.ndarray, y_true: np.ndarray, bias: np.ndarray | None = None) -> float:
    mask = y_true != IGNORE_LABEL_INDEX
    if not mask.any():
        return 0.0
    adjusted = logits[mask] + (bias if bias is not None else 0.0)
    pred = adjusted.argmax(axis=1)
    return float(f1_score(y_true[mask], pred, average="macro", zero_division=0))


def fit_biases(logits_by_head: Dict[str, np.ndarray], y_by_head: Dict[str, np.ndarray]) -> Dict[str, List[float]]:
    biases: Dict[str, List[float]] = {}
    grid = np.array([-2.0, -1.5, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0])
    for head in HEAD_KEYS:
        n_labels = logits_by_head[head].shape[1]
        bias = np.zeros(n_labels, dtype=np.float32)
        best = macro_f1_for_logits(logits_by_head[head], y_by_head[head], bias)
        for _ in range(3):
            improved = False
            for cls in range(n_labels):
                local_best = best
                local_bias = float(bias[cls])
                for val in grid:
                    trial = bias.copy()
                    trial[cls] = val
                    score = macro_f1_for_logits(logits_by_head[head], y_by_head[head], trial)
                    if score > local_best + 1e-9:
                        local_best = score
                        local_bias = float(val)
                if local_best > best + 1e-9:
                    bias[cls] = local_bias
                    best = local_best
                    improved = True
            if not improved:
                break
        biases[head] = [float(x) for x in bias.tolist()]
    return biases


def metrics(logits_by_head: Dict[str, np.ndarray], y_by_head: Dict[str, np.ndarray], biases: Dict[str, List[float]] | None = None) -> Dict[str, float]:
    out: Dict[str, float] = {}
    vals = []
    for head in HEAD_KEYS:
        bias = np.array(biases[head], dtype=np.float32) if biases else None
        f1 = macro_f1_for_logits(logits_by_head[head], y_by_head[head], bias)
        out[f"f1_macro_{head}"] = f1
        vals.append(f1)
    out["f1_macro_mean"] = float(np.mean(vals))
    return out


def load_rows(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must be a JSON array")
    return [r for r in data if isinstance(r, dict)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Post-hoc TTA + class-bias calibration for Synapse TextCNN.")
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--val", type=Path, required=True)
    ap.add_argument("--test", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--views", choices=("head", "head_tail", "score"), default="score")
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    word2idx = ckpt["word2idx"]
    keys = tuple(ckpt.get("keys", HEAD_KEYS))
    if tuple(keys) != tuple(HEAD_KEYS):
        raise ValueError(f"Checkpoint heads mismatch: {keys}")
    max_len = int(ckpt.get("max_len", 160))
    num_labels = {h: len(LABEL_SPECS[h]) for h in HEAD_KEYS}
    model = SynapseTextCNN(
        vocab_size=len(word2idx),
        num_labels=num_labels,
        embed_dim=300,
        dropout=0.0,
        padding_idx=word2idx.get("<pad>", 0),
    ).to(device)
    model.load_state_dict(ckpt["model_state"])

    val_rows = load_rows(args.val)
    test_rows = load_rows(args.test)
    val_logits, val_y = collect_logits(model, val_rows, word2idx, max_len, args.views, args.batch_size, device)
    test_logits, test_y = collect_logits(model, test_rows, word2idx, max_len, args.views, args.batch_size, device)
    biases = fit_biases(val_logits, val_y)

    report = {
        "views": args.views,
        "checkpoint_epoch": ckpt.get("epoch"),
        "baseline_val": metrics(val_logits, val_y),
        "calibrated_val": metrics(val_logits, val_y, biases),
        "baseline_test": metrics(test_logits, test_y),
        "calibrated_test": metrics(test_logits, test_y, biases),
        "biases": biases,
        "labels": {h: list(LABEL_SPECS[h]) for h in HEAD_KEYS},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
