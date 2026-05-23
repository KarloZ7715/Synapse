import { type JSX, createContext, createEffect, createSignal, useContext } from "solid-js";
import { applyHljsTheme } from "~/lib/hljsTheme";

type Theme = "dark" | "light";

const STORAGE_KEY = "synapse-theme";

const ThemeContext = createContext<{
  theme: () => Theme;
  toggle: () => void;
}>({ theme: () => "dark" as Theme, toggle: () => {} });

function readStoredTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return "dark";
}

function applyTheme(t: Theme) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem(STORAGE_KEY, t);
  applyHljsTheme(t);
}

function runThemeTransition(apply: () => void) {
  const root = document.documentElement;
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const finish = () => {
    root.classList.remove("theme-transition-active");
  };

  const runWithFlash = () => {
    if (!prefersReduced) {
      const overlay = document.createElement("div");
      overlay.className = "theme-flash-overlay";
      overlay.setAttribute("aria-hidden", "true");
      document.body.appendChild(overlay);
      window.setTimeout(() => overlay.remove(), 700);
    }

    root.classList.add("theme-transition-active");
    apply();
    window.setTimeout(finish, prefersReduced ? 0 : 560);
  };

  if (!prefersReduced && "startViewTransition" in document) {
    const transition = (
      document as Document & {
        startViewTransition: (cb: () => void) => { finished: Promise<void> };
      }
    ).startViewTransition(() => {
      apply();
    });
    root.classList.add("theme-transition-active");
    void transition.finished.finally(() => {
      finish();
      if (!prefersReduced) {
        const overlay = document.createElement("div");
        overlay.className = "theme-flash-overlay";
        overlay.setAttribute("aria-hidden", "true");
        document.body.appendChild(overlay);
        window.setTimeout(() => overlay.remove(), 700);
      }
    });
    return;
  }

  runWithFlash();
}

export function ThemeProvider(props: { children: JSX.Element }) {
  const [theme, setTheme] = createSignal<Theme>(readStoredTheme());

  applyTheme(theme());

  createEffect(() => {
    applyHljsTheme(theme());
  });

  const toggle = () => {
    const next: Theme = theme() === "dark" ? "light" : "dark";
    runThemeTransition(() => {
      setTheme(next);
      applyTheme(next);
    });
  };

  return <ThemeContext.Provider value={{ theme, toggle }}>{props.children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
