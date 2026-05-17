export function Sparkline(props: { data: number[]; color?: string | undefined }) {
  const color = props.color || "#22d3ee";
  const width = 100;
  const height = 16;
  const max = Math.max(...props.data, 1);
  const min = Math.min(...props.data, 0);
  const range = max - min || 1;

  const points = props.data
    .map((v, i) => {
      const x = (i / (props.data.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Sparkline"
    >
      <polyline points={points} fill="none" stroke={color} stroke-width="1" opacity="0.5" />
    </svg>
  );
}
