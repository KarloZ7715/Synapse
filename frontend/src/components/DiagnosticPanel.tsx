import { Tabs } from "@ark-ui/solid";
import { MetricCard } from "~/components/diagnostic/MetricCard";
import { RadarChart } from "~/components/diagnostic/RadarChart";
import { Activity, AlertCircle, Clock } from "~/components/icons";
import { Badge } from "~/components/ui/badge";
import type { ClassificationResult, ClassifierStatus } from "~/types/classifier";

const sparklineData = [12, 8, 10, 4, 6, 2, 5, 3, 1, 4];

export function DiagnosticPanel(props: {
  status: ClassifierStatus;
  result: ClassificationResult | null;
  loadMs: number | null;
  error: string | null;
}) {
  const meta = () => props.result?.metadata;

  const radarValues = () => ({
    nivel: meta()?.confianza || 0,
    urgencia: 0.45,
    emocion: 0.71,
    dominio: 0.93,
  });

  return (
    <aside
      class="flex w-[320px] shrink-0 flex-col gap-4 overflow-y-auto border-l border-[var(--border-color)] bg-[var(--bg-base)] p-4"
      aria-label="Diagnóstico"
      data-testid="metadata-panel"
    >
      <h2 class="text-[10px] font-mono font-medium uppercase tracking-widest text-[var(--text-tertiary)]">
        Diagnóstico
      </h2>

      {/* Status line */}
      <div class="text-xs text-[var(--text-secondary)]">
        Estado: <span class="font-mono text-[#22d3ee]">{props.status}</span>
        {props.loadMs !== null && (
          <>
            {" · "}carga:{" "}
            <span class="font-mono text-[var(--text-primary)]">
              {Math.round(props.loadMs)}ms
            </span>
          </>
        )}
      </div>

      {props.error && (
        <div class="flex items-start gap-2 rounded-xl border border-[#f87171]/30 bg-[#f87171]/8 px-3 py-2.5 text-xs text-[#f87171]">
          <AlertCircle color="#f87171" size={14} class="mt-0.5 shrink-0" />
          {props.error}
        </div>
      )}

      {/* Radar */}
      {meta() && (
        <div class="rounded-xl bg-[var(--bg-elevated)] p-4 ring-1 ring-[var(--border-color)]">
          <div class="mb-3 flex items-center gap-2 font-mono text-[10px] font-medium text-[var(--text-secondary)]">
            <TargetIcon color="var(--text-secondary)" size={12} />
            Clasificación
          </div>
          <RadarChart values={radarValues()} />
          <div class="mt-3 flex flex-wrap gap-1.5">
            <Badge variant="blue">Nivel · {meta()?.nivel_tecnico ?? "—"}</Badge>
            <Badge variant="amber">Urgencia · {meta()?.urgencia ?? "—"}</Badge>
            <Badge variant="emerald">Dominio · {meta()?.dominio ?? "—"}</Badge>
            <Badge variant="purple">Emoción · {meta()?.emocion ?? "—"}</Badge>
          </div>
        </div>
      )}

      {/* Metrics */}
      <div>
        <div class="mb-2 flex items-center gap-2 font-mono text-[10px] font-medium text-[var(--text-secondary)]">
          <Activity color="var(--text-secondary)" size={12} />
          Métricas
        </div>
        <div class="grid grid-cols-2 gap-2">
          <MetricCard
            label="Inferencia RN"
            value={props.result?.inferenceMs || 0}
            unit="ms"
            color="#22d3ee"
            sparkline={sparklineData}
          />
          <MetricCard
            label="Tokens/s"
            value={560}
            color="#c084fc"
            sparkline={[14, 12, 8, 10, 6, 4, 2, 5, 3, 1]}
          />
          <MetricCard label="Tokens totales" value={1.2} unit="K" />
          <MetricCard label="Proveedor" value="Groq" color="#4ade80" />
        </div>
      </div>

      {/* Telemetry with Ark UI Tabs */}
      <div class="rounded-xl bg-[var(--bg-elevated)] p-4 ring-1 ring-[var(--border-color)]">
        <div class="mb-2 flex items-center gap-2 font-mono text-[10px] font-medium text-[var(--text-secondary)]">
          <BrainIcon color="var(--text-secondary)" size={12} />
          Info Técnica
        </div>
        <Tabs.Root defaultValue="rn">
          <Tabs.List class="mb-2 flex gap-1 border-b border-[var(--border-color)]">
            {["rn", "llm"].map((tab) => (
              // biome-ignore lint/correctness/useJsxKeyInIterable: Ark UI Tabs.Trigger does not accept key in Solid
              <Tabs.Trigger
                value={tab}
                class="px-2 py-1 font-mono text-[10px] uppercase text-[var(--text-tertiary)] transition-colors data-[selected]:text-[var(--text-primary)]"
              >
                {tab === "rn" ? "RN" : "LLM"}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          <Tabs.Content value="rn" class="space-y-1.5 font-mono text-[10px]">
            <div class="flex justify-between">
              <span class="text-[var(--text-tertiary)]">Modelo</span>
              <span class="text-[var(--text-secondary)]">TextCNN + FastText</span>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--text-tertiary)]">Backend</span>
              <span class="text-[#22d3ee]">WebGPU</span>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--text-tertiary)]">VRAM</span>
              <span class="text-[var(--text-secondary)]">~45MB</span>
            </div>
          </Tabs.Content>
          <Tabs.Content value="llm" class="space-y-1.5 font-mono text-[10px]">
            <div class="flex justify-between">
              <span class="text-[var(--text-tertiary)]">Modelo</span>
              <span class="text-[var(--text-secondary)]">llama-3.1-8b</span>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--text-tertiary)]">Temp</span>
              <span class="text-[var(--text-secondary)]">0.7</span>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--text-tertiary)]">Top P</span>
              <span class="text-[var(--text-secondary)]">0.95</span>
            </div>
          </Tabs.Content>
        </Tabs.Root>
      </div>

      {/* History */}
      <div>
        <div class="mb-2 flex items-center gap-2 font-mono text-[10px] font-medium text-[var(--text-secondary)]">
          <Clock color="var(--text-secondary)" size={12} />
          Historial
        </div>
        <div class="space-y-1">
          <button
            type="button"
            class="flex w-full items-center gap-1.5 rounded-lg px-2.5 py-2 text-left font-mono text-[10px] text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-elevated)]"
          >
            <span class="text-[var(--text-tertiary)]">12:01</span>
            <span>·</span>
            <span>Algoritmos</span>
            <span>·</span>
            <AlertCircle color="#f87171" size={10} />
          </button>
        </div>
      </div>
    </aside>
  );
}

// Inline mini-icons for DiagnosticPanel only
function TargetIcon(props: { size?: number; class?: string; color?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={props.size ?? 16}
      height={props.size ?? 16}
      viewBox="0 0 24 24"
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      class={props.class}
      role="img"
      aria-label="Target icon"
    >
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" fill={props.color ?? "currentColor"} />
    </svg>
  );
}

function BrainIcon(props: { size?: number; class?: string; color?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={props.size ?? 16}
      height={props.size ?? 16}
      viewBox="0 0 24 24"
      fill={props.color ?? "currentColor"}
      stroke="none"
      class={props.class}
      role="img"
      aria-label="Brain icon"
    >
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15.5a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15.5a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  );
}
