# ADR-001: SolidJS SPA con Vite (sin SSR)

## Contexto

Necesitamos elegir el framework y estrategia de renderizado para el frontend del tutor de programación. La aplicación requiere:

- Integración con ONNX Runtime Web + WebGPU para inferencia de red neuronal local
- Ejecución de modelos ML en Web Workers sin bloquear la UI
- Renderizado eficiente de streaming de tokens desde el backend
- Bundle size mínimo para carga rápida del modelo ONNX (~30-50MB)
- UI con componentes accesibles y personalizables (shadcn-style)

## Decisión

Usaremos **SolidJS v1.9 como SPA con Vite**, sin Server-Side Rendering (SSR).

## Justificación

1. **Rendimiento superior con WebGPU:** SolidJS compila JSX a operaciones directas del DOM sin Virtual DOM. Con un bundle de ~7.6KB gzipped, deja más recursos disponibles para ONNX Runtime Web y WebGPU. Benchmarks de 2026 muestran que SolidJS compite con vanilla JS en velocidad.
2. **SSR innecesario:** Nuestra aplicación es 100% interactiva (chat + clasificador ML). No tiene contenido indexable por SEO. No hay páginas estáticas que beneficiarían de SSR. La carga inicial es secundaria frente a la performance de inferencia.
3. **Signals para streaming:** La reactividad de grano fino de SolidJS (signals) es ideal para actualizar el DOM token por token durante el streaming SSE sin re-renderizar componentes enteros.
4. **Ecosistema compatible:** SolidUI (port de shadcn), Ark UI (headless, Zag.js), Kobalte — todos compatibles con SolidJS y con soporte para Tailwind CSS v4.
5. **SolidStart descartado:** SolidStart v2.0 está en alpha. Para un proyecto académico, la estabilidad de SolidJS vanilla + Vite es preferible. No necesitamos file-based routing complejo ni API routes (eso lo maneja FastAPI).

## Alternativas Consideradas


| Alternativa        | Rechazada porque                                                                  |
| ------------------ | --------------------------------------------------------------------------------- |
| React + Next.js    | Virtual DOM overhead compite con WebGPU. Bundle 45KB+. SSR innecesario            |
| Svelte + SvelteKit | Excelente opción, pero menor ecosistema headless UI. SolidJS supera en benchmarks |
| Vue + Nuxt         | Virtual DOM (aunque optimizado). Ecosistema UI no tan headless-first              |
| Astro              | Excelente para contenido estático, no para SPAs interactivas con ML               |


## Consecuencias

- **Positivas:** Máximo rendimiento para ONNX/WebGPU. Código cercano a vanilla JS. Signals ideales para streaming.
- **Negativas:** Ecosistema más pequeño que React. Menos tutoriales y recursos. Curva de aprendizaje para reactivity model.
- **Mitigación:** SolidJS tiene sintaxis similar a React. La documentación oficial cubre todos los casos de uso necesarios.

