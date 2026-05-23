import hljsDarkUrl from "highlight.js/styles/github-dark.min.css?url";
import hljsLightUrl from "highlight.js/styles/github.min.css?url";

const LINK_ID = "synapse-hljs-theme";

export function applyHljsTheme(theme: "dark" | "light") {
  if (typeof document === "undefined") return;

  const href = theme === "dark" ? hljsDarkUrl : hljsLightUrl;
  let link = document.getElementById(LINK_ID) as HTMLLinkElement | null;

  if (!link) {
    link = document.createElement("link");
    link.id = LINK_ID;
    link.rel = "stylesheet";
    document.head.appendChild(link);
  }

  if (link.href !== href) {
    link.href = href;
  }
}
