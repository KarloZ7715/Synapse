/** Ejemplos inspirados en consultas reales del dataset (Stack Overflow ES + GoEmotions). */
export type ExamplePrompt = {
  id: string;
  text: string;
  domain: string;
  nivel: string;
  emotion: string;
};

export const EXAMPLE_PROMPTS: ReadonlyArray<ExamplePrompt> = [
  {
    id: "python-matrix-sort",
    text: "¿Cómo puedo ordenar una matriz de forma descendente en Python?",
    domain: "backend",
    nivel: "principiante",
    emotion: "frustracion",
  },
  {
    id: "pandas-nan-corr",
    text: "¿Cómo calcular correlaciones en un DataFrame con muchos NaN?",
    domain: "data_science",
    nivel: "principiante",
    emotion: "motivacion",
  },
  {
    id: "spring-getters",
    text: "¿Por qué no me detecta los getter y setter en Spring Boot?",
    domain: "backend",
    nivel: "intermedio",
    emotion: "frustracion",
  },
  {
    id: "flutter-play-bundle",
    text: "¿Por qué el bundle de Play Store no se comporta igual que el APK local en Flutter?",
    domain: "movil",
    nivel: "intermedio",
    emotion: "frustracion",
  },
  {
    id: "jwt-middleware",
    text: "¿Cómo validar un JWT en middleware para proteger rutas privadas en Node?",
    domain: "backend",
    nivel: "principiante",
    emotion: "ansiedad",
  },
  {
    id: "s3-permissions",
    text: "¿Cómo dar permisos de lectura y escritura en un bucket S3 a un usuario externo?",
    domain: "devops",
    nivel: "intermedio",
    emotion: "frustracion",
  },
  {
    id: "sql-joins",
    text: "Tengo síntomas raros con JOINs en SQL: ¿cómo depuro si el problema es el índice o la consulta?",
    domain: "bases_de_datos",
    nivel: "intermedio",
    emotion: "confusion",
  },
  {
    id: "vue-laravel-records",
    text: "¿Por qué no se visualizan los registros de Laravel dentro de un componente Vue?",
    domain: "frontend",
    nivel: "intermedio",
    emotion: "confusion",
  },
  {
    id: "recursion-python",
    text: "No entiendo nada de recursividad en Python, ¿me lo explicas con un ejemplo corto?",
    domain: "backend",
    nivel: "principiante",
    emotion: "confusion",
  },
  {
    id: "android-window-token",
    text: "Error «token null is not valid» al abrir un diálogo en Android Studio, ¿qué reviso primero?",
    domain: "movil",
    nivel: "intermedio",
    emotion: "confusion",
  },
] as const;
