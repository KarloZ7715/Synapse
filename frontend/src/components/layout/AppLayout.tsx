import type { JSX } from "solid-js";

export function AppLayout(props: { header: JSX.Element; nav?: JSX.Element; children: JSX.Element }) {
  return (
    <div class="relative flex h-screen w-screen flex-col overflow-hidden bg-surface text-on-surface">
      {props.header}
      <main class="flex flex-1 overflow-hidden">
        {props.nav}
        <div class="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {props.children}
        </div>
      </main>
    </div>
  );
}
