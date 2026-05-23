import { Show } from "solid-js";
import type { SetStoreFunction } from "solid-js/store";
import type { ConversationStore } from "~/store/conversation";
import type { ClassificationResult, ClassifierStatus } from "~/types/classifier";
import { CommandInput } from "./classification/CommandInput";
import { DiagnosticsHUD } from "./classification/DiagnosticsHUD";
import { Transcript } from "./classification/Transcript";

type Classifier = {
  status: () => ClassifierStatus;
  error: () => string | null;
  result: () => ClassificationResult | null;
  loadMs: () => number | null;
  classify: (text: string) => Promise<ClassificationResult>;
};

export function ClassificationTab(props: {
  classifier: Classifier;
  convo: ConversationStore;
  setConvo: SetStoreFunction<ConversationStore>;
  onClassify: () => void | Promise<void>;
  busy: boolean;
  isMobile: boolean;
}) {
  return (
    <div class="flex min-h-0 min-w-0 flex-1 overflow-hidden">
      <section class="relative flex min-h-0 min-w-0 flex-1 flex-col bg-surface/90">
        <Transcript status={props.classifier.status()} convo={props.convo} />
        <CommandInput
          value={props.convo.draftQuestion}
          onChange={(v) => props.setConvo("draftQuestion", v)}
          onSubmit={() => void props.onClassify()}
          disabled={props.busy || props.classifier.status() === "error"}
          lastResult={props.convo.lastResult}
        />
      </section>
      <Show when={!props.isMobile}>
        <DiagnosticsHUD
          status={props.classifier.status()}
          result={props.convo.lastResult}
          loadMs={props.classifier.loadMs()}
          error={props.classifier.error()}
        />
      </Show>
    </div>
  );
}
