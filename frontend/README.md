# Synapse — Frontend

SPA **SolidJS + Vite** con clasificación local vía **Web Worker** y **ONNX Runtime Web**.

## Requisitos

- Node **>= 22**
- **pnpm** 9.x

## Artefactos del modelo

Antes de `pnpm dev` o tests E2E que ejecuten inferencia real:

```bash
cd frontend
pnpm install
pnpm sync:model
```

Esto copia `synapse_textcnn.onnx` y `vocab.json` desde `neural_network/notebook/data/...` a `public/models/`.

> Los binarios grandes no se versionan por defecto (ver `.gitignore`). En CI, ejecuta `pnpm sync:model` antes del build.

## Scripts


| Comando          | Descripción                                             |
| ---------------- | ------------------------------------------------------- |
| `pnpm dev`       | Servidor de desarrollo (Vite)                           |
| `pnpm build`     | Build de producción                                     |
| `pnpm test:unit` | Vitest (unit + componentes)                             |
| `pnpm test:e2e`  | Playwright (requiere `sync:model` para inferencia real) |
| `pnpm lint`      | Biome                                                   |
| `pnpm typecheck` | `tsc --noEmit`                                          |


