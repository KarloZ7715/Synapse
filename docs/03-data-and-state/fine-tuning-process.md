# Entrenamiento — Red neuronal propia (TextCNN) y ONNX

## 1. Resumen

Guía para **diseñar, entrenar y exportar desde cero** el clasificador de Synapse: una **TextCNN** sobre **embeddings preentrenados** (FastText español). Las capas convolucionales y densas son propias; **no** se hace fine-tuning de un transformer (BERT/DistilBERT).

Cada mensaje tiene **exactamente una etiqueta por dimensión** (multi-task **single-label**), no multi-label con 26 sigmoides.

```mermaid
graph LR
    A[Dataset final<br/>~2k-6k ejemplos] --> B[Split + vocab + FastText]
    B --> C[Entrenamiento PyTorch<br/>Google Colab T4]
    C --> D[Export ONNX<br/>torch.onnx.export]
    D --> E[Browser<br/>ONNX Runtime Web + WebGPU / WASM]

    style A fill:#1c1c22,stroke:#22d3ee,color:#ededef
    style B fill:#1c1c22,stroke:#c084fc,color:#ededef
    style C fill:#1c1c22,stroke:#fbbf24,color:#ededef
    style D fill:#1c1c22,stroke:#34d399,color:#ededef
    style E fill:#1c1c22,stroke:#4ade80,color:#ededef,stroke-width:2px
```

---

## 2. Formulación del problema

| Dimensión       | Clases | Salida del modelo | Pérdida por cabeza |
| --------------- | ------ | ----------------- | ------------------ |
| `nivel_tecnico` | 3      | logits `[C0]`     | `CrossEntropyLoss` |
| `urgencia`      | 3      | logits `[C1]`     | `CrossEntropyLoss` |
| `emocion`       | 9      | logits `[C2]`     | `CrossEntropyLoss` |
| `dominio`       | 11     | logits `[C3]`     | `CrossEntropyLoss` |

**Pérdida total:** \mathcal{L} = \sum\_{k} \mathcal{L}\_k (suma de las cuatro entropías cruzadas).

**Inferencia:** `argmax` por cabeza (sin sigmoid ni umbral 0.5).

> **Nota:** La redacción anterior basada en `26` salidas + `BCEWithLogitsLoss` correspondía a un esquema multi-label concatenado. Para Synapse (una etiqueta por dimensión) lo académicamente coherente es **4 cabezas softmax**.

Orden fijo de etiquetas: ver `dataset/scripts/training_labels.py`.

---

## 3. Comparación de arquitecturas candidatas

| Arquitectura                                            | Ventajas                                                                                            | Desventajas                                                                                        | ~2k ejemplos                                        | ONNX / Web                                |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ----------------------------------------- |
| **MLP** (pool mean de embeddings)                       | Mínima complejidad, muy rápida, fácil de exponer                                                    | Ignora orden y n-gramas locales                                                                    | Viable con embeddings fijos + regularización fuerte | Excelente                                 |
| **CNN 1D (TextCNN)**                                    | Captura patrones locales (“no entiendo”, “urgente”, nombres de tech); referencia clásica (Kim 2014) | Hiperparámetros (`k`, filtros)                                                                     | **Recomendada** con Congelar→Descongelar embed      | **Excelente** (Conv + ReLU + Pool + Gemm) |
| **BiLSTM**                                              | Mejor modelado de dependencias a largo plazo                                                        | Más parámetros; LSTM en ONNX Web a veces con soporte o rendimiento peores; entrenamiento más lento | Factible pero más riesgo de overfitting             | Revisar ops; a menudo más fallback WASM   |
| **Embedding + atención** (sin transformer preentrenado) | Interpretable (pesos de atención); buen baseline                                                    | Más trabajo de implementación y de export                                                          | Viable                                              | Buena si se usa MatMul/Softmax estándar   |

### Recomendación: **TextCNN + FastText (cc.es.300)**

- Buen equilibrio **calidad / datos limitados / tamaño del modelo / explicabilidad**.
- Exportación ONNX con operadores ampliamente soportados en **ONNX Runtime Web**.
- Tamaño en disco típico **mucho menor** que un DistilBERT cuantizado (solo embedding table + CNN pequeña; ver sección 10).

---

## 4. Arquitectura detallada (SynapseTextCNN)

Implementación de referencia: `dataset/scripts/textcnn_model.py`.

| Componente          | Tamaño / notas                                       |
| ------------------- | ---------------------------------------------------- |
| `Embedding`         | `vocab_size × 300`, inicializado con FastText `.vec` |
| `Conv1d` kernels    | tamaños `3, 4, 5`, `100` filtros por kernel          |
| `MaxPool1d`         | global por canal                                     |
| `Linear` compartida | `300 → 256` + `ReLU` + `Dropout`                     |
| Cabezas             | `256 → 3`, `256 → 3`, `256 → 9`, `256 → 11`          |

**Secuencia:** tokens → embedding `[B,L,300]` → Conv1d sobre dim de características → ReLU → max-over-time → concatenar → FC → 4 logits.

---

## 5. Preprocesado de texto

1. **Normalizar:** minúsculas; tokenización con regex de palabras (`[^\W\d_]+` con bandera Unicode) — ver `build_vocab.py` / `train_textcnn.py`.
2. **Índices:** `word2idx` con `<pad>=0`, `<unk>=1`.
3. **Longitud:** `max_len` recomendado **96** (ajustable 64–128).
4. **Padding:** relleno con `<pad>` a la derecha.

---

## 6. Pipeline reproducible (scripts)

Requisitos en Colab o venv:

```bash
pip install torch scikit-learn numpy
```

### 6.1 Split train / val / test

```bash
python dataset/scripts/split_dataset.py \
  --input dataset/final/dataset.json \
  --out-dir dataset/final \
  --seed 42
```

Genera `train.json`, `val.json`, `test.json`, `split_meta.json`.

### 6.2 Vocabulario + matriz FastText

Descarga vectores (ej. Common Crawl español):

- [FastText Spanish CC vectors](https://fasttext.cc/docs/en/pretrained-vectors.html) — fichero `.vec` (descomprimido).

```bash
python dataset/scripts/build_vocab.py \
  --train dataset/final/train.json \
  --fasttext /ruta/a/cc.es.300.vec \
  --min-freq 2 \
  --max-vocab 40000 \
  --out-dir dataset/artifacts
```

Salidas: `dataset/artifacts/vocab.json`, `dataset/artifacts/embedding_init.pt`.

### 6.3 Entrenamiento

```bash
python dataset/scripts/train_textcnn.py \
  --train dataset/final/train.json \
  --val dataset/final/val.json \
  --vocab dataset/artifacts/vocab.json \
  --embedding dataset/artifacts/embedding_init.pt \
  --out-dir dataset/checkpoints/textcnn_run1 \
  --max-len 96 \
  --epochs 80 \
  --batch-size 32 \
  --lr 1e-3 \
  --weight-decay 1e-2 \
  --dropout 0.4 \
  --freeze-epochs 5 \
  --patience 8
```

**Hiperparámetros iniciales (T4):**

| Parámetro       | Valor inicial                                      |
| --------------- | -------------------------------------------------- |
| `lr`            | `1e-3` (AdamW); tras descongelar embedding, `5e-4` |
| `batch_size`    | `32` (subir si hay RAM; bajar si OOM)              |
| `epochs`        | hasta `80` con early stopping                      |
| `weight_decay`  | `1e-2`                                             |
| `dropout`       | `0.3`–`0.5`                                        |
| `freeze_epochs` | `5` (solo conv+fc entrenan)                        |

**Regularización y datos pequeños:**

- Early stopping por `**f1_macro_mean`\*\* en validación.
- `clip_grad_norm_` (1.0) ya aplicado en script.
- Si hay clases muy minoritarias: **class weights** en `CrossEntropyLoss` (extensión opcional del script).
- Reportar métricas por cabeza: **F1 macro y micro**; guardar `best_metrics.json`.

### 6.4 Evaluación en test

Cargar `best.pt` y correr un paso similar al bucle de `evaluate()` en `train_textcnn.py` sobre `test.json` (script extra opcional).

---

## 7. Exportación a ONNX (`torch.onnx.export`)

No se usa Hugging Face Optimum (orientado a modelos HF). Flujo recomendado:

```bash
python dataset/scripts/export_onnx.py \
  --checkpoint dataset/checkpoints/textcnn_run1/best.pt \
  --out synapse_textcnn.onnx \
  --opset 17
```

**Entradas / salidas:**

| Nombre                 | Tipo      | Shape              |
| ---------------------- | --------- | ------------------ |
| `input_ids`            | `int64`   | `[batch, seq_len]` |
| `logits_nivel_tecnico` | `float32` | `[batch, 3]`       |
| `logits_urgencia`      | `float32` | `[batch, 3]`       |
| `logits_emocion`       | `float32` | `[batch, 9]`       |
| `logits_dominio`       | `float32` | `[batch, 11]`      |

Validación rápida en Python:

```python
import numpy as np
import onnxruntime as ort

sess = ort.InferenceSession("synapse_textcnn.onnx", providers=["CPUExecutionProvider"])
# ids: np.int64 [1, seq]
out = sess.run(None, {"input_ids": ids})
```

**Cuantización INT8 (opcional):** usar `onnxruntime.quantization` (post-training) si se necesita reducir tamaño; validar después en ORT Web.

---

## 8. Ejecución en el navegador (ONNX Runtime Web + WebGPU)

```javascript
import * as ort from "onnxruntime-web/webgpu";

const session = await ort.InferenceSession.create(
  "/models/synapse_textcnn.onnx",
  {
    executionProviders: ["webgpu", "wasm"],
  },
);

const inputIds = new ort.Tensor("int64", bigInt64ArrayFromTokenizer, [
  1,
  seqLen,
]);
const outs = await session.run({ input_ids: inputIds });

function argmax(arr) {
  let j = 0;
  for (let i = 1; i < arr.length; i++) if (arr[i] > arr[j]) j = i;
  return j;
}

const nivelIdx = argmax(outs.logits_nivel_tecnico.data);
// Mapear índices → strings con los mismos órdenes que training_labels.py
```

**Cabeceras COOP/COEP** para `SharedArrayBuffer` / multi-hilo: igual que antes (p. ej. Cloudflare `_headers`).

---

## 9. ¿Son suficientes ~2000 ejemplos?

- **Mínimo defendible:** ~2000 ejemplos **curados y balanceados**, con embeddings FastText, red **pequeña**, early stopping y augmentación dirigida a clases minoritarias.
- **Recomendado para producción sólida:** **4000–6000** ejemplos (especialmente para `emocion` y `dominio`).
- **Mínimo por clase minoritaria:** apuntar a **≥100–150** ejemplos reales+aumentados; ideal **≥200** por etiqueta rara.
- **Parámetros entrenables:** del orden **10⁵–10⁶** si el embedding empieza congelado; al descongelar, el embedding domina el recuento total (sigue siendo factible en T4 con vocab moderado).

---

## 10. Tamaño del artefacto (orden de magnitud)

| Componente             | Notas                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------ |
| `synapse_textcnn.onnx` | CNN + cabezas en FP32 suele ser **< 5–15 MB** según vocab y si el embedding va embebido completo |
| Vocab + tokenizer TS   | `vocab.json` **~hundreds KB–few MB**                                                             |

Mucho menor que un transformer tipo DistilBERT en INT8 (~28MB solo del encoder).

---

## 11. Referencias

- Yoon Kim, Convolutional Neural Networks for Sentence Classification, EMNLP 2014.
- FastText embeddings: [fasttext.cc](https://fasttext.cc/)
- ONNX Runtime Web + WebGPU: [tutorial](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html)
- PyTorch ONNX: [torch.onnx.export](https://docs.pytorch.org/docs/stable/onnx.html)
