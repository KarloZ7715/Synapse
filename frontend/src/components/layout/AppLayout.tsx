import type { JSX } from "solid-js";
import { AppHeader } from "./AppHeader";

export function AppLayout(props: { children: JSX.Element }) {
  return (
    <div class="flex h-screen flex-col overflow-hidden bg-[var(--bg-base)]">
      <AppHeader />
      <main class="flex min-h-0 flex-1">{props.children}</main>
    </div>
  );
}
