import type { JSX } from "solid-js";
import { cn } from "~/lib/utils";

export function Card(props: { children: JSX.Element; class?: string }) {
  return (
    <div
      class={cn(
        "rounded-md border bg-[var(--bg-elevated)] p-[var(--spacing-card)]",
        "border-[var(--border-color)] shadow-[var(--shadow-panel)]",
        "transition-all duration-150 ease-out",
        "hover:border-[var(--border-color)]/80",
        props.class,
      )}
    >
      {props.children}
    </div>
  );
}
