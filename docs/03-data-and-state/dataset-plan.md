# Dataset — Plan de Generación Híbrida

## 1. Decisión: Opción 1 — GoEmotions ES + Stack Overflow API + LLM

Estrategia híbrida que combina un dataset real de emociones en español con preguntas reales de programación y generación asistida por LLM para las dimensiones faltantes.

```mermaid
graph LR
    A[GoEmotions ES<br/>54,263 filas, 28 emociones] --> D[Dataset Final<br/>~5000 ejemplos]
    B[Stack Overflow ES API<br/>Preguntas reales + tags] --> D
    C[Copilot Models<br/>via copilot-api proxy] --> D

    style A fill:#1c1c22,stroke:#22d3ee,color:#ededef
    style B fill:#1c1c22,stroke:#34d399,color:#ededef
    style C fill:#1c1c22,stroke:#c084fc,color:#ededef
    style D fill:#1c1c22,stroke:#fbbf24,color:#ededef,stroke-width:2px
```



## 2. Fuentes de Datos

### 2.1 GoEmotions ES (Emociones)


| Propiedad | Valor                                               |
| --------- | --------------------------------------------------- |
| Dataset   | `AnasAlokla/multilingual_go_emotions` (HuggingFace) |
| Filas ES  | 54,263                                              |
| Emociones | 28 clases (multi-label)                             |
| Idioma    | Español (filtrado por language="sp")                |
| Metadata  | text, labels (IDs), id, language                    |
| Licencia  | Apache 2.0                                          |


**Mapeo de emociones (28 → 9):**


| Emociones GoEmotions ES                                                 | Emoción Synapse |
| ----------------------------------------------------------------------- | --------------- |
| anger, annoyance, disapproval                                           | `frustracion`   |
| confusion (derivable de curiosity + sadness)                            | `confusion`     |
| curiosity, interest                                                     | `curiosidad`    |
| nervousness, fear, anxiety                                              | `ansiedad`      |
| admiration, approval, excitement, joy, love, optimism, pride, gratitude | `motivacion`    |
| realization, surprise (negativo)                                        | `abrumado`      |
| approval, pride (positivo)                                              | `confiado`      |
| sadness, disappointment, grief, remorse                                 | `desesperado`   |
| neutral, caring                                                         | `neutral`       |


### 2.2 Stack Overflow ES API (Preguntas Reales)


| Propiedad       | Valor                                                                           |
| --------------- | ------------------------------------------------------------------------------- |
| API             | `api.stackexchange.com/2.3/questions?site=es.stackoverflow`                     |
| Filtros         | tags: python, javascript, java, react, sql, css, html, node.js, typescript, git |
| Selección       | score ≥ 3 (garantiza calidad)                                                   |
| Volumen         | 200-300 preguntas semilla                                                       |
| Datos extraídos | title, body (sin respuestas), tags, score, view_count                           |


**Mapeo de tags → Dominio Synapse:**


| Tags de Stack Overflow                             | Dominio Synapse       |
| -------------------------------------------------- | --------------------- |
| python, javascript, java, go, rust, php, ruby      | `backend`             |
| react, vue, css, html, angular, svelte, nextjs     | `frontend`            |
| sql, mysql, postgresql, mongodb, redis             | `bases_de_datos`      |
| docker, kubernetes, aws, gcp, ci/cd, nginx         | `devops`              |
| android, ios, flutter, react-native, swift, kotlin | `movil`               |
| pandas, numpy, scikit-learn, tensorflow, pytorch   | `data_science`        |
| sorting, algorithms, data-structures, recursion    | `algoritmos`          |
| security, authentication, encryption, oauth        | `seguridad`           |
| os, memory, concurrency, threads, process          | `sistemas`            |
| design-patterns, testing, architecture, solid      | `ingenieria_software` |
| Otros                                              | `general`             |


### 2.3 Fuentes complementarias (emoción y afín en español)

Útiles para **aumentar cobertura emocional** y robustez fuera del estilo Reddit/GoEmotions, o para **pre-entrenar / regularizar** antes del dataset mezclado con programación. Siempre revisar licencia y **re-mapear** etiquetas al esquema Synapse (9 emociones) mediante reglas documentadas.


| Dataset                                  | Enlace                                                                                                                       | Por qué aplica                                                                   |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **GoEmotions multilingüe** (base actual) | [AnasAlokla/multilingual_go_emotions](https://huggingface.co/datasets/AnasAlokla/multilingual_go_emotions)                   | Gran volumen ES; multi-label fino → útil tras mapeo                              |
| **EmoEvent** (ES)                        | [fmplaza/EmoEvent](https://huggingface.co/datasets/fmplaza/EmoEvent) (subconjunto español; puede requerir aceptación en Hub) | Tweets en español con emociones Ekman + ofensivo/no; útil para tono informal     |
| **SemEval-2018 Task 1** (E-c, ES)        | [SemEvalWorkshop/sem_eval_2018_task_1](https://huggingface.co/datasets/SemEvalWorkshop/sem_eval_2018_task_1)                 | Emoción multi-label en tweets ES; etiquetas distintas → requiere mapeo cuidadoso |
| **Preguntas técnicas ES**                | API/site `es.stackoverflow` + dump oficial SE                                                                                | Dominio “programación en español” nativo; ya integrado en el pipeline            |


**Kaggle:** no hay un estándar único “SO español” en Kaggle; suele usarse **API/dump** (arriba) o subconjuntos de SO en inglés solo como data augmentation de *estilo* (con filtro de idioma si se mezcla).

**Sintético (LLM):** misma política que en Copilot — generar variaciones controladas y **filtrar** con ROUGE-L / revisión manual para clases minoritarias.

**Objetivo de volumen:** mínimo defendible **~2000** ejemplos curados; recomendado **4000–6000** para emociones/dominios minoritarios. **Umbral por clase rara:** apuntar a **≥100–150** ejemplos (real+aumentados); ideal **≥200**.

### 2.4 Copilot (Etiquetado de Dimensiones Faltantes)

Usamos Copilot via proxy OpenAI-compatible y rotamos modelos disponibles:


| Modelo         | Fuente  | Uso principal         |
| -------------- | ------- | --------------------- |
| **gpt-5-mini** | Copilot | Etiquetado principal  |
| **gpt-4.1**    | Copilot | Etiquetado secundario |
| **gpt-4o**     | Copilot | Respaldo de rotación  |


**Estrategia de distribución:**

- Rotación round-robin entre modelos configurados (`--models`)
- Validación dinámica de IDs contra `GET /v1/models`
- Reanudación incremental sobre `processed/labeled.json`

**Tiempo estimado:** ~1 día para el lote de 250 preguntas SO ES

## 3. Pipeline de Generación

```mermaid
graph TD
    subgraph PASO1["Paso 1: Extracción"]
        A1[Stack Overflow ES API] --> A2[200-300 preguntas semilla]
        A2 --> A3[Filtrar por tags populares<br/>score ≥ 3]
    end

    subgraph PASO2["Paso 2: Mapeo Emociones"]
        B1[GoEmotions ES<br/>54,263 filas] --> B2[Seleccionar muestras<br/>representativas]
        B2 --> B3[Mapear 28 → 9 emociones]
    end

    subgraph PASO3["Paso 3: Etiquetado LLM"]
        C1[Semillas SO ES] --> C2[Copilot etiqueta:<br/>urgencia + nivel técnico]
        C2 --> C3[Formato JSON estructurado]
    end

    subgraph PASO4["Paso 4: Augmentation"]
        D1[Dataset base ~500 ej] --> D2[NLPaug + paráfrasis LLM]
        D2 --> D3[Dataset ampliado ~2000 ej]
    end

    subgraph PASO5["Paso 5: Validación"]
        E1[Dataset ampliado] --> E2[Filtrar duplicados<br/>ROUGE-L > 0.8]
        E2 --> E3[Validar balance<br/>≥100–150 /clase minoritaria]
        E3 --> E4[Dataset final]
    end

    PASO1 --> PASO3
    PASO2 --> PASO3
    PASO3 --> PASO4
    PASO4 --> PASO5

    style PASO1 fill:#141418,stroke:#22d3ee,color:#ededef
    style PASO2 fill:#141418,stroke:#c084fc,color:#ededef
    style PASO3 fill:#141418,stroke:#fbbf24,color:#ededef
    style PASO4 fill:#141418,stroke:#34d399,color:#ededef
    style PASO5 fill:#141418,stroke:#f87171,color:#ededef
```



### Paso 1: Extracción de Semillas (Stack Overflow ES)

```python
# Ejemplo de llamada a la API
import requests

url = "https://api.stackexchange.com/2.3/questions"
params = {
    "order": "desc",
    "sort": "votes",
    "site": "es.stackoverflow",
    "pagesize": 100,
    "tagged": "python",
    "filter": "withbody"
}
response = requests.get(url, params=params)
questions = response.json()["items"]
```

### Paso 2: Mapeo de Emociones (GoEmotions ES → Synapse)

```python
# Mapeo de las 28 emociones de GoEmotions a nuestras 9
EMOTION_MAPPING = {
    # frustracion
    "anger": "frustracion",
    "annoyance": "frustracion",
    "disapproval": "frustracion",
    # confusion
    "confusion": "confusion",
    # curiosidad
    "curiosity": "curiosidad",
    "interest": "curiosidad",
    # ansiedad
    "nervousness": "ansiedad",
    "fear": "ansiedad",
    # motivacion
    "admiration": "motivacion",
    "approval": "motivacion",
    "excitement": "motivacion",
    "joy": "motivacion",
    "love": "motivacion",
    "optimism": "motivacion",
    "pride": "motivacion",
    "gratitude": "motivacion",
    "desire": "motivacion",
    # abrumado
    "surprise": "abrumado",
    "realization": "abrumado",
    # confiado
    # (se deriva de approval + pride en contexto positivo)
    # desesperado
    "sadness": "desesperado",
    "disappointment": "desesperado",
    "grief": "desesperado",
    "remorse": "desesperado",
    "embarrassment": "desesperado",
    # neutral
    "neutral": "neutral",
    "caring": "neutral",
}
```

### Paso 3: Etiquetado con LLM

```python
PROMPT_TEMPLATE = """
Eres un etiquetador de datos para un clasificador de emociones en programación.

Dada esta pregunta de programación en español:
"{texto}"

Y estas emociones candidatas: {emociones_candidatas}

Determina:
1. La emoción principal (de la lista proporcionada)
2. El nivel técnico del autor (principiante/intermedio/avanzado)
3. La urgencia de la consulta (baja/media/alta)

Responde en JSON:
{{
  "emocion": "...",
  "nivel_tecnico": "...",
  "urgencia": "...",
  "justificacion": "..."
}}
"""
```

### Paso 4: Data Augmentation

```mermaid
graph LR
    A[Dataset base<br/>~500 ejemplos] --> B[NLPaug<br/>Sustitución sinónimos]
    A --> C[Paráfrasis LLM<br/>Reformular sin cambiar sentido]
    A --> D[Back-translation<br/>ES → EN → ES]
    B --> E[Dataset ampliado<br/>~5000 ejemplos]
    C --> E
    D --> E

    style A fill:#1c1c22,stroke:#22d3ee,color:#ededef
    style E fill:#1c1c22,stroke:#4ade80,color:#ededef,stroke-width:2px
```



### Paso 5: Filtrado y Validación

- Eliminar duplicados (similitud ROUGE-L > 0.8)
- Validar clases minoritarias: **≥100–150** ejemplos (ideal **≥200**); ampliar dataset hacia **4k–6k** ejemplos cuando sea posible

## 4. Distribución de Clases Objetivo


| Dimensión     | Etiquetas                              | Ejemplos por clase | Total |
| ------------- | -------------------------------------- | ------------------ | ----- |
| Nivel técnico | 3 (principiante, intermedio, avanzado) | ~667               | 5000  |
| Urgencia      | 3 (baja, media, alta)                  | ~667               | 5000  |
| Emoción       | 9                                      | ~222               | 5000  |
| Dominio       | 11                                     | ~182               | 5000  |


## 5. Formato del Dataset

```json
[
  {
    "texto": "No entiendo nada de recursividad, llevo horas intentándolo",
    "nivel_tecnico": "principiante",
    "urgencia": "alta",
    "emocion": "frustracion",
    "dominio": "algoritmos",
    "fuente": "so_es",
    "emocion_original_goemotions": "annoyance"
  },
  {
    "texto": "¿Cómo funciona el event loop de JavaScript a nivel interno?",
    "nivel_tecnico": "avanzado",
    "urgencia": "baja",
    "emocion": "curiosidad",
    "dominio": "frontend",
    "fuente": "so_es",
    "emocion_original_goemotions": "curiosity"
  }
]
```

## 6. Herramientas


| Herramienta                  | Uso                             | Fuente                                                                             |
| ---------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| Stack Exchange API           | Extraer preguntas semilla       | `api.stackexchange.com`                                                            |
| GoEmotions ES (AnasAlokla)   | Dataset de emociones en español | [HuggingFace](https://huggingface.co/datasets/AnasAlokla/multilingual_go_emotions) |
| GitHub Copilot + copilot-api | Etiquetado (urgencia + nivel)   | `npx copilot-api@latest start --port 4141`                                         |
| NLPaug                       | Data augmentation               | `pip install nlpaug`                                                               |
| ROUGE-L                      | Filtrado de duplicados          | `pip install rouge-score`                                                          |
| Python + pandas              | Procesamiento y limpieza        | -                                                                                  |


## 7. Entregables

```
dataset/
├── raw/
│   ├── so_questions.json          # Preguntas originales de SO ES
│   ├── goemotions_es.csv          # GoEmotions ES completo
│   └── goemotions_es.json         # GoEmotions ES en JSON
├── processed/
│   ├── goemotions_mapped.json     # Mapeo GoEmotions 28 -> 9
│   └── labeled.json               # Con etiquetas del LLM
├── final/
│   ├── dataset.json               # Dataset final entrenable (F4: build_final_dataset)
│   ├── quality_report.json        # Conteos por dimensión y fuente
│   ├── train.json                 # 70% entrenamiento
│   ├── val.json                   # 15% validación
│   ├── test.json                  # 15% prueba
│   └── split_meta.json            # Metadatos del split
├── artifacts/                     # Generado: vocab.json, embedding_init.pt
├── checkpoints/                   # Generado: best.pt por corrida de entrenamiento
├── scripts/
│   ├── download_goemotions.py
│   ├── map_emotions.py
│   ├── extract_so.py
│   ├── label_with_copilot.py
│   ├── build_final_dataset.py    # Fusiona SO+GoE, meta ~4k–6k, dedup, split
│   ├── split_dataset.py           # Train/val/test reproducible (también desde build_final_dataset)
│   ├── build_vocab.py              # Vocab + matriz FastText
│   ├── textcnn_model.py           # Definición SynapseTextCNN
│   ├── training_labels.py         # Orden de clases por cabeza
│   ├── train_textcnn.py         # Entrenamiento PyTorch
│   ├── export_onnx.py            # Export ONNX
│   └── backup/
└── README.md
```

## 8. Cronograma


| Día | Tarea                                               | Entregable                                                     |
| --- | --------------------------------------------------- | -------------------------------------------------------------- |
| 1   | Extraer preguntas SO ES + descargar GoEmotions ES   | `raw/`                                                         |
| 1   | Mapear emociones GoEmotions → Synapse               | `processed/goemotions_mapped.json`                             |
| 2   | Etiquetar con LLM (urgencia + nivel)                | `processed/labeled.json`                                       |
| 2-3 | Fusionar y escalar (~4k–6k), dedup, balance emoción | `final/dataset.json`, `quality_report.json`                    |
| 3   | Split reproducible (integrado o `split_dataset.py`) | `final/train.json`, `val.json`, `test.json`, `split_meta.json` |


**Tiempo total: 3 días** (dentro de las 2 semanas)

## 9. Justificación Académica

### Por qué esta estrategia

1. **GoEmotions Multilingual** es un dataset académico validado (Google Research, 2020) con traducciones a múltiples idiomas incluyendo español
2. **Stack Overflow ES** proporciona preguntas de programación reales en español
3. **Etiquetado con LLM** es una práctica validada por el paper *"Synthetic Data Generation with LLMs for Text Classification"* (arXiv:2310.07849)
4. **Data augmentation** con NLPaug está respaldado por múltiples papers de NLP

### Ventajas sobre 100% sintético

- Emociones de un dataset real, no inventadas
- Preguntas de programación reales de desarrolladores hispanohablantes
- Más defensible en la sustentación académica
- Mejor generalización del modelo

### Referencias

- GoEmotions: *"A Dataset for Fine-Grained Emotion Classification"* (Demszky et al., 2020)
- GoEmotions Multilingual: [AnasAlokla/multilingual_go_emotions](https://huggingface.co/datasets/AnasAlokla/multilingual_go_emotions)
- EmoEvent: [fmplaza/EmoEvent](https://huggingface.co/datasets/fmplaza/EmoEvent) (Plaza-del-Arco et al., LREC 2020)
- SemEval-2018 Task 1: [SemEvalWorkshop/sem_eval_2018_task_1](https://huggingface.co/datasets/SemEvalWorkshop/sem_eval_2018_task_1) (Mohammad et al., 2018)
- Stack Overflow API: Documentación oficial de Stack Exchange
- Synthetic Data: *"Synthetic Data Generation with LLMs for Text Classification"* (arXiv:2310.07849)

