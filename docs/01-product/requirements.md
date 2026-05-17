# Requisitos de Producto — Synapse

## 1. Visión

Synapse es un sistema híbrido de tutoría de programación que combina una **Red Neuronal (RN)** ejecutándose localmente en el navegador vía ONNX Runtime Web + WebGPU con un **Large Language Model (LLM)** servido desde la nube. El sistema clasifica la pregunta del usuario en 4 dimensiones (nivel técnico, urgencia, emoción, dominio) y genera una respuesta personalizada usando Groq (Llama 3.1 8B Instant) como principal y Google Gemini (Gemma 4 26B A4B) como fallback.

**Proyecto académico** desarrollado para la materia de Simulación de la Universidad de Córdoba, Colombia.

**Autores:** Carlos Alberto Canabal Cordero, Sebastián José Leal Flórez.

## 2. Requisitos Funcionales

### RF-01: Entrada de Texto del Usuario

El sistema debe permitir al usuario escribir una pregunta o duda sobre programación en lenguaje natural (español) mediante una interfaz web.

**Criterios de aceptación:**

- Campo de texto libre, sin restricciones de formato
- Soporte para tildes, eñes y caracteres especiales del español
- Longitud máxima de entrada: 2000 caracteres
- Botón de envío y soporte para Enter

### RF-02: Clasificación por Red Neuronal Local

El sistema debe analizar la pregunta del usuario usando una RN que corre en el navegador (ONNX Runtime Web + WebGPU en un Web Worker) y clasificarla en las siguientes dimensiones:

| Dimensión         | Etiquetas                                                                                                                                           | Descripción                                           |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **Nivel técnico** | `principiante`, `intermedio`, `avanzado`                                                                                                            | Nivel de conocimiento en el tema preguntado           |
| **Urgencia**      | `baja`, `media`, `alta`                                                                                                                             | Qué tan urgente es la consulta para el usuario        |
| **Emoción**       | `frustracion`, `confusion`, `curiosidad`, `ansiedad`, `motivacion`, `abrumado`, `confiado`, `desesperado`, `neutral`                                | Estado emocional detectado (taxonomía educativa)      |
| **Dominio**       | `backend`, `frontend`, `bases_de_datos`, `movil`, `devops`, `data_science`, `sistemas_seguridad`, `general` (taxonomía del **TextCNN ONNX** actual) | Área técnica colapsada para el clasificador entrenado |

> **Nota:** La tabla extendida de dominios más abajo describe una taxonomía de producto de referencia; el modelo exportado y el frontend usan solo las **8** etiquetas anteriores. Ampliación futura = reentrenamiento + actualización de contratos.

**Descripción expandida de etiquetas:**

### Emociones (taxonomía educativa para programación)

| Etiqueta      | Descripción                                         | Ejemplo de frase                                            |
| ------------- | --------------------------------------------------- | ----------------------------------------------------------- |
| `frustracion` | El código no funciona, llevo horas, no sé qué hacer | "¡Esto no compila y no tengo ni idea de por qué!"           |
| `confusion`   | No entiendo el concepto, necesito claridad          | "¿Qué diferencia hay entre async/await y promesas?"         |
| `curiosidad`  | Quiero aprender más, interés genuino                | "¿Cómo funciona realmente el event loop de JS?"             |
| `ansiedad`    | Nervios por examen/entrega, presión de tiempo       | "Mañana tengo examen de estructuras de datos, ¡ayuda!"      |
| `motivacion`  | Ganas de aprender, actitud positiva                 | "Quiero ser mejor programador, ¿por dónde empiezo con Go?"  |
| `abrumado`    | Demasiada información, no sé por dónde empezar      | "Hay tantos frameworks de frontend, ¿cuál aprendo primero?" |
| `confiado`    | Cree saber la respuesta pero busca confirmación     | "Creo que es O(n log n) pero quiero verificar..."           |
| `desesperado` | Bloqueado, no avanza, sensación de no poder         | "Llevo 3 días con este bug, ya no sé qué más intentar"      |
| `neutral`     | Sin carga emocional detectable                      | "¿Cómo se hace un JOIN en SQL?"                             |

### Dominios (referencia de producto; el modelo ONNX actual usa 8 etiquetas — ver RF-02)

| Etiqueta              | Descripción                           | Temas incluidos                                                 |
| --------------------- | ------------------------------------- | --------------------------------------------------------------- |
| `frontend`            | Desarrollo web del lado del cliente   | React, Vue, CSS, HTML, JS/TS, accesibilidad, animaciones        |
| `backend`             | Desarrollo del lado del servidor      | Node.js, Python, Java, Go, Rust, REST, GraphQL, autenticación   |
| `algoritmos`          | Algoritmos y estructuras de datos     | Sorting, searching, DP, grafos, árboles, complejidad, Big O     |
| `bases_de_datos`      | Bases de datos y almacenamiento       | SQL, NoSQL, diseño de esquemas, migraciones, optimización       |
| `devops`              | Operaciones y despliegue              | Docker, CI/CD, cloud (AWS/GCP/Azure), Linux, nginx              |
| `movil`               | Desarrollo móvil                      | Android, iOS, Flutter, React Native, Swift, Kotlin              |
| `data_science`        | Ciencia de datos y ML                 | Python, pandas, NumPy, scikit-learn, estadística, visualización |
| `seguridad`           | Ciberseguridad                        | Criptografía, OWASP, redes, ethical hacking, autenticación      |
| `sistemas`            | Sistemas operativos y bajo nivel      | Memoria, concurrencia, procesos, C, Rust, ensamblador           |
| `ingenieria_software` | Ingeniería de software                | Patrones de diseño, arquitectura limpia, testing, metodologías  |
| `general`             | No clasifica en un dominio específico | Preguntas generales sobre programación, carrera, herramientas   |

**Criterios de aceptación:**

- Inferencia <100ms (no bloquea la UI)
- Ejecución dentro de un Web Worker dedicado
- El modelo ONNX se descarga una sola vez y se cachea en el navegador

### RF-03: Generación de Metadatos Enriquecidos

La RN debe producir un objeto JSON estructurado con los metadatos de clasificación que se enviará al backend para enriquecer el prompt del LLM.

**Formato esperado:**

```json
{
  "nivel_tecnico": "principiante",
  "urgencia": "alta",
  "emocion": "frustracion",
  "dominio": "backend",
  "confianza": 0.87
}
```

### RF-04: Generación de Respuesta Personalizada por LLM

El backend debe construir un prompt enriquecido con los metadatos y enviarlo al LLM para generar una respuesta adaptada al perfil del estudiante.

**Criterios de aceptación:**

- Respuesta en español, tono adaptado a la emoción detectada
- Para nivel principiante: explicaciones desde cero, ejemplos simples, analogías
- Para nivel avanzado: explicaciones técnicas, referencias a documentación
- Para urgencia alta: respuesta directa y concisa
- Para frustración: tono empático y motivacional
- Tiempo total de respuesta <5 segundos (incluyendo clasificación + LLM)

### RF-05: Streaming de Respuesta

La respuesta del LLM debe transmitirse en tiempo real (token por token) mediante Server-Sent Events (SSE) para que el usuario vea la respuesta generándose progresivamente.

**Criterios de aceptación:**

- Primer token visible en <2 segundos
- Streaming continuo sin cortes
- Indicador visual de "escribiendo..." durante la generación

### RF-06: Fallback entre Proveedores LLM

Si Groq falla (timeout, error 429, error 5xx), el sistema debe automáticamente reintentar con Google Gemini (Gemma 4) sin intervención del usuario.

**Criterios de aceptación:**

- Circuit breaker: 3 fallos consecutivos en Groq → cambiar a Gemini por 30 segundos
- El usuario no debe notar el cambio de proveedor
- Mensaje de error genérico si ambos proveedores fallan

### RF-07: Historial de Conversación (Solo Sesión)

El sistema debe mantener el contexto de la conversación actual (máximo 5 pares pregunta-respuesta, 10 mensajes) para permitir preguntas de seguimiento.

**Criterios de aceptación:**

- Almacenado solo en memoria (no persistente)
- Se pierde al cerrar/recargar la página
- Límite de 5 pares pregunta-respuesta (ventana deslizante)

## 3. Requisitos No Funcionales

### RNF-01: Rendimiento

| Métrica                         | Objetivo     |
| ------------------------------- | ------------ |
| INP (Interaction to Next Paint) | <200ms (p75) |
| LCP (Largest Contentful Paint)  | <2.5s        |
| CLS (Cumulative Layout Shift)   | <0.1         |
| Bundle JS total (gzip)          | <400KB       |
| Tiempo de clasificación RN      | <100ms       |
| Time to First Token (LLM)       | <2s          |
| Tiempo total de respuesta       | <5s          |

### RNF-02: Disponibilidad

- Frontend: 99.9% (Cloudflare Pages)
- Backend: El servicio puede dormirse tras 15 min de inactividad (Render free tier). Mitigado con UptimeRobot.

### RNF-03: Compatibilidad

- Navegadores con soporte WebGPU: Chrome 113+, Edge 113+, Firefox Nightly
- Sin dependencia de plugins ni extensiones
- Responsive: desktop-first (ver UX decisions)

### RNF-04: Seguridad

- API keys de Groq y Google Gemini NUNCA en el frontend
- El backend actúa como proxy: frontend → backend → LLM API
- Variables de entorno para secretos
- CORS configurado solo para el dominio del frontend
- CSP headers configurados

### RNF-05: Testing

- Cobertura de código ≥80%
- Unitarios: Vitest + Testing Library
- E2E: Playwright (flujo completo)
- Componentes: Storybook

### RNF-06: Costo Operacional

- **$0/mes** en producción:
  - Cloudflare Pages: gratuito (ilimitado)
  - Render: gratuito (750h/mes)
  - Groq API: gratuita (Developer plan)
  - Google Gemini API: gratuita (Tier 1, $250/mes cap)
  - GitHub Actions: 2000 min/mes gratis
  - UptimeRobot: gratuito (50 monitores)

### RNF-07: Escalabilidad Académica

- El sistema debe ser demostrable en una sustentación universitaria
- Debe funcionar sin configuración compleja (solo abrir URL)
- Código documentado y con justificación académica de cada decisión

## 4. Restricciones

- **Idioma:** 100% español (interfaz, prompts, respuestas, documentación)
- **Plataforma:** Web (no nativa móvil)
- **Infraestructura:** Solo herramientas gratuitas
- **Tiempo de desarrollo:** ~2 semanas (estimación inicial)
- **Equipo:** Carlos Alberto Canabal Cordero, Sebastián José Leal Flórez

## 5. Referencias

Carpeta: `docs/02-architecture/adr/` para decisiones técnicas detalladas.
