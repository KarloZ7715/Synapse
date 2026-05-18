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

## Deploy en Cloudflare Pages

Configuracion recomendada:

- Root directory: `frontend`
- Build command: `pnpm install --frozen-lockfile && pnpm sync:model && pnpm build`
- Build output directory: `dist`
- Variable de entorno: `VITE_API_BASE_URL=https://<tu-servicio-render>.onrender.com`
- Variable opcional: `VITE_ONNX_MODEL_URL=https://<tu-servicio-render>.onrender.com/assets/models/synapse_textcnn.onnx`

Notas:

- El repo ya incluye `frontend/.node-version` con Node 22.
- `pnpm sync:model` es obligatorio en el build porque copia el ONNX y el vocabulario desde `neural_network/notebook/data/` a `public/models/`.
- Si despliegas por subida directa a Pages y el `.onnx` supera el límite por archivo, define `VITE_ONNX_MODEL_URL`; el postbuild eliminará `dist/models/synapse_textcnn.onnx` y la app cargará el modelo desde esa URL externa.
- Los headers de seguridad para Pages viven en `frontend/public/_headers`.


