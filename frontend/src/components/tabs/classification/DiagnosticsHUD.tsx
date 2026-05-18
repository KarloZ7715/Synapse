import { For, Show } from "solid-js";
import type { ClassificationResult, ClassifierStatus } from "~/types/classifier";

const AXIS_LABELS = ["NIVEL", "URGENCIA", "EMOCIÓN", "DOMINIO"] as const;

export function DiagnosticsHUD(props: {
  status: ClassifierStatus;
  result: ClassificationResult | null;
  loadMs: number | null;
  error: string | null;
}) {
  return (
    <aside class="hidden w-column-diagnostics shrink-0 flex-col gap-6 overflow-y-auto border-l border-outline-variant bg-surface-container-high p-6 md:flex">
      <header class="flex items-end justify-between border-b border-outline-variant pb-2">
        <h3 class="font-mono text-[12px] font-bold uppercase tracking-widest text-on-surface-variant">
          DIAGNOSTICS HUD
        </h3>
        <span class="material-symbols-outlined text-sm text-on-surface-variant">query_stats</span>
      </header>

      <Show when={props.error}>
        <div class="flex items-start gap-2 border border-error bg-error/10 p-3 font-mono text-[11px] text-error">
          <span class="material-symbols-outlined text-base">error</span>
          <span>{props.error}</span>
        </div>
      </Show>

      <ConfidenceRadar result={props.result} />

      <div class="grid grid-cols-1 gap-3 font-mono text-sm">
        <MetricCard
          label="Inferencia"
          value={props.result ? `${Math.round(props.result.inferenceMs)}ms` : "—"}
          accent="primary"
        />
        <MetricCard
          label="Confianza"
          value={
            props.result ? `${Math.round(props.result.metadata.confianza * 100)}%` : "—"
          }
          accent="secondary"
        />
        <MetricCard label="Backend ONNX" value={props.result?.ortBackend.toUpperCase() ?? "—"} />
        <MetricCard
          label="Carga modelo"
          value={props.loadMs !== null ? `${Math.round(props.loadMs)}ms` : "—"}
        />
      </div>

      <StatusLog
        status={props.status}
        result={props.result}
        loadMs={props.loadMs}
        error={props.error}
      />
    </aside>
  );
}

function MetricCard(props: {
  label: string;
  value: string;
  accent?: "primary" | "secondary";
}) {
  const containerCls = () => {
    if (props.accent === "primary")
      return "border-primary-fixed/30 bg-primary-fixed/5 hover:border-primary-fixed";
    if (props.accent === "secondary")
      return "border-secondary-fixed/30 bg-secondary-fixed/5 hover:border-secondary-fixed";
    return "border-outline-variant bg-surface";
  };
  const valueCls = () => {
    if (props.accent === "primary") return "text-primary-fixed";
    if (props.accent === "secondary") return "text-secondary-fixed";
    return "text-on-surface";
  };
  return (
    <div class={`flex items-center justify-between border p-3 transition-colors ${containerCls()}`}>
      <span class="text-xs uppercase text-on-surface-variant">{props.label}</span>
      <span class={`font-bold tracking-wider ${valueCls()}`}>{props.value}</span>
    </div>
  );
}

function ConfidenceRadar(props: { result: ClassificationResult | null }) {
  const r = () => props.result;
  const vals = () => {
    const cur = r();
    if (!cur) return [0, 0, 0, 0] as const;
    return [
      cur.headConfidences.nivel_tecnico,
      cur.headConfidences.urgencia,
      cur.headConfidences.emocion,
      cur.headConfidences.dominio,
    ] as const;
  };
  const points = () => {
    const [n, u, e, d] = vals();
    const cx = 50;
    const cy = 50;
    const rad = 40;
    return [
      [cx, cy - n * rad],
      [cx + u * rad, cy],
      [cx, cy + e * rad],
      [cx - d * rad, cy],
    ];
  };

  return (
    <div class="relative border border-outline-variant bg-surface-dim p-4">
      <div class="absolute left-0 top-0 border-b border-r border-outline-variant bg-surface px-2 py-0.5 font-mono text-[10px] uppercase text-on-surface-variant">
        CONFIDENCE_MATRIX
      </div>
      <div class="relative mt-6 flex aspect-square w-full items-center justify-center">
        {/* Brutalist concentric squares */}
        <div class="absolute h-full w-full border border-outline-variant/30" />
        <div class="absolute h-3/4 w-3/4 border border-outline-variant/50" />
        <div class="absolute h-1/2 w-1/2 border border-outline-variant/70" />
        <div class="absolute h-1/4 w-1/4 border border-outline-variant" />
        {/* Crosshair */}
        <div class="absolute h-px w-full bg-outline-variant/60" />
        <div class="absolute h-full w-px bg-outline-variant/60" />
        <svg
          class="absolute h-full w-full text-primary-fixed"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-label="Radar de confianza por cabeza"
          role="img"
        >
          <Show when={props.result}>
            <polygon
              fill="currentColor"
              fill-opacity="0.25"
              stroke="currentColor"
              stroke-width="1.5"
              points={points()
                .map(([x, y]) => `${x},${y}`)
                .join(" ")}
            />
            <For each={points()}>
              {([x, y]) => (
                <rect x={x - 1.5} y={y - 1.5} width="3" height="3" fill="currentColor" />
              )}
            </For>
          </Show>
        </svg>
        {/* Axis labels */}
        <span class="absolute left-1/2 top-1 -translate-x-1/2 font-mono text-[9px] uppercase text-on-surface-variant">
          {AXIS_LABELS[0]}
        </span>
        <span class="absolute right-1 top-1/2 -translate-y-1/2 font-mono text-[9px] uppercase text-on-surface-variant">
          {AXIS_LABELS[1]}
        </span>
        <span class="absolute bottom-1 left-1/2 -translate-x-1/2 font-mono text-[9px] uppercase text-on-surface-variant">
          {AXIS_LABELS[2]}
        </span>
        <span class="absolute left-1 top-1/2 -translate-y-1/2 font-mono text-[9px] uppercase text-on-surface-variant">
          {AXIS_LABELS[3]}
        </span>
      </div>
    </div>
  );
}

type LogKind = "info" | "ok" | "warn" | "error";

function StatusLog(props: {
  status: ClassifierStatus;
  result: ClassificationResult | null;
  loadMs: number | null;
  error: string | null;
}) {
  const entries = (): Array<{ kind: LogKind; text: string }> => {
    const out: Array<{ kind: LogKind; text: string }> = [];
    if (props.loadMs !== null) {
      out.push({ kind: "ok", text: `Modelo cargado (${Math.round(props.loadMs)}ms)` });
    }
    if (props.status === "loading_model") {
      out.push({ kind: "info", text: "Cargando modelo TextCNN local..." });
    } else if (props.status === "ready" && !props.result) {
      out.push({ kind: "info", text: "Esperando consulta..." });
    } else if (props.status === "classifying") {
      out.push({ kind: "info", text: "Inferencia en curso..." });
    }
    if (props.result) {
      out.push({
        kind: "ok",
        text: `Clasificado en ${Math.round(props.result.inferenceMs)}ms (${props.result.ortBackend})`,
      });
      out.push({
        kind: "info",
        text: "Metadata lista para backend /api/chat",
      });
    }
    if (props.error) {
      out.push({ kind: "error", text: props.error });
    }
    return out;
  };

  const colorOf = (k: LogKind) =>
    k === "ok"
      ? "text-primary-fixed"
      : k === "warn"
        ? "text-tertiary-fixed-dim"
        : k === "error"
          ? "text-error"
          : "text-secondary-fixed";
  const tagOf = (k: LogKind) =>
    k === "ok" ? "[OK]" : k === "warn" ? "[WARN]" : k === "error" ? "[ERR]" : "[INFO]";

  return (
    <div class="flex min-h-[160px] flex-1 flex-col border border-outline-variant bg-surface-dim">
      <div class="flex items-center justify-between border-b border-outline-variant bg-surface-variant p-1 font-mono text-[10px] uppercase">
        <span class="ml-2 text-on-surface-variant">sys_log.out</span>
        <div class="mr-1 flex gap-1">
          <span class="h-2 w-2 rounded-full bg-outline" />
          <span class="h-2 w-2 rounded-full bg-outline" />
          <span class="h-2 w-2 rounded-full bg-outline" />
        </div>
      </div>
      <div class="space-y-1 overflow-y-auto p-3 font-mono text-[11px] text-on-surface-variant">
        <For each={entries()}>
          {(entry) => (
            <p>
              <span class={`font-bold ${colorOf(entry.kind)}`}>{tagOf(entry.kind)}</span>{" "}
              {entry.text}
            </p>
          )}
        </For>
      </div>
    </div>
  );
}
