# Synapse — Documentación del Proyecto

Sistema híbrido de tutoría de programación que combina una Red Neuronal clasificadora (ONNX + WebGPU en navegador) con un LLM generativo (Groq + Gemma 4) para ofrecer respuestas personalizadas según nivel técnico, urgencia y emoción del estudiante.

## Estructura de Documentación

| Carpeta              | Contenido                     | Descripción                          |
| -------------------- | ----------------------------- | ------------------------------------ |
| `01-product/`        | Discovery, requisitos, UX     | Qué se construye y por qué           |
| `02-architecture/`   | Overview, ADRs, API contracts | Cómo se construye técnicamente       |
| `03-data-and-state/` | Modelo de datos, estado       | Qué datos fluyen y cómo se gestionan |
| `04-security/`       | Modelo de seguridad           | API keys, CORS, CSP, secretos        |
| `05-project-config/` | Estructura de carpetas        | Organización del monorepo            |
| `06-roadmap/`        | Milestones y entregables      | Plan de implementación               |

## Stack Tecnológico

| Capa            | Tecnología                                   |
| --------------- | -------------------------------------------- |
| Frontend        | Vite + SolidJS + TypeScript (SPA)            |
| UI              | SolidUI + Ark UI + Kobalte + Tailwind CSS v4 |
| ML Browser      | ONNX Runtime Web + WebGPU (Web Worker)       |
| Backend         | FastAPI + Python 3.12 + Pydantic AI          |
| LLM Principal   | Groq (Llama 3.1 8B Instant)                  |
| LLM Fallback    | Google Gemini (Gemma 4 26B A4B)              |
| Deploy Frontend | Cloudflare Pages                             |
| Deploy Backend  | Render                                       |
| CI/CD           | GitHub Actions                               |
| Testing         | Vitest + Playwright + Storybook              |
| Linting         | Biome + lefthook                             |

**Autores:** Carlos Alberto Canabal Cordero, Sebastián José Leal Flórez

**Universidad de Córdoba — Materia: Simulación**
