/** Evita que SolidJS agrupe varios tokens del mismo chunk SSE en un solo frame. */
export function scheduleStreamingUpdate(run: () => void): void {
  queueMicrotask(run);
}
