import { type JSX, createContext, createSignal, useContext } from "solid-js";

type Theme = "dark" | "light";

const ThemeContext = createContext<{
  theme: () => Theme;
  toggle: () => void;
}>({ theme: () => "dark" as Theme, toggle: () => {} });

export function ThemeProvider(props: { children: JSX.Element }) {
  const [theme, setTheme] = createSignal<Theme>(
    (localStorage.getItem("synapse-theme") as Theme) ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  );

  const apply = (t: Theme) => {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("synapse-theme", t);
  };

  apply(theme());

  const toggle = () => {
    const next = theme() === "dark" ? "light" : "dark";
    setTheme(next);
    apply(next);
  };

  return <ThemeContext.Provider value={{ theme, toggle }}>{props.children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
