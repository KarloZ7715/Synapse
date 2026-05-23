import { describe, expect, it } from "vitest";
import { renderMarkdownToHtml, stabilizeStreamingMarkdown } from "~/lib/markdown";

describe("stabilizeStreamingMarkdown", () => {
  it("cierra un fence abierto", () => {
    const input = "Texto\n```python\nprint('hola')";
    expect(stabilizeStreamingMarkdown(input)).toBe(`${input}\n\`\`\``);
  });

  it("no modifica fences balanceados", () => {
    const input = "```js\nconst x = 1;\n```";
    expect(stabilizeStreamingMarkdown(input)).toBe(input);
  });
});

describe("renderMarkdownToHtml", () => {
  it("renderiza encabezados, listas y tablas", () => {
    const html = renderMarkdownToHtml(
      "## Titulo\n\n- item\n\n| col | val |\n| --- | --- |\n| a | 1 |",
    );
    expect(html).toContain("<h2");
    expect(html).toContain("<ul");
    expect(html).toContain("<table");
    expect(html).toContain("<td");
  });

  it("resalta bloques de codigo", () => {
    const html = renderMarkdownToHtml("```python\nprint('ok')\n```");
    expect(html).toContain("<pre");
    expect(html).toContain("hljs");
    expect(html).toContain("print");
  });

  it("elimina scripts maliciosos", () => {
    const html = renderMarkdownToHtml('<script>alert("x")</script>\n\nTexto seguro');
    expect(html).not.toContain("<script");
    expect(html).toContain("Texto seguro");
  });
});
