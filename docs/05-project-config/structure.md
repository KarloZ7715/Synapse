# Configuración del Proyecto — Estructura

## Estructura del Monorepo

```
synapse/
├── README.md
├── docs/                          # Documentación del proyecto
│   ├── README.md
│   ├── 01-product/
│   ├── 02-architecture/
│   ├── 03-data-and-state/
│   ├── 04-security/
│   ├── 05-project-config/
│   └── 06-roadmap/
│
├── frontend/                      # SPA SolidJS
│   ├── index.html
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── biome.json
│   ├── lefthook.yml
│   ├── .env.example
│   ├── public/
│   │   ├── favicon.ico
│   │   ├── robots.txt
│   │   └── _headers              # Cloudflare Pages security headers
│   ├── src/
│   │   ├── main.tsx              # Entry point
│   │   ├── App.tsx               # Root component
│   │   ├── index.css             # Tailwind imports
│   │   ├── components/
│   │   │   ├── ui/               # SolidUI components
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── MetadataPanel.tsx
│   │   │   └── ThemeToggle.tsx
│   │   ├── workers/
│   │   │   └── classifier.worker.ts  # ONNX Runtime Web Worker
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   ├── useClassifier.ts
│   │   │   └── useTheme.ts
│   │   ├── store/
│   │   │   └── conversation.ts   # Estado global (createStore)
│   │   ├── types/
│   │   │   └── index.ts          # Tipos compartidos
│   │   ├── utils/
│   │   │   ├── api.ts            # Fetch wrapper + SSE
│   │   │   └── tokenizer.ts      # Preprocesamiento para ONNX
│   │   └── models/
│   │       └── synapse-textcnn.onnx   # Modelo ONNX
│   └── tests/
│       ├── unit/
│       ├── e2e/
│       └── components/
│
├── backend/                       # FastAPI Python
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── render.yaml                # Config de deploy en Render
│   ├── .env.example
│   ├── main.py                    # Entry point: app = FastAPI()
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings desde .env
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # POST /api/chat
│   │   │   └── health.py          # GET /health
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_gateway.py     # Pydantic AI agent
│   │   │   ├── circuit_breaker.py # Circuit breaker pattern
│   │   │   └── cache.py           # LRU cache en memoria
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py         # Pydantic models
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── rate_limit.py
│   │       └── cors.py
│   └── tests/
│       └── test_chat.py
│
├── dataset/                       # Pipeline de datos (raw → final, splits)
│   ├── final/                     # train.json, val.json, test.json
│   ├── processed/
│   ├── scripts/                   # Solo pipeline de dataset
│   └── README.md
│
├── neural_network/                # TextCNN Synapse: única copia del código de la RN
│   ├── notebook/                  # Cuaderno Colab; en Colab real los JSON suelen ir en /content/data
│   │   ├── synapse_textcnn_training.ipynb
│   │   └── data/                  # JSON del split para Colab
│   └── scripts/
│       ├── build_vocab.py
│       ├── train_textcnn.py
│       ├── textcnn_model.py
│       ├── training_labels.py
│       └── export_onnx.py
│
└── .github/
    └── workflows/
        ├── ci.yml                 # Biome + Vitest + Playwright + Lighthouse
        └── deploy.yml             # Auto-deploy a Cloudflare Pages + Render
```

## Dataset y modelo TextCNN

- `**dataset/**`: ingesta, procesamiento, fusión y splits (`final/train.json`, etc.). Los scripts bajo `dataset/scripts/` son el pipeline de datos.
- `**neural_network/**`: implementación única de **SynapseTextCNN** — `scripts/` (vocabulario FastText, entrenamiento, ONNX, etiquetas) y `notebook/` (`synapse_textcnn_training.ipynb`: flujo Colab/repo con **salida en streaming** de `build_vocab` y `train_textcnn`). En **Google Colab** el explorador suele mostrar solo `/content`: allí se colocan `scripts/` y `data/`.

## Configuraciones Clave

### TypeScript (frontend/tsconfig.json)

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "exactOptionalPropertyTypes": true,
    "jsx": "preserve",
    "jsxImportSource": "solid-js",
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler"
  }
}
```

### Biome (frontend/biome.json)

```json
{
  "formatter": { "indentStyle": "space", "lineWidth": 100 },
  "linter": {
    "rules": {
      "correctness": { "all": true },
      "security": { "all": true },
      "style": { "all": true }
    }
  }
}
```

### lefthook (frontend/lefthook.yml)

```yaml
pre-commit:
  commands:
    biome:
      run: pnpm biome check --write {staged_files}
    type-check:
      run: pnpm tsc --noEmit
pre-push:
  commands:
    test:
      run: pnpm vitest run --coverage
```

### pnpm (frontend/package.json)

```json
{
  "packageManager": "pnpm@9.0.0",
  "engines": { "node": ">=22" },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:e2e": "playwright test",
    "lint": "biome check",
    "format": "biome format --write",
    "storybook": "storybook dev"
  }
}
```

### Render (backend/render.yaml)

```yaml
services:
  - type: web
    name: synapse-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: FRONTEND_ORIGIN
        value: https://synapse.pages.dev
```

## Comandos de Inicio

```bash
# Frontend
cd frontend
pnpm install
pnpm dev              # http://localhost:5173

# Dataset (entrenamiento TextCNN desde la raíz del repo)
python neural_network/scripts/train_textcnn.py --help

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload  # http://localhost:8000
```
