#!/usr/bin/env python3
"""
Arquitectura TextCNN multi-cabeza para Synapse (entrenamiento + export ONNX).

No usa transformers pre-entrenados: solo Embedding inicializado con FastText
u otros vectores de palabras, y capas convolucionales/densas propias.
"""

from __future__ import annotations

from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class SynapseTextCNN(nn.Module):
    """
    TextCNN (Kim 2014) + 4 cabezas categóricas (multi-task single-label).

    Salidas: logits por cabeza (aplicar CrossEntropyLoss por cabeza en entrenamiento).
    """

    def __init__(
        self,
        vocab_size: int,
        num_labels: Dict[str, int],
        embed_dim: int = 300,
        num_filters: int = 100,
        filter_sizes: Tuple[int, ...] = (3, 4, 5),
        hidden_dim: int = 256,
        dropout: float = 0.4,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        self.padding_idx = padding_idx
        self.num_labels = dict(num_labels)
        self.filter_sizes = filter_sizes
        self.num_filters = num_filters

        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=padding_idx)
        self.convs = nn.ModuleList(
            [nn.Conv1d(embed_dim, num_filters, kernel_size=k) for k in filter_sizes]
        )
        conv_out_dim = num_filters * len(filter_sizes)
        self.dropout = nn.Dropout(dropout)
        self.fc_shared = nn.Linear(conv_out_dim, hidden_dim)
        self.heads = nn.ModuleDict(
            {
                "nivel_tecnico": nn.Linear(hidden_dim, num_labels["nivel_tecnico"]),
                "urgencia": nn.Linear(hidden_dim, num_labels["urgencia"]),
                "emocion": nn.Linear(hidden_dim, num_labels["emocion"]),
                "dominio": nn.Linear(hidden_dim, num_labels["dominio"]),
            }
        )

    def forward(self, input_ids: torch.Tensor) -> Dict[str, torch.Tensor]:
        # input_ids: [batch, seq_len]
        emb = self.embedding(input_ids)  # [B, L, D]
        emb = emb.transpose(1, 2)  # [B, D, L]
        conv_outs = []
        for conv in self.convs:
            h = conv(emb)  # [B, F, L']
            h = F.relu(h)
            h = F.max_pool1d(h, kernel_size=h.size(2))  # [B, F, 1]
            conv_outs.append(h.squeeze(2))
        x = torch.cat(conv_outs, dim=1)  # [B, F*len(k)]
        x = self.dropout(x)
        x = F.relu(self.fc_shared(x))
        x = self.dropout(x)
        return {k: self.heads[k](x) for k in self.heads}

    def init_embedding_from_matrix(
        self, matrix: torch.Tensor, freeze: bool = True
    ) -> None:
        """matrix: [vocab_size, embed_dim] alineado con ids del vocabulario."""
        with torch.no_grad():
            self.embedding.weight.copy_(matrix)
        self.embedding.weight.requires_grad = not freeze


def count_parameters(model: nn.Module, trainable_only: bool = True) -> int:
    if trainable_only:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)
    return sum(p.numel() for p in model.parameters())
