import { Moon, Sun, Terminal, Zap } from "~/components/icons";
import { useTheme } from "~/hooks/useTheme";

export function AppHeader() {
  const { theme, toggle } = useTheme();

  return (
    <header class="flex h-12 shrink-0 items-center justify-between border-b border-[var(--border-color)] bg-[var(--bg-base)]/80 px-4 backdrop-blur-md">
      <div class="flex items-center gap-3">
        <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-[#22d3ee]/30 to-[#22d3ee]/10 ring-1 ring-[#22d3ee]/20">
          <Zap color="#22d3ee" size={16} />
        </div>
        <span class="text-sm font-semibold tracking-tight text-[var(--text-primary)]">
          Synapse
        </span>
        <span class="rounded bg-[var(--bg-elevated)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-tertiary)]">
          v0.1
        </span>
      </div>

      <div class="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
        <span class="flex items-center gap-1.5 font-mono">
          <span class="h-1.5 w-1.5 rounded-full bg-[#22d3ee] shadow-[0_0_6px_#22d3ee]" />
          WebGPU
        </span>
        <span class="font-mono text-[var(--text-tertiary)]">12ms</span>
        <button
          type="button"
          onClick={toggle}
          class="rounded-lg p-1.5 transition-all hover:bg-[var(--bg-surface)] hover:shadow-[var(--shadow-panel)]"
          aria-label={theme() === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
        >
          {theme() === "dark" ? (
            <Sun color="var(--text-secondary)" size={16} />
          ) : (
            <Moon color="var(--text-secondary)" size={16} />
          )}
        </button>
        <button
          type="button"
          class="rounded-lg p-1.5 transition-all hover:bg-[var(--bg-surface)] hover:shadow-[var(--shadow-panel)]"
          aria-label="Consola"
        >
          <Terminal color="var(--text-secondary)" size={16} />
        </button>
      </div>
    </header>
  );
}
