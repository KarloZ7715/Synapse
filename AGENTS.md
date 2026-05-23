# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Synapse is an AI programming tutor for Spanish-speaking students. It has two main services:

| Service | Directory | Start command | Port |
|---------|-----------|---------------|------|
| Frontend (SolidJS + Vite) | `frontend/` | `pnpm dev` | 5173 |
| Backend (FastAPI) | `backend/` | `uvicorn main:app --host 0.0.0.0 --port 8000` | 8000 |

The frontend runs an ONNX classifier locally in the browser via Web Worker. The backend proxies enriched prompts to Groq LLM via SSE streaming.

### Key commands

See `frontend/README.md` for the full script table. Quick reference:

- **Lint**: `cd frontend && pnpm lint` (Biome)
- **Typecheck**: `cd frontend && pnpm typecheck` (tsc --noEmit)
- **Unit tests**: `cd frontend && pnpm test:unit` (Vitest)
- **E2E tests**: `cd frontend && pnpm test:e2e` (Playwright — requires `pnpm sync:model` first)
- **Backend**: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`

### Important caveats

1. **ONNX model sync**: Before running the frontend dev server or E2E tests, run `cd frontend && pnpm sync:model`. This copies the trained model (`synapse_textcnn.onnx`) and vocabulary from `neural_network/notebook/data/` to `frontend/public/models/`. Without this, the local classifier won't work.

2. **Backend static assets**: The backend serves the ONNX model from `backend/static/models/`. If this directory doesn't exist, create it and copy the model: `mkdir -p backend/static/models && cp neural_network/notebook/data/checkpoints/textcnn_run/synapse_textcnn.onnx backend/static/models/`.

3. **PATH for uvicorn**: The `uvicorn` binary installs to `~/.local/bin`. Ensure this is on PATH: `export PATH="$HOME/.local/bin:$PATH"`.

4. **GROQ_API_KEY**: The backend requires a valid Groq API key for LLM responses. Without it, the `/health` endpoint reports "degraded" and `/api/chat` returns a streaming error. The `.env.example` in `backend/` has a placeholder — replace with a real key in `backend/.env`.

5. **Pre-existing lint/typecheck issues**: The codebase has minor Biome formatting issues (import ordering, trailing newlines) and one TypeScript `exactOptionalPropertyTypes` error in `src/hooks/useClassifier.ts`. These are pre-existing and do not affect runtime behavior.

6. **No database**: The system is fully stateless — no database setup required.
