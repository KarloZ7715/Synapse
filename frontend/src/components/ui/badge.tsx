import type { JSX } from "solid-js";
import { cn } from "~/lib/utils";

const variants = {
  default: "bg-[var(--bg-surface)] text-[var(--text-secondary)] border-[var(--border-color)]",
  cyan: "bg-[#22d3ee]/10 text-[#22d3ee] border-[#22d3ee]/20",
  purple: "bg-[#c084fc]/10 text-[#c084fc] border-[#c084fc]/20",
  blue: "bg-[#60a5fa]/10 text-[#60a5fa] border-[#60a5fa]/20",
  amber: "bg-[#fbbf24]/10 text-[#fbbf24] border-[#fbbf24]/20",
  emerald: "bg-[#34d399]/10 text-[#34d399] border-[#34d399]/20",
  red: "bg-[#f87171]/10 text-[#f87171] border-[#f87171]/20",
};

export function Badge(props: {
  children: JSX.Element;
  variant?: keyof typeof variants;
  class?: string;
}) {
  return (
    <span
      class={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        variants[props.variant || "default"],
        props.class,
      )}
    >
      {props.children}
    </span>
  );
}
