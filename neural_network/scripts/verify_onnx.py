#!/usr/bin/env python3
"""
Verifica que un export ONNX coincide con el checkpoint PyTorch (paridad numérica).

Uso típico (misma carpeta de corrida):
  pip install onnxruntime torch
  python neural_network/scripts/verify_onnx.py \\
    --checkpoint neural_network/notebook/data/checkpoints/textcnn_run/best.pt \\
    --onnx neural_network/notebook/data/checkpoints/textcnn_run/synapse_textcnn.onnx

Si el export usó --calibration, pásalo (o se detecta posthoc_calibration.json junto al checkpoint):
  python neural_network/scripts/verify_onnx.py --checkpoint .../best.pt --onnx .../synapse_textcnn.onnx \\
    --calibration .../posthoc_calibration.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_onnx import ONNXWrapper
from textcnn_model import SynapseTextCNN
from train_textcnn import encode_text

HEAD_ORDER = ("nivel_tecnico", "urgencia", "emocion", "dominio")
ONNX_OUT_NAMES = (
    "logits_nivel_tecnico",
    "logits_urgencia",
    "logits_emocion",
    "logits_dominio",
)


def _pad(ids: List[int], max_len: int, pad_id: int) -> List[int]:
    ids = ids[:max_len]
    return ids + [pad_id] * (max_len - len(ids))


def _load_biases(path: Optional[Path]) -> Optional[Dict[str, List[float]]]:
    if path is None or not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    biases = data.get("biases")
    if not isinstance(biases, dict):
        raise ValueError(f"{path} no contiene objeto 'biases'")
    return biases


def _build_torch_model(
    ckpt: dict, biases: Optional[Dict[str, List[float]]]
) -> torch.nn.Module:
    num_labels = ckpt["num_labels"]
    word2idx = ckpt["word2idx"]
    embed_dim = ckpt["model_state"]["embedding.weight"].shape[1]
    core = SynapseTextCNN(
        vocab_size=len(word2idx),
        num_labels=num_labels,
        embed_dim=embed_dim,
        padding_idx=word2idx.get("<pad>", 0),
    )
    core.load_state_dict(ckpt["model_state"])
    core.eval()
    return ONNXWrapper(core, biases=biases)


def _torch_forward(
    model: torch.nn.Module, input_ids: torch.Tensor
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    with torch.no_grad():
        out = model(input_ids)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Paridad PyTorch vs ONNX Runtime (CPU)")
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--onnx", type=Path, required=True)
    ap.add_argument(
        "--calibration",
        type=Path,
        default=None,
        help="JSON con biases (export_onnx --calibration). Por defecto: posthoc_calibration.json junto al checkpoint.",
    )
    ap.add_argument(
        "--no-calibration",
        action="store_true",
        help="Forzar biases cero aunque exista posthoc_calibration.json",
    )
    ap.add_argument(
        "--rtol",
        type=float,
        default=1e-4,
        help="Tolerancia relativa np.allclose (salvo logits_emocion usa 5e-4 por defecto si no se pasa)",
    )
    ap.add_argument("--atol", type=float, default=1e-5)
    args = ap.parse_args()

    try:
        import onnxruntime as ort
    except ImportError as e:
        print("Instala onnxruntime: pip install onnxruntime", file=sys.stderr)
        raise SystemExit(1) from e

    ckpt_path = args.checkpoint.expanduser().resolve()
    onnx_path = args.onnx.expanduser().resolve()
    if not ckpt_path.is_file():
        print(f"No existe checkpoint: {ckpt_path}", file=sys.stderr)
        return 1
    if not onnx_path.is_file():
        print(f"No existe ONNX: {onnx_path}", file=sys.stderr)
        return 1

    ckpt = torch.load(ckpt_path, map_location="cpu")
    word2idx: Dict[str, int] = ckpt["word2idx"]
    max_len: int = int(ckpt["max_len"])
    pad_id = int(word2idx["<pad>"])

    cal_path = args.calibration
    if cal_path is not None:
        cal_path = cal_path.expanduser().resolve()
    elif not args.no_calibration:
        cand = ckpt_path.parent / "posthoc_calibration.json"
        if cand.is_file():
            cal_path = cand

    biases = None if args.no_calibration else _load_biases(cal_path)
    if biases is not None:
        print(f"Usando calibración post-hoc: {cal_path}")
    else:
        print("Sin biases post-hoc (export sin --calibration o --no-calibration).")

    torch_model = _build_torch_model(ckpt, biases)
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    in_meta = sess.get_inputs()[0]
    if in_meta.name != "input_ids":
        print(f"Aviso: entrada ONNX se llama {in_meta.name!r}, se esperaba input_ids.", file=sys.stderr)

    samples = [
        "¿Cómo hago un deploy en Kubernetes con urgencia?",
        "No entiendo nada de React hooks help",
        "python django base de datos error 500",
        "neutral short",
    ]

    worst: Tuple[str, str, float] = ("", "", 0.0)
    for text in samples:
        ids = _pad(encode_text(text, word2idx, max_len), max_len, pad_id)
        x = torch.tensor([ids], dtype=torch.long)
        np_ids = np.array([ids], dtype=np.int64)

        t_out = _torch_forward(torch_model, x)
        o_list = sess.run(None, {in_meta.name: np_ids})
        # ORT devuelve en el orden de salidas del modelo
        names = [o.name for o in sess.get_outputs()]
        o_map = dict(zip(names, o_list))

        for i, head in enumerate(HEAD_ORDER):
            oname = ONNX_OUT_NAMES[i]
            arr_t = t_out[i].numpy()
            arr_o = o_map.get(oname)
            if arr_o is None and len(o_list) == 4:
                arr_o = o_list[i]
            if arr_o is None:
                print(f"Falta salida ONNX {oname}; salidas: {names}", file=sys.stderr)
                return 1
            arr_on = np.asarray(arr_o, dtype=np.float32)
            arr_tn = np.asarray(arr_t, dtype=np.float32)
            diff = float(np.max(np.abs(arr_tn - arr_on)))
            tag = f"{text[:40]!r} / {head}"
            if diff > worst[2]:
                worst = (text[:48], head, diff)
            rtol = args.rtol
            if head == "emocion":
                rtol = max(rtol, 5e-4)
            if not np.allclose(arr_tn, arr_on, rtol=rtol, atol=args.atol):
                print(
                    f"FALLO paridad {tag}: max|diff|={diff:.6g} rtol={rtol} atol={args.atol}",
                    file=sys.stderr,
                )
                print("  Si exportaste sin --calibration, prueba: --no-calibration", file=sys.stderr)
                print("  Si exportaste con --calibration, asegura --calibration correcto.", file=sys.stderr)
                return 1

    print("OK: paridad PyTorch vs ONNXRuntime (CPU) en frases de prueba.")
    print(f"  Peor max|diff| observado: {worst[2]:.6g} (cabezal {worst[1]}, texto …{worst[0]!r})")
    print(f"  Checkpoint: {ckpt_path}")
    print(f"  ONNX:       {onnx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
