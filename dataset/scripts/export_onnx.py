#!/usr/bin/env python3
"""
Exporta SynapseTextCNN entrenado a ONNX para ONNX Runtime Web.

Entrada: int64 input_ids [batch, seq] (nombre: input_ids)
Salidas: logits_nivel, logits_urgencia, logits_emocion, logits_dominio (float32)

Uso:
  python dataset/scripts/export_onnx.py \\
    --checkpoint dataset/checkpoints/textcnn_default/best.pt \\
    --out synapse_textcnn.onnx \\
    --opset 17

Validar en Python:
  pip install onnxruntime
  python -c "import onnxruntime as ort; ..."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from textcnn_model import SynapseTextCNN


class ONNXWrapper(nn.Module):
    def __init__(self, core: SynapseTextCNN) -> None:
        super().__init__()
        self.core = core

    def forward(self, input_ids: torch.Tensor) -> tuple:
        out = self.core(input_ids)
        return (
            out["nivel_tecnico"],
            out["urgencia"],
            out["emocion"],
            out["dominio"],
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("synapse_textcnn.onnx"))
    ap.add_argument("--opset", type=int, default=17)
    args = ap.parse_args()

    ckpt = torch.load(args.checkpoint, map_location="cpu")
    num_labels = ckpt["num_labels"]
    max_len = ckpt["max_len"]
    word2idx = ckpt["word2idx"]

    embed_dim = ckpt["model_state"]["embedding.weight"].shape[1]
    core = SynapseTextCNN(
        vocab_size=len(word2idx),
        num_labels=num_labels,
        embed_dim=embed_dim,
        padding_idx=word2idx.get("<pad>", 0),
    )
    core.load_state_dict(ckpt["model_state"])
    wrapped = ONNXWrapper(core)
    wrapped.eval()

    dummy = torch.zeros((1, max_len), dtype=torch.long)
    torch.onnx.export(
        wrapped,
        dummy,
        args.out,
        input_names=["input_ids"],
        output_names=[
            "logits_nivel_tecnico",
            "logits_urgencia",
            "logits_emocion",
            "logits_dominio",
        ],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "seq_len"},
            "logits_nivel_tecnico": {0: "batch"},
            "logits_urgencia": {0: "batch"},
            "logits_emocion": {0: "batch"},
            "logits_dominio": {0: "batch"},
        },
        opset_version=args.opset,
        do_constant_folding=True,
    )
    print(f"Exportado: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
