# ADR-008: Clasificador TextCNN propio (FastText) en lugar de DistilBETO

## Contexto

La documentación y el roadmap previos asumían **fine-tuning** de `dccuchile/distilbert-base-spanish-wwm-cased` (DistilBETO) con un encabezado multi-label de 26 salidas y exportación vía Optimum.

Los requisitos académicos exigen:

- **Red neuronal diseñada y entrenada desde cero** (sin fine-tuning de transformer preentrenado como cuerpo del modelo).
- Uso permitido de **embeddings preentrenados** (p. ej. FastText) como entrada.
- Inferencia local en navegador con **ONNX Runtime Web** y **WebGPU**.

Además, el producto define **una sola etiqueta por dimensión** por mensaje: la formulación correcta es **multi-task single-label** (4 × `CrossEntropyLoss`), no 26 sigmoides + `BCEWithLogitsLoss`.

## Decisión

1. Reemplazar DistilBETO por **SynapseTextCNN**: CNN 1D sobre embeddings inicializados con **FastText español (300d)**, con 4 cabezas lineales (3+3+9+11 clases).
2. Entrenar con **PyTorch** en Colab; exportar ONNX con `**torch.onnx.export`\*\*, no con `optimum-cli`.
3. Congelar embeddings las primeras épocas; luego descongelar con menor learning rate (ver `fine-tuning-process.md`).

## Alternativas consideradas

| Opción                                | Por qué no es la principal                                          |
| ------------------------------------- | ------------------------------------------------------------------- |
| Seguir con DistilBETO                 | Viola restricción académica de “desde cero”                         |
| Solo MLP sobre media de embeddings    | Menor capacidad en patrones locales; peor en textos cortos ruidosos |
| BiLSTM                                | Mayor riesgo de compatibilidad/eficiencia en ONNX WebGPU            |
| Transformer “scratch” sin pretraining | Insostenible con ~2k–6k ejemplos                                    |

## Consecuencias

- **Positivas:** Modelo más ligero; narrativa académica clara; operadores ONNX ampliamente soportados; alineación con etiquetas categóricas.
- **Negativas:** Menor techo de calidad vs. BERT grande si el dataset crece poco; hay que mantener `vocab.json` + preprocesado JS alineados con Python.
- **Mitigación:** Aumentar dataset a ~10k-12k; augmentación dirigida; **`--class-weights`** en `train_textcnn.py` si hay desbalance extremo.

## Implementación de referencia

- Modelo: `neural_network/scripts/textcnn_model.py`
- Etiquetas: `neural_network/scripts/training_labels.py`
- Entrenamiento / ONNX: `neural_network/scripts/train_textcnn.py`, `neural_network/scripts/export_onnx.py`
