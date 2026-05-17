import type { ClassificationResult } from "~/types/classifier";
import type { ClassifierStatus } from "~/types/classifier";

type Props = {
  status: ClassifierStatus;
  result: ClassificationResult | null;
  loadMs: number | null;
  error: string | null;
};

function chip(label: string, value: string, color: string) {
  return (
    <div class="flex flex-col gap-0.5 rounded-md border border-[#292930] bg-[#1c1c22] px-2 py-1.5">
      <span class="text-[10px] font-medium uppercase tracking-wide text-[#6b6b75]">{label}</span>
      <span class={`text-sm font-medium ${color}`}>{value}</span>
    </div>
  );
}

export function MetadataPanel(props: Props) {
  const meta = () => props.result?.metadata;

  return (
    <aside
      class="flex w-full max-w-[320px] flex-col gap-3 rounded-lg border border-[#292930] bg-[#141418] p-3"
      aria-label="Metadatos de clasificación"
      data-testid="metadata-panel"
    >
      <h2 class="text-sm font-semibold tracking-wide text-[#9898a0]">Diagnóstico</h2>
      <div class="text-xs text-[#9898a0]">
        Estado: <span class="font-mono-ui text-cyan-300">{props.status}</span>
        {props.loadMs !== null && (
          <>
            {" "}
            · carga modelo:{" "}
            <span class="font-mono-ui text-[#ededef]">{Math.round(props.loadMs)} ms</span>
          </>
        )}
        {props.result && (
          <>
            {" "}
            · inferencia:{" "}
            <span class="font-mono-ui text-[#ededef]">
              {Math.round(props.result.inferenceMs)} ms
            </span>
            {" · "}
            <span class="font-mono-ui text-[#ededef]">{props.result.ortBackend}</span>
          </>
        )}
      </div>
      {props.error && (
        <div class="rounded-md border border-red-500/40 bg-red-500/10 px-2 py-2 text-xs text-red-200">
          {props.error}
        </div>
      )}
      <div class="grid grid-cols-2 gap-2">
        {chip("Nivel", meta()?.nivel_tecnico ?? "—", "text-blue-300")}
        {chip("Urgencia", meta()?.urgencia ?? "—", "text-amber-300")}
        {chip("Emoción", meta()?.emocion ?? "—", "text-violet-300")}
        {chip("Dominio", meta()?.dominio ?? "—", "text-emerald-300")}
      </div>
      {meta() && (
        <div class="rounded-md border border-[#292930] bg-[#0a0a0c] px-2 py-2 text-xs">
          <span class="text-[#6b6b75]">confianza (geom.): </span>
          <span class="font-mono-ui text-[#22d3ee]">{meta()?.confianza.toFixed(4)}</span>
        </div>
      )}
    </aside>
  );
}
