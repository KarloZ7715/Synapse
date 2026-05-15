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
├── scripts/                      # Scripts de procesamiento
│   ├── download_goemotions.py    # Descarga GoEmotions ES
│   ├── map_emotions.py           # Mapeo de emociones (28 → 9)
│   ├── extract_so.py             # Extracción de Stack Overflow ES
│   ├── label_with_copilot.py     # Etiquetado con Copilot
│   └── backup/                   # Scripts operativos de respaldo
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

### 5. Data Augmentation (En desarrollo)

La fase de augmentation está planificada en `docs/06-roadmap/roadmap.md` y todavía no tiene script operativo definitivo en este repositorio.

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

