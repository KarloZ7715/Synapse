import { Show, createMemo } from "solid-js";
import { useTheme } from "~/hooks/useTheme";
import { renderMarkdownToHtml } from "~/lib/markdown";

export function MarkdownContent(props: {
  source: string;
  streaming?: boolean;
  class?: string;
}) {
  const { theme } = useTheme();
  const html = createMemo(() => {
    theme();
    return renderMarkdownToHtml(props.source, props.streaming);
  });

  return (
    <div
      class={`markdown-content ${props.class ?? ""}`.trim()}
      data-markdown-theme={theme()}
    >
      <div innerHTML={html()} />
      <Show when={props.streaming}>
        <span class="markdown-stream-cursor animate-pulse text-primary-fixed" aria-hidden="true">
          █
        </span>
      </Show>
    </div>
  );
}
