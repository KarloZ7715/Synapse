import { For, createMemo } from "solid-js";

const AXES = [
  { label: "Nivel", color: "#60a5fa", key: "nivel" },
  { label: "Urg", color: "#fbbf24", key: "urgencia" },
  { label: "Dom", color: "#34d399", key: "dominio" },
  { label: "Emo", color: "#a78bfa", key: "emocion" },
] as const;

export function RadarChart(props: {
  values: Record<string, number>;
}) {
  const size = 160;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = 60;

  const points = createMemo(() => {
    return AXES.map((axis, i) => {
      const angle = (Math.PI * 2 * i) / AXES.length - Math.PI / 2;
      const val = Math.min(1, Math.max(0, props.values[axis.key] || 0));
      const r = val * maxR;
      return {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
        labelX: cx + (maxR + 14) * Math.cos(angle),
        labelY: cy + (maxR + 14) * Math.sin(angle),
        color: axis.color,
        label: axis.label,
      };
    });
  });

  const polyPoints = () =>
    points()
      .map((p) => `${p.x},${p.y}`)
      .join(" ");

  return (
    <div class="flex flex-col items-center">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label="Radar chart"
      >
        {/* Background circles */}
        <circle
          cx={cx}
          cy={cy}
          r={maxR / 3}
          fill="none"
          stroke="var(--border-color)"
          stroke-width="0.5"
        />
        <circle
          cx={cx}
          cy={cy}
          r={(maxR * 2) / 3}
          fill="none"
          stroke="var(--border-color)"
          stroke-width="0.5"
        />
        <circle
          cx={cx}
          cy={cy}
          r={maxR}
          fill="none"
          stroke="var(--border-color)"
          stroke-width="0.5"
        />

        {/* Axes */}
        <For each={points()}>
          {(p) => (
            <line
              x1={cx}
              y1={cy}
              x2={cx + maxR * Math.cos(Math.atan2(p.y - cy, p.x - cx))}
              y2={cy + maxR * Math.sin(Math.atan2(p.y - cy, p.x - cx))}
              stroke="var(--border-color)"
              stroke-width="1"
            />
          )}
        </For>

        {/* Polygon */}
        <polygon
          points={polyPoints()}
          fill="rgba(34, 211, 238, 0.08)"
          stroke="#22d3ee"
          stroke-width="1.5"
          class="transition-all duration-500"
        />

        {/* Labels */}
        <For each={points()}>
          {(p) => (
            <text
              x={p.labelX}
              y={p.labelY}
              text-anchor="middle"
              dominant-baseline="middle"
              fill={p.color}
              font-size="9"
              font-family="JetBrains Mono"
            >
              {p.label}
            </text>
          )}
        </For>
      </svg>
    </div>
  );
}
