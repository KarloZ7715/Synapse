import { Sparkline } from "./Sparkline";

export function MetricCard(props: {
  label: string;
  value: string | number;
  unit?: string | undefined;
  color?: string | undefined;
  sparkline?: number[] | undefined;
}) {
  return (
    <div class="rounded-lg bg-[var(--bg-elevated)] p-2.5 transition-all hover:shadow-[var(--shadow-panel)]">
      <p
        class="font-mono text-xl font-medium"
        style={{ color: props.color || "var(--text-primary)" }}
      >
        {props.value}
        {props.unit && <span class="text-sm text-[var(--text-secondary)]">{props.unit}</span>}
      </p>
      <p class="mt-0.5 font-mono text-[10px] text-[var(--text-tertiary)]">{props.label}</p>
      {props.sparkline && <Sparkline data={props.sparkline} color={props.color} />}
    </div>
  );
}
