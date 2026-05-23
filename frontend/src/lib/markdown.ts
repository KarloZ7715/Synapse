import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import cpp from "highlight.js/lib/languages/cpp";
import css from "highlight.js/lib/languages/css";
import java from "highlight.js/lib/languages/java";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import python from "highlight.js/lib/languages/python";
import sql from "highlight.js/lib/languages/sql";
import typescript from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";
import { marked } from "marked";

const LANGUAGE_ALIASES: Record<string, string> = {
  js: "javascript",
  ts: "typescript",
  py: "python",
  sh: "bash",
  shell: "bash",
  md: "markdown",
  html: "xml",
};

hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("java", java);
hljs.registerLanguage("cpp", cpp);
hljs.registerLanguage("sql", sql);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("css", css);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);

marked.setOptions({
  gfm: true,
  breaks: true,
});

marked.use({
  renderer: {
    code({ text, lang }) {
      const normalized = normalizeLanguage(lang);
      const highlighted = highlightCode(text, normalized);
      const languageClass = normalized ? `language-${normalized}` : "";
      return `<pre class="hljs-block"><code class="hljs ${languageClass}">${highlighted}</code></pre>`;
    },
  },
});

function normalizeLanguage(lang?: string | null): string | undefined {
  if (!lang) return undefined;
  const trimmed = lang.trim().toLowerCase();
  if (!trimmed) return undefined;
  const alias = LANGUAGE_ALIASES[trimmed] ?? trimmed;
  return hljs.getLanguage(alias) ? alias : undefined;
}

function highlightCode(text: string, lang?: string): string {
  if (lang) {
    return hljs.highlight(text, { language: lang }).value;
  }
  return hljs.highlightAuto(text).value;
}

/** Cierra fences abiertos para que el markdown parcial durante streaming sea legible. */
export function stabilizeStreamingMarkdown(source: string): string {
  const fenceCount = (source.match(/```/g) ?? []).length;
  if (fenceCount % 2 === 1) {
    return `${source}\n\`\`\``;
  }
  return source;
}

export function renderMarkdownToHtml(source: string, streaming = false): string {
  const input = streaming ? stabilizeStreamingMarkdown(source) : source;
  const raw = marked.parse(input, { async: false }) as string;
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ["target", "rel"],
  });
}
