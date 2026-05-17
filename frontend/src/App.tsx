import { Show } from "solid-js";
import { ChatPanel } from "~/components/ChatPanel";
import { DiagnosticPanel } from "~/components/DiagnosticPanel";
import { PipelinePanel } from "~/components/PipelinePanel";
import { AppLayout } from "~/components/layout/AppLayout";
import { useBreakpoint } from "~/hooks/useBreakpoint";
import { useClassifier } from "~/hooks/useClassifier";
import { createConversationStore } from "~/store/conversation";

export default function App() {
  const classifier = useClassifier();
  const { state, setState } = createConversationStore();
  const isMobile = useBreakpoint(768);

  const onClassify = async () => {
    const text = state.draftQuestion.trim();
    if (!text) {
      return;
    }
    try {
      const r = await classifier.classify(text);
      setState("lastResult", r);
    } catch (e) {
      console.error(e);
    }
  };

  const busy = () =>
    classifier.status() === "loading_model" || classifier.status() === "classifying";

  return (
    <AppLayout>
      {/* Panel A - Pipeline (hidden on mobile) */}
      <Show when={!isMobile()}>
        <PipelinePanel status={classifier.status()} />
      </Show>

      {/* Panel B - Chat */}
      <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <ChatPanel
          state={state}
          setState={setState}
          disabled={busy() || classifier.status() === "error"}
          onClassify={onClassify}
        />
        <Show when={state.lastResult}>
          {(r) => (
            <pre class="font-mono-ui max-h-40 shrink-0 overflow-auto rounded-lg border border-[var(--border-color)] bg-[var(--bg-base)] p-3 text-[11px] text-[var(--text-secondary)]">
              {JSON.stringify(r().metadata, null, 2)}
            </pre>
          )}
        </Show>
      </div>

      {/* Panel C - Diagnóstico (hidden on mobile) */}
      <Show when={!isMobile()}>
        <DiagnosticPanel
          status={classifier.status()}
          result={state.lastResult}
          loadMs={classifier.loadMs()}
          error={classifier.error()}
        />
      </Show>
    </AppLayout>
  );
}
