import type { JSX } from "solid-js";

type IconProps = {
  class?: string;
  size?: number;
  color?: string;
};

const defaults: JSX.SvgSVGAttributes<SVGSVGElement> = {
  xmlns: "http://www.w3.org/2000/svg",
  width: "16",
  height: "16",
  viewBox: "0 0 24 24",
  "stroke-linecap": "round",
  "stroke-linejoin": "round",
  "aria-hidden": "true",
};

export function Zap(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill={props.color ?? "currentColor"}
      stroke="none"
    >
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  );
}

export function Moon(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

export function Sun(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <circle cx="12" cy="12" r="5" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

export function Terminal(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

export function FileText(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

export function Type(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <polyline points="4 7 4 4 20 4 20 7" />
      <line x1="9" y1="20" x2="15" y2="20" />
      <line x1="12" y1="4" x2="12" y2="20" />
    </svg>
  );
}

export function Brain(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill={props.color ?? "currentColor"}
      stroke="none"
    >
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15.5a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15.5a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  );
}

export function Target(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" fill={props.color ?? "currentColor"} />
    </svg>
  );
}

export function FileCode(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <polyline points="9 13 11 15 15 11" />
    </svg>
  );
}

export function Monitor(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}

export function Paperclip(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}

export function Send(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill={props.color ?? "currentColor"}
      stroke="none"
    >
      <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  );
}

export function Activity(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

export function Clock(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

export function Crosshair(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="22" y1="12" x2="18" y2="12" />
      <line x1="6" y1="12" x2="2" y2="12" />
      <line x1="12" y1="6" x2="12" y2="2" />
      <line x1="12" y1="22" x2="12" y2="18" />
    </svg>
  );
}

export function ChevronDown(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export function Cpu(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
      <rect x="9" y="9" width="6" height="6" />
      <line x1="9" y1="1" x2="9" y2="4" />
      <line x1="15" y1="1" x2="15" y2="4" />
      <line x1="9" y1="20" x2="9" y2="23" />
      <line x1="15" y1="20" x2="15" y2="23" />
      <line x1="20" y1="9" x2="23" y2="9" />
      <line x1="20" y1="14" x2="23" y2="14" />
      <line x1="1" y1="9" x2="4" y2="9" />
      <line x1="1" y1="14" x2="4" y2="14" />
    </svg>
  );
}

export function AlertCircle(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill="none"
      stroke={props.color ?? "currentColor"}
      stroke-width="2.5"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

export function Sparkles(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill={props.color ?? "currentColor"}
      stroke="none"
    >
      <path d="M12 2l1.5 4.5L18 8l-4.5 1.5L12 14l-1.5-4.5L6 8l4.5-1.5z" />
      <path d="M5 16l1 3 3 1-3 1-1 3-1-3-3-1 3-1z" opacity="0.5" />
      <path d="M19 16l1 3 3 1-3 1-1 3-1-3-3-1 3-1z" opacity="0.5" />
    </svg>
  );
}

export function MessageSquare(props: IconProps) {
  return (
    <svg
      {...defaults}
      class={props.class}
      width={props.size ?? 16}
      height={props.size ?? 16}
      fill={props.color ?? "currentColor"}
      stroke="none"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
