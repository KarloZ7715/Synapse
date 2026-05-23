import { Show, createMemo } from "solid-js";
import { renderMarkdownToHtml } from "~/lib/markdown";

export function MarkdownContent(props: {
  source: string;
  streaming?: boolean;
  class?: string;
}) {
  const html = createMemo(() => renderMarkdownToHtml(props.source, props.streaming));

  return (
    <div class={`markdown-content ${props.class ?? ""}`.trim()}>
      <div innerHTML={html()} />
      <Show when={props.streaming}>
        <span class="markdown-stream-cursor animate-pulse text-primary-fixed" aria-hidden="true">
          █
        </span>
      </Show>
    </div>
  );
}
