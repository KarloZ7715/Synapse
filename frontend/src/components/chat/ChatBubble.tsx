import type { JSX } from "solid-js";
import { cn } from "~/lib/utils";

type Props = {
  children: JSX.Element;
  variant: "user" | "assistant";
  class?: string;
};

export function ChatBubble(props: Props) {
  return (
    <div
      class={cn(
        "max-w-[85%] rounded-lg p-3 text-sm leading-relaxed transition-all duration-200",
        props.variant === "user"
          ? "border-l-2 border-[#22d3ee] bg-[var(--bg-surface)] text-[var(--text-primary)] self-end"
          : "border-l-2 border-[var(--border-color)] bg-[var(--bg-elevated)] text-[var(--text-primary)] self-start",
        props.class,
      )}
    >
      {props.children}
    </div>
  );
}
