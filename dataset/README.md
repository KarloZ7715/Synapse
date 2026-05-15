# Dataset — Synapse

## Descripción

Dataset para entrenar la Red Neuronal clasificadora de Synapse. Combina:

- **GoEmotions ES**: Dataset de emociones en español (54,263 filas)
- **Stack Overflow ES**: Preguntas reales de programación en español
- **GitHub Copilot (copilot-api)**: Etiquetado de urgencia y nivel técnico

## Estructura

```
dataset/
├── raw/                          # Datos originales sin procesar
│   ├── goemotions_es.csv         # GoEmotions ES descargado
│   ├── goemotions_es.json        # GoEmotions ES en formato JSON
│   ├── so_questions.json         # Preguntas de Stack Overflow ES
│   └── backups/                  # Respaldos operativos de extracción
│
├── processed/                    # Datos procesados
│   ├── backups/                  # Snapshots de control de calidad fase 3
│   ├── goemotions_mapped.json    # GoEmotions con emociones mapeadas (28 → 9)
│   └── labeled.json              # Con etiquetas de urgencia y nivel
│
├── final/                        # Artefactos finales para entrenamiento/evaluación
│   ├── dataset.json              # Dataset consolidado y limpio
│   ├── train.json                # Split de entrenamiento
│   ├── val.json                  # Split de validación
│   ├── test.json                 # Split de prueba
│   ├── dataset_card.json         # Metadatos: fuentes, mapeos, versionado
│   └── quality_report.json       # Métricas de balance y consistencia de etiquetas
│
├── artifacts/                    # vocab.json, embedding_init.pt (gitignored por defecto)
├── checkpoints/                  # best.pt por corrida (gitignored por defecto)
│
├── scripts/                      # Scripts de procesamiento
│   ├── download_goemotions.py
│   ├── map_emotions.py
│   ├── extract_so.py
│   ├── label_with_copilot.py
│   ├── build_final_dataset.py    # Fusiona SO+GoE, meta ~4k–6k, split
│   ├── split_dataset.py          # Split reproducible (también llamado por build_final_dataset)
│   ├── build_vocab.py            # Vocab + matriz FastText
│   ├── textcnn_model.py
│   ├── training_labels.py
│   ├── train_textcnn.py
│   ├── export_onnx.py
│   └── backup/
│
└── README.md                     # Este archivo
```

## Scripts

### 1. Descargar GoEmotions ES

```bash
cd /home/carloscc/Documentos/Dev/synapse
python dataset/scripts/download_goemotions.py
```

**Dependencias:**

```bash
pip install datasets pandas
```

**Salida:**

- `dataset/raw/goemotions_es.csv`
- `dataset/raw/goemotions_es.json`

**Dataset fuente:** [AnasAlokla/multilingual_go_emotions](https://huggingface.co/datasets/AnasAlokla/multilingual_go_emotions)

- 54,263 ejemplos en español
- 28 emociones multi-label
- Licencia: Apache 2.0

### 2. Mapear Emociones

```bash
python dataset/scripts/map_emotions.py
```

**Dependencias:**

```bash
pip install pandas
```

**Salida:**

- `dataset/processed/goemotions_mapped.json`

**Mapeo de emociones:**


| GoEmotions (28)                                                         | Synapse (9) |
| ----------------------------------------------------------------------- | ----------- |
| anger, annoyance, disapproval                                           | frustracion |
| confusion                                                               | confusion   |
| curiosity, interest, desire                                             | curiosidad  |
| nervousness, fear                                                       | ansiedad    |
| admiration, approval, excitement, joy, love, optimism, pride, gratitude | motivacion  |
| surprise, realization                                                   | abrumado    |
| sadness, disappointment, grief, remorse, embarrassment                  | desesperado |
| neutral, caring                                                         | neutral     |


### 3. Extraer Preguntas de Stack Overflow ES

```bash
python dataset/scripts/extract_so.py
```

**Dependencias:**

```bash
pip install requests
```

**Salida:**

- `dataset/raw/so_questions.json`

### 4. Etiquetar con Copilot

```bash
python dataset/scripts/label_with_copilot.py --list-models
python dataset/scripts/label_with_copilot.py --max-examples 250
```

**Dependencias:**

```bash
pip install openai
```

**Modelos usados:**

- Configurables por CLI (`--models`)
- Defaults del script: `gpt-5-mini,gpt-4.1,gpt-4o`
- IDs reales se validan contra `GET /v1/models` del proxy
- Si un modelo requiere otro endpoint, usar `--model-route-overrides` con JSON `modelo -> base_url`

**Notas operativas:**

- Iniciar proxy: `npx copilot-api@latest start --port 4141`
- El script reanuda automáticamente si existe `dataset/processed/labeled.json`

**Salida:**

- `dataset/processed/labeled.json`

### 5. Dataset final fusionado (~4k–6k)

Fusiona Stack Overflow etiquetado + GoEmotions mapeado, deduplica por texto, equilibra por `emocion` hacia una meta de filas (por defecto 5000) y escribe `dataset/final/dataset.json` más `quality_report.json`. Por defecto **también ejecuta el split** 70/15/15 (omitir con `--no-split`).

```bash
pip install scikit-learn
python dataset/scripts/build_final_dataset.py --target-rows 5000 --seed 42
```

Opciones útiles: `--min-per-emotion 200`, `--no-augment-so` (desactiva frases de relleno SO si no las queréis), `--no-split`.

**Salida:** `dataset/final/dataset.json`, `quality_report.json`, y salvo `--no-split`: `train.json`, `val.json`, `test.json`, `split_meta.json`.

### 6. Split train / val / test (solo `dataset.json`)

Si ya tenéis `dataset/final/dataset.json` sin split (p. ej. generado con `--no-split`):

```bash
pip install scikit-learn
python dataset/scripts/split_dataset.py --input dataset/final/dataset.json
```

Salida: `dataset/final/train.json`, `val.json`, `test.json`, `split_meta.json`.

### 7. Vocabulario y matriz FastText

Descarga vectores `.vec` (ej. [FastText Spanish CC](https://fasttext.cc/docs/en/crawl-vectors.html)).

```bash
pip install torch
python dataset/scripts/build_vocab.py \
  --train dataset/final/train.json \
  --fasttext /ruta/cc.es.300.vec \
  --out-dir dataset/artifacts
```

### 8. Entrenar TextCNN (PyTorch)

```bash
pip install torch scikit-learn numpy
python dataset/scripts/train_textcnn.py \
  --train dataset/final/train.json \
  --val dataset/final/val.json \
  --vocab dataset/artifacts/vocab.json \
  --embedding dataset/artifacts/embedding_init.pt \
  --out-dir dataset/checkpoints/mi_corrida
```

Detalle de hiperparámetros y pérdida: [`docs/03-data-and-state/fine-tuning-process.md`](../docs/03-data-and-state/fine-tuning-process.md).

### 9. Exportar ONNX

```bash
python dataset/scripts/export_onnx.py \
  --checkpoint dataset/checkpoints/mi_corrida/best.pt \
  --out synapse_textcnn.onnx
```

### 10. Augmentation SO

El script `build_final_dataset.py` puede añadir frases cortas de contexto SO (sin cambiar etiquetas) cuando el conteo total sigue por debajo de `--target-rows`. Para desactivar: `--no-augment-so`.

## Formato del Dataset Final

```json
{
  "texto": "No entiendo nada de recursividad, llevo horas intentándolo",
  "nivel_tecnico": "principiante",
  "urgencia": "alta",
  "emocion": "frustracion",
  "dominio": "algoritmos",
  "fuente": "so_es",
  "emocion_original_goemotions": "annoyance"
}
```

## Fuentes

- **GoEmotions Multilingual**: [AnasAlokla/multilingual_go_emotions](https://huggingface.co/datasets/AnasAlokla/multilingual_go_emotions)
- **Stack Overflow ES API**: [Stack Exchange API](https://api.stackexchange.com/2.3/questions?site=es.stackoverflow)
- **Copilot API Proxy**: [ericc-ch/copilot-api](https://github.com/ericc-ch/copilot-api)

## Licencias

- GoEmotions Multilingual: Apache 2.0
- Stack Overflow: CC BY-SA 4.0
- Copilot: términos y políticas de GitHub Copilot

