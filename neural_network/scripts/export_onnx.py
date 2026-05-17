#!/usr/bin/env python3
"""
Exporta SynapseTextCNN entrenado a ONNX para ONNX Runtime Web.

Entrada: int64 input_ids [batch, seq] (nombre: input_ids)
Salidas: logits_nivel, logits_urgencia, logits_emocion, logits_dominio (float32)

Uso:
  python neural_network/scripts/export_onnx.py \\
    --checkpoint dataset/final/checkpoints/textcnn_default/best.pt \\
    --out synapse_textcnn.onnx \\
    --opset 17

Validar paridad vs checkpoint:
  pip install onnxruntime
  python neural_network/scripts/verify_onnx.py --checkpoint .../best.pt --onnx .../synapse_textcnn.onnx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import torch
import torch.nn as nn

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from textcnn_model import SynapseTextCNN


class ONNXWrapper(nn.Module):
    def __init__(self, core: SynapseTextCNN, biases: Optional[Dict[str, List[float]]] = None) -> None:
        super().__init__()
        self.core = core
        biases = biases or {}
        for head in ("nivel_tecnico", "urgencia", "emocion", "dominio"):
            raw = biases.get(head)
            tensor = torch.tensor(raw, dtype=torch.float32) if raw is not None else torch.zeros(core.num_labels[head])
            self.register_buffer(f"bias_{head}", tensor)

    def forward(self, input_ids: torch.Tensor) -> tuple:
        out = self.core(input_ids)
        return (
            out["nivel_tecnico"] + self.bias_nivel_tecnico,
            out["urgencia"] + self.bias_urgencia,
            out["emocion"] + self.bias_emocion,
            out["dominio"] + self.bias_dominio,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("synapse_textcnn.onnx"))
    ap.add_argument("--opset", type=int, default=17)
    ap.add_argument("--calibration", type=Path, default=None, help="JSON de calibrate_checkpoint.py con biases post-hoc")
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
    biases = None
    if args.calibration is not None:
        with open(args.calibration, encoding="utf-8") as f:
            calibration = json.load(f)
        biases = calibration.get("biases")
        if not isinstance(biases, dict):
            raise ValueError(f"{args.calibration} no contiene objeto 'biases'")
        print(f"Aplicando calibración post-hoc desde: {args.calibration}")
    wrapped = ONNXWrapper(core, biases=biases)
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
        dynamo=False,
    )
    print(f"Exportado: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
