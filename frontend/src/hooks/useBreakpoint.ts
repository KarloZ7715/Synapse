import { createSignal, onCleanup } from "solid-js";

export function useBreakpoint(breakpoint = 768) {
  const [matches, setMatches] = createSignal(window.innerWidth < breakpoint);

  const mql = window.matchMedia(`(max-width: ${breakpoint}px)`);
  const handler = (e: MediaQueryListEvent) => setMatches(e.matches);

  mql.addEventListener("change", handler);
  onCleanup(() => mql.removeEventListener("change", handler));

  return matches;
}
