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
│   ├── extraction_audit.json     # Conteos post-extracción SO (extract_so)
│   └── backups/                  # Respaldos operativos de extracción
│
├── processed/                    # Datos procesados
│   ├── labeling_audit/          # Fallos de parseo/validación Copilot (jsonl)
│   ├── backups/                  # Snapshots de control de calidad fase 3
│   ├── goemotions_mapped.json    # GoEmotions con emociones mapeadas (28 → 10 Synapse)
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
├── scripts/                      # Pipeline de datos
│   ├── download_goemotions.py
│   ├── map_emotions.py
│   ├── extract_so.py
│   ├── label_with_copilot.py
│   ├── build_final_dataset.py    # Fusiona SO+GoE, meta ~12k, split
│   ├── split_dataset.py          # Split reproducible
│   └── backup/
│
├── README.md                     # Este archivo
│
└── neural_network/                 # TextCNN + cuaderno Colab
    ├── notebook/
    │   ├── synapse_textcnn_training.ipynb
    │   └── data/                     # train/val/test en el repo; en Colab suelen copiarse a /content/data
    └── scripts/
        ├── build_vocab.py
        ├── train_textcnn.py
        ├── textcnn_model.py
        ├── training_labels.py
        └── export_onnx.py
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

| GoEmotions (28)                                        | Synapse (10) |
| ------------------------------------------------------ | ------------ |
| anger, annoyance, disapproval                          | frustracion  |
| confusion                                              | confusion    |
| curiosity, interest, desire                            | curiosidad   |
| nervousness, fear                                      | ansiedad     |
| admiration, excitement, joy, love, optimism, gratitude | motivacion   |
| approval, pride                                        | confiado     |
| surprise, realization                                  | abrumado     |
| sadness, disappointment, grief, remorse, embarrassment | desesperado  |
| neutral, caring                                        | neutral      |

### 3. Extraer Preguntas de Stack Overflow ES

```bash
python dataset/scripts/extract_so.py
```

Selección **quota-aware**: por defecto **sembrado** desde `so_questions.json` ya existente (`--seed-existing`, activo salvo `--no-seed-existing`) para no perder SO ya curado; luego la API amplía el pool. Pisos por `domain_synapse` (`DEFAULT_DOMAIN_MIN_QUOTA`), relleno hasta `--max-questions` (por defecto **1600**) con diversidad por urgencia/avanzado. Presupuesto API por defecto `--max-api-calls 960`, `--max-tags-per-domain 5`, `--max-pages-per-tag 4`. Opcional: `--domain-min-json path.json`.

**Dependencias:**

```bash
pip install requests
```

**Cuota API:** sin `STACKEXCHANGE_KEY` la API de Stack Exchange limita fuerte (429). Exporta `STACKEXCHANGE_KEY` (clave en [stackapps](https://stackapps.com/)) antes de extracciones grandes (`--max-questions` alto).

**Salida:**

- `dataset/raw/so_questions.json`

**Rebalanceo agresivo (extracción):** `python dataset/scripts/extract_so.py --rebalance-profile aggressive` — pisos mayores en dominios débiles, más términos advanced y búsqueda “baja urgencia”. Suele requerir subir `--max-api-calls` (p. ej. 1200). Ver `dataset/raw/extraction_audit.json` (`rebalance_profile`).

### 4. Etiquetar con Copilot

```bash
python dataset/scripts/label_with_copilot.py --list-models
python dataset/scripts/label_with_copilot.py
# Opcional: misma llamada con emoción Synapse (recomendado para filas nuevas)
python dataset/scripts/label_with_copilot.py --label-emotion
# Opcional: solo rellenar emocion en filas ya etiquetadas (moderado)
python dataset/scripts/label_with_copilot.py --emotion-backfill-only --max-examples 600
# Opcional: calibración dirigida de colas (tras una corrida completa)
python dataset/scripts/label_with_copilot.py --calibration-pass --target-min-avanzado 120 --target-min-alta 140 --target-min-baja 160
```

**Dependencias:**

```bash
pip install openai
```

Orden de regeneración y gates: `[docs/03-data-and-state/dataset-plan.md](../docs/03-data-and-state/dataset-plan.md)` §3.0 y §1bis.

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

Fusiona Stack Overflow etiquetado + GoEmotions mapeado, deduplica por texto, equilibra por `emocion` hacia una meta de filas (por defecto 5000) y escribe `dataset/final/dataset.json` más `quality_report.json` (incluye `**dataset_gates`**, `**rebalance_strict_gates**`, `**split_aware_counts**`y`**so_emocion_labeling**`) y `dataset_quality_gates.json`. Por defecto **también ejecuta el split\*\* 70/15/15 (omitir con `--no-split`).

```bash
pip install scikit-learn
python dataset/scripts/build_final_dataset.py --target-rows 5000 --seed 42
```

Opciones útiles: `--min-per-emotion 200`, `--no-augment-so` (no duplicar SO con sufijos para rellenar hasta `--target-rows`), `--strict-rebalance-gates` (dataset + colas SO; **exit code 1** si falla), `--no-split`.

**Salida:** `dataset/final/dataset.json`, `quality_report.json`, `dataset_quality_gates.json`, y salvo `--no-split`: `train.json`, `val.json`, `test.json`, `split_meta.json`.

### 6. Split train / val / test (solo `dataset.json`)

Si ya tenéis `dataset/final/dataset.json` sin split (p. ej. generado con `--no-split`):

```bash
pip install scikit-learn
python dataset/scripts/split_dataset.py --input dataset/final/dataset.json
```

Salida: `dataset/final/train.json`, `val.json`, `test.json`, `split_meta.json`.

### 7. Vocabulario y matriz FastText

Descarga vectores `.vec` (ej. [FastText Spanish CC](https://fasttext.cc/docs/en/crawl-vectors.html)).

`build_vocab.py` hace **una pasada en streaming** por el `.vec`: solo materializa vectores para tokens del vocabulario (memoria O(|vocab|)), sin cargar el fichero completo en RAM.

```bash
pip install torch
python neural_network/scripts/build_vocab.py \
  --train dataset/final/train.json \
  --fasttext /ruta/cc.es.300.vec \
  --out-dir dataset/artifacts \
  --seed 42
```

### 8. Entrenar TextCNN (PyTorch)

```bash
pip install torch scikit-learn numpy
python neural_network/scripts/train_textcnn.py \
  --train dataset/final/train.json \
  --val dataset/final/val.json \
  --test dataset/final/test.json \
  --vocab dataset/artifacts/vocab.json \
  --embedding dataset/artifacts/embedding_init.pt \
  --out-dir dataset/checkpoints/mi_corrida \
  --seed 42
```

Salidas típicas bajo `--out-dir`: `best.pt`, `best_metrics.json`, `run_config.json`, `history.json`, `test_metrics.json`, `dod_report.json`, `majority_baselines.json`, `val_head_detail.json`. Durante el entrenamiento, la consola muestra por época pérdidas, accuracy media (cuatro cabezas) en train/val, `f1_macro_mean` en val y F1 por cabeza.

**Pesos por cabeza:** por defecto `train_textcnn.py` usa **pesos balanceados** (`--class-weights` activo); `**--no-class-weights`\*\* solo para un baseline de comparación.

### 9. Exportar ONNX

```bash
python neural_network/scripts/export_onnx.py \
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
  "emocion_source_so": "heuristic",
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
