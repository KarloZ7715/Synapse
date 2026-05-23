import { Show } from "solid-js";
import { useTheme } from "~/hooks/useTheme";
import type { ClassifierStatus } from "~/types/classifier";

function healthLabel(status: ClassifierStatus): string {
  switch (status) {
    case "ready":
      return "STABLE";
    case "classifying":
      return "PROCESSING";
    case "loading_model":
      return "LOADING";
    case "error":
      return "ERROR";
    default:
      return "IDLE";
  }
}

function healthDotClass(status: ClassifierStatus): string {
  if (status === "error") return "bg-error";
  if (status === "ready" || status === "classifying") return "bg-primary-fixed";
  return "bg-on-surface-variant";
}

export function AppHeader(props: {
  status: ClassifierStatus;
  loadMs: number | null;
  inferenceMs: number | null;
  backend: "webgpu" | "wasm" | null;
  onToggleTerminal: () => void;
}) {
  const { theme, toggle } = useTheme();

  return (
    <header class="z-50 flex h-16 w-full shrink-0 items-center justify-between border-b border-primary-fixed/20 bg-surface-container-lowest/80 px-gutter text-primary-fixed backdrop-blur-md">
      <div class="flex items-center gap-4">
        <span class="material-symbols-outlined text-3xl text-primary-fixed">psychology</span>
        <h1
          class="glitch-text font-display text-[20px] font-bold tracking-tighter text-primary-fixed drop-shadow-[0_0_8px_rgba(121,255,91,0.4)] md:text-[24px]"
          data-text="SYNAPSE AI v1.0.4"
        >
          SYNAPSE AI v1.0.4
        </h1>
      </div>

      <div class="hidden items-center gap-6 font-mono text-[12px] uppercase tracking-wider md:flex">
        <div class="flex items-center gap-2">
          <span
            class={`h-2 w-2 animate-pulse rounded-full shadow-[0_0_8px_currentColor] ${healthDotClass(props.status)}`}
          />
          <span class="text-on-surface-variant">
            SYSTEM_HEALTH: <span class="text-on-surface">{healthLabel(props.status)}</span>
          </span>
        </div>
        <Show when={props.inferenceMs !== null}>
          <div class="text-on-surface-variant">
            LATENCY:{" "}
            <span class="text-on-surface">{Math.round(props.inferenceMs ?? 0)}ms</span>
          </div>
        </Show>
        <Show when={props.inferenceMs === null && props.loadMs !== null}>
          <div class="text-on-surface-variant">
            LOAD: <span class="text-on-surface">{Math.round(props.loadMs ?? 0)}ms</span>
          </div>
        </Show>
        <Show when={props.backend !== null}>
          <div class="text-on-surface-variant">
            BACKEND: <span class="text-on-surface">{(props.backend ?? "").toUpperCase()}</span>
          </div>
        </Show>
      </div>

      <div class="flex items-center gap-1">
        <button
          type="button"
          class="p-2 text-on-surface-variant transition-all hover:bg-surface-variant hover:text-primary-fixed"
          onClick={props.onToggleTerminal}
          aria-label="Abrir terminal"
        >
          <span class="material-symbols-outlined">terminal</span>
        </button>
        <button
          type="button"
          class="theme-toggle-btn p-2 text-on-surface-variant transition-colors hover:bg-surface-variant hover:text-primary-fixed"
          onClick={toggle}
          aria-label={theme() === "dark" ? "Modo claro" : "Modo oscuro"}
          title={theme() === "dark" ? "Activar modo claro" : "Activar modo oscuro"}
        >
          <span class="theme-toggle-icon material-symbols-outlined">
            {theme() === "dark" ? "light_mode" : "dark_mode"}
          </span>
        </button>
      </div>
    </header>
  );
}
