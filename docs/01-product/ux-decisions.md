# Decisiones UX — Synapse

## 1. Desktop-First con Responsive Mobile

**Decisión:** Desktop-first, con diseño responsive que funciona en móvil.

**Justificación:**

- Proyecto académico: estudiantes de programación frente a un computador escribiendo código
- El contexto de uso es: VS Code abierto + navegador al lado para consultar dudas
- Sin embargo, un estudiante podría consultar dudas rápidas desde el celular (transporte, pasillo, antes de clase)

**Consecuencias:**

- Diseño optimizado para viewports ≥1024px de ancho (layout de 2 paneles)
- En móvil (<768px): layout de 1 columna, paneles apilados verticalmente
- Panel de metadatos colapsable en móvil (ahorra espacio vertical)
- Tipografía monospace para snippets de código (Fira Code o JetBrains Mono)
- Touch targets de al menos 44x44px en móvil
- La experiencia core (preguntar → recibir respuesta) debe ser fluida en ambos formatos

## 2. Interfaz Minimalista

**Decisión:** UI limpia, sin distracciones, enfocada en el contenido.

**Justificación:**

- El valor está en la respuesta del tutor, no en la interfaz
- Estudiantes con frustración/ansiedad necesitan una UI que no abrume
- Menos JS = mejor performance para ONNX Runtime Web

**Consecuencias:**

- Una sola pantalla principal (sin navegación compleja)
- Solo 2 secciones: input (abajo) + respuesta (arriba)
- Panel lateral colapsable con metadatos de clasificación
- Sin modales, sin popups, sin onboarding forzado

## 3. Retroalimentación de Clasificación Visible

**Decisión:** Mostrar los metadatos de clasificación al usuario.

**Justificación:**

- Transparencia: el usuario entiende por qué recibe cierta respuesta
- Valor académico: el profesor puede verificar que la RN funciona
- Permite al usuario corregir si la clasificación es incorrecta (modo "override")

**Consecuencias:**

- Panel de metadatos que muestra:
  - "Te detecté como nivel principiante en algoritmos"
  - Indicador de emoción: "Parece que estás frustrado, voy a explicarlo con calma"
- Botón "Clasificarme diferente" para que el usuario pueda ajustar manualmente
- Si el usuario corrige, se usa su input en lugar del clasificador

## 4. Streaming de Respuesta con Cursor Visible

**Decisión:** Mostrar la respuesta generándose token por token, con un cursor parpadeante.

**Justificación:**

- Reduce la percepción de espera (el usuario ve progreso)
- Experiencia similar a ChatGPT/Claude
- Permite al usuario empezar a leer mientras se genera el resto

**Consecuencias:**

- Implementar `EventSource` en el frontend para recibir SSE
- Animación de cursor intermitente durante la generación
- Renderizado progresivo de Markdown (código con syntax highlighting)

## 5. Soporte para Código

**Decisión:** Soporte nativo para bloques de código con syntax highlighting.

**Justificación:**

- Es un tutor de PROGRAMACIÓN — el código es el contenido principal
- Sin syntax highlighting, el valor pedagógico se reduce drásticamente

**Consecuencias:**

- Usar Shiki o Prism.js para syntax highlighting (lazy-loaded)
- Soporte para: JavaScript, TypeScript, Python, Java, C++, SQL, HTML, CSS
- Botón "Copiar código" en cada bloque
- Los snippets deben ser ejecutables mentalmente (no requieren IDE)

## 6. Historial de Sesión Efímero

**Decisión:** Mostrar la conversación actual (scrollable), sin persistencia.

**Justificación:**

- Mantiene el contexto para preguntas de seguimiento
- No requiere login, base de datos, ni cookies
- Privacidad: los datos se van al cerrar la pestaña

**Consecuencias:**

- Scroll infinito hacia arriba para ver mensajes anteriores
- Máximo 5 pares pregunta-respuesta visibles
- Botón "Nueva conversación" para limpiar contexto

## 7. Accesibilidad Básica

**Decisión:** Cumplir con WCAG 2.2 AA en lo posible.

**Criterios:**

- Contraste mínimo 4.5:1 para texto normal
- Navegación completa por teclado (Tab, Enter, Escape)
- Focus visible en todos los elementos interactivos
- Labels semánticos en campos de formulario
- Texto alternativo en iconos e indicadores de estado

## 8. Dark Mode por Defecto

**Decisión:** Tema oscuro como predeterminado, con opción de cambiar a claro.

**Justificación:**

- Los programadores usan dark mode en sus IDEs
- Reduce fatiga visual en sesiones largas de estudio
- Coherencia visual con el entorno de desarrollo

**Consecuencias:**

- Detectar `prefers-color-scheme` del sistema
- Toggle manual sol/luna
- Tailwind CSS dark mode con selector `class`

## 9. No Login, No Registro

**Decisión:** Sin autenticación de usuarios.

**Justificación:**

- Reduce fricción de uso
- No requiere base de datos
- Sin implicaciones de protección de datos personales (GDPR)

**Consecuencias:**

- Sin guardado de historial
- Sin personalización persistente
- Ideal para demo universitario

