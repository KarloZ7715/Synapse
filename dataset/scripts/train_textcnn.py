#!/usr/bin/env python3
"""
Entrena SynapseTextCNN (PyTorch) en Colab o local.

Pérdida: suma de CrossEntropyLoss sobre 4 cabezas (multi-task single-label).

Uso (después de split_dataset + build_vocab):
  pip install torch scikit-learn
  python dataset/scripts/train_textcnn.py \\
    --train dataset/final/train.json \\
    --val dataset/final/val.json \\
    --vocab dataset/artifacts/vocab.json \\
    --embedding dataset/artifacts/embedding_init.pt \\
    --out-dir dataset/checkpoints/textcnn_run1 \\
    --epochs 80 --batch-size 32 --lr 1e-3 --patience 8
"""

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
from torch.utils.data import DataLoader, Dataset
from sklearn.metrics import f1_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from textcnn_model import SynapseTextCNN, count_parameters
from training_labels import LABEL_SPECS, label_to_idx_maps

_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text.lower()) if t.strip()]


def encode_text(text: str, word2idx: Dict[str, int], max_len: int) -> List[int]:
    unk = word2idx.get("<unk>", 1)
    toks = tokenize(text)[:max_len]
    return [word2idx.get(t, unk) for t in toks]


def pad_batch(seqs: List[List[int]], pad_idx: int, max_len: int) -> torch.Tensor:
    out = []
    for s in seqs:
        if len(s) > max_len:
            s = s[:max_len]
        out.append(s + [pad_idx] * (max_len - len(s)))
    return torch.tensor(out, dtype=torch.long)


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
        y = {}
        defaults = {
            "nivel_tecnico": "principiante",
            "urgencia": "media",
            "emocion": "neutral",
            "dominio": "general",
        }
        field_aliases = {
            "dominio": ("dominio", "domain_synapse"),
        }
        for k in self.keys:
            if k in field_aliases:
                alts = field_aliases[k]
                raw = str(row.get(alts[0]) or row.get(alts[1]) or "").strip()
            else:
                raw = str(row.get(k, "")).strip()
            lab_map = self.maps[k]
            if raw not in lab_map:
                raw = defaults[k]
            y[k] = lab_map[raw]
        return x, y


def collate_fn(
    batch, key_order: Tuple[str, ...]
) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
    xs = [b[0] for b in batch]
    x = torch.stack(xs, dim=0)
    ys: Dict[str, torch.Tensor] = {
        k: torch.tensor([b[1][k] for b in batch], dtype=torch.long) for k in key_order
    }
    return x, ys


def compute_f1_per_head(
    y_true: Dict[str, np.ndarray], y_pred: Dict[str, np.ndarray]
) -> Dict[str, float]:
    out = {}
    for k in y_true:
        out[f"f1_macro_{k}"] = float(
            f1_score(y_true[k], y_pred[k], average="macro", zero_division=0)
        )
        out[f"f1_micro_{k}"] = float(
            f1_score(y_true[k], y_pred[k], average="micro", zero_division=0)
        )
    macro_mean = float(np.mean([out[f"f1_macro_{k}"] for k in y_true]))
    out["f1_macro_mean"] = macro_mean
    return out


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
            batch_loss += criterions[k](logits[k], yb[k].to(device)).item()
        total_loss += batch_loss
        n_batches += 1
        for k in keys:
            pred = logits[k].argmax(dim=-1).cpu().numpy()
            all_pred[k].extend(pred.tolist())
            all_true[k].extend(yb[k].numpy().tolist())

    metrics = compute_f1_per_head(
        {k: np.array(all_true[k]) for k in keys},
        {k: np.array(all_pred[k]) for k in keys},
    )
    return total_loss / max(n_batches, 1), metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=PROJECT_ROOT / "dataset/final/train.json")
    ap.add_argument("--val", type=Path, default=PROJECT_ROOT / "dataset/final/val.json")
    ap.add_argument("--vocab", type=Path, default=PROJECT_ROOT / "dataset/artifacts/vocab.json")
    ap.add_argument("--embedding", type=Path, default=PROJECT_ROOT / "dataset/artifacts/embedding_init.pt")
    ap.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "dataset/checkpoints/textcnn_default")
    ap.add_argument("--max-len", type=int, default=96)
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-2)
    ap.add_argument("--dropout", type=float, default=0.4)
    ap.add_argument("--freeze-epochs", type=int, default=5, help="Congelar embeddings las primeras N epochs")
    ap.add_argument("--patience", type=int, default=8, help="Early stopping según f1_macro_mean en val")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    keys: Tuple[str, ...] = ("nivel_tecnico", "urgencia", "emocion", "dominio")
    num_labels = {k: len(LABEL_SPECS[k]) for k in keys}
    maps = label_to_idx_maps()
    # Mapa de alias dominio → índice (normalización)
    for row_domain in list(maps["dominio"].keys()):
        pass

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

    def _collate(batch):
        return collate_fn(batch, keys)

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=_collate
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=_collate
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    emb_cpu = torch.load(args.embedding, map_location="cpu")
    embed_dim = emb_cpu.shape[1]
    model = SynapseTextCNN(
        vocab_size=len(word2idx),
        num_labels=num_labels,
        embed_dim=embed_dim,
        dropout=args.dropout,
        padding_idx=word2idx.get("<pad>", 0),
    ).to(device)

    model.init_embedding_from_matrix(emb_cpu.to(device), freeze=True)
    print(f"Parámetros entrenables (inicial): {count_parameters(model)}")

    criterions = {k: nn.CrossEntropyLoss() for k in keys}
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    best_f1 = -1.0
    stale = 0

    for epoch in range(1, args.epochs + 1):
        if epoch == args.freeze_epochs + 1:
            model.embedding.weight.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr * 0.5, weight_decay=args.weight_decay)
            print(f"Epoch {epoch}: embeddings descongelados, lr -> {args.lr * 0.5}")

        model.train()
        for xb, yb in train_loader:
            xb = xb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = sum(criterions[k](logits[k], yb[k].to(device)) for k in keys)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        val_loss, metrics = evaluate(model, val_loader, criterions, device, keys)
        f1m = metrics["f1_macro_mean"]
        print(
            f"Epoch {epoch}: val_loss={val_loss:.4f} f1_macro_mean={f1m:.4f} "
            + " ".join(f"{k}={metrics[k]:.3f}" for k in sorted(metrics) if k.startswith("f1_macro_") and k != "f1_macro_mean")
        )

        if f1m > best_f1:
            best_f1 = f1m
            stale = 0
            ckpt = {
                "model_state": model.state_dict(),
                "num_labels": num_labels,
                "max_len": args.max_len,
                "word2idx": word2idx,
                "keys": list(keys),
                "epoch": epoch,
                "metrics_val": metrics,
            }
            torch.save(ckpt, args.out_dir / "best.pt")
            with open(args.out_dir / "best_metrics.json", "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
        else:
            stale += 1
            if stale >= args.patience:
                print(f"Early stopping en epoch {epoch} (mejor f1_macro_mean={best_f1:.4f})")
                break

    print(f"Mejor checkpoint: {args.out_dir / 'best.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
