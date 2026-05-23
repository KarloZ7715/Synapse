import { For, Show } from "solid-js";
import { MarkdownContent } from "~/components/markdown/MarkdownContent";
import type { ConversationTurn, LlmState } from "~/store/conversation";
import type { ClassificationResult, ClassifierStatus } from "~/types/classifier";

export function Transcript(props: {
  status: ClassifierStatus;
  turns: ConversationTurn[];
}) {
  return (
    <div class="relative z-10 flex flex-1 flex-col gap-6 overflow-y-auto p-8">
      <Show when={props.turns.length > 0} fallback={<EmptyState status={props.status} />}>
        <For each={props.turns}>
          {(turn) => (
            <>
              <UserBubble text={turn.submittedText} />
              <Show when={turn.classification.status === "done" && turn.classification.result}>
                {(result) => <ClassifierBubble result={result()} />}
              </Show>
              <Show when={turn.classification.status === "pending"}>
                <ClassifierPendingBubble />
              </Show>
              <Show when={turn.classification.status === "error" && turn.classification.error}>
                {(error) => <ClassifierErrorBubble error={error()} />}
              </Show>
              <Show when={turn.llm.status !== "idle" || turn.llm.response || turn.llm.error}>
                <LlmBubble llm={turn.llm} />
              </Show>
            </>
          )}
        </For>
      </Show>
    </div>
  );
}

function EmptyState(props: { status: ClassifierStatus }) {
  const hint = () => {
    if (props.status === "loading_model") return "Cargando modelo TextCNN local...";
    if (props.status === "error") return "El clasificador no pudo iniciarse.";
    if (props.status === "classifying") return "Procesando consulta...";
    return "Escribe una duda de programación abajo para que el modelo local la clasifique.";
  };
  return (
    <div class="m-auto flex max-w-xl flex-col items-center gap-4 text-center">
      <div class="flex h-20 w-20 items-center justify-center border-2 border-primary-fixed bg-surface-container shadow-[0_0_24px_rgba(57,255,20,0.2)]">
        <span class="material-symbols-outlined text-4xl text-primary-fixed">psychology</span>
      </div>
      <div>
        <h2 class="font-display text-[24px] font-bold uppercase tracking-tighter text-on-surface">
          SYNAPSE listo
        </h2>
        <p class="mt-2 font-mono text-[12px] uppercase tracking-wider text-on-surface-variant">
          {hint()}
        </p>
      </div>
    </div>
  );
}

function UserBubble(props: { text: string }) {
  return (
    <div class="flex max-w-2xl items-start gap-4 self-end">
      <div class="relative flex-1 border border-outline-variant bg-surface-container p-4 font-mono text-[13px] text-on-surface">
        <div class="absolute right-0 top-0 border-b border-l border-outline-variant bg-surface-variant p-1 font-mono text-[10px] uppercase text-on-surface-variant">
          USER_QUERY
        </div>
        <p class="mt-3 whitespace-pre-wrap">{props.text}</p>
      </div>
      <div class="flex h-10 w-10 shrink-0 items-center justify-center border border-outline bg-surface-variant">
        <span class="material-symbols-outlined text-on-surface-variant">person</span>
      </div>
    </div>
  );
}

function ClassifierBubble(props: { result: ClassificationResult }) {
  const m = props.result.metadata;
  const confidencePct = () => Math.round(m.confianza * 100);
  return (
    <div class="flex w-full max-w-3xl items-start gap-4 self-start">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center border border-primary-fixed bg-primary-fixed/20 shadow-[0_0_10px_var(--color-primary-fixed)]">
        <span class="material-symbols-outlined text-primary-fixed">smart_toy</span>
      </div>
      <div class="neon-glow-primary relative flex-1 bg-surface-container-high/80 p-4 font-mono text-[13px] text-on-surface backdrop-blur-md">
        <div class="absolute left-0 top-0 border-b border-r border-primary-fixed/50 bg-primary-fixed/20 p-1 font-mono text-[10px] uppercase text-primary-fixed">
          CLASSIFIER_OUTPUT
        </div>
        <div class="mt-4 space-y-3">
          <p class="text-on-surface-variant">
            Submodelo local clasificó la consulta. Metadata lista para construir el prompt y enviar
            la petición al LLM.
          </p>
          <dl class="grid grid-cols-2 gap-x-4 gap-y-2 border border-outline-variant bg-surface-container-lowest p-3">
            <dt class="text-on-surface-variant">nivel</dt>
            <dd class="uppercase text-primary-fixed">{m.nivel_tecnico}</dd>
            <dt class="text-on-surface-variant">urgencia</dt>
            <dd class="uppercase text-primary-fixed">{m.urgencia}</dd>
            <dt class="text-on-surface-variant">emoción</dt>
            <dd class="uppercase text-primary-fixed">{m.emocion}</dd>
            <dt class="text-on-surface-variant">dominio</dt>
            <dd class="uppercase text-primary-fixed">{m.dominio}</dd>
          </dl>
          <div class="flex items-center justify-between border-t border-outline-variant pt-2 text-[11px]">
            <span class="text-on-surface-variant">CONFIANZA</span>
            <span class="font-bold text-primary-fixed">{confidencePct()}%</span>
          </div>
          <div class="flex items-center justify-between text-[11px]">
            <span class="text-on-surface-variant">INFERENCE</span>
            <span class="text-secondary-fixed">
              {Math.round(props.result.inferenceMs)}ms · {props.result.ortBackend.toUpperCase()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ClassifierPendingBubble() {
  return (
    <div class="flex w-full max-w-3xl items-start gap-4 self-start">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center border border-primary-fixed bg-primary-fixed/10 shadow-[0_0_10px_var(--color-primary-fixed)]">
        <span class="material-symbols-outlined animate-pulse text-primary-fixed">smart_toy</span>
      </div>
      <div class="relative flex-1 border border-primary-fixed/30 bg-surface-container-high/80 p-4 font-mono text-[13px] text-on-surface backdrop-blur-md">
        <div class="absolute left-0 top-0 border-b border-r border-primary-fixed/40 bg-primary-fixed/10 p-1 font-mono text-[10px] uppercase text-primary-fixed">
          CLASSIFIER_OUTPUT · PENDING
        </div>
        <div class="mt-4 text-on-surface-variant">
          Analizando nivel, urgencia, emoción y dominio para esta consulta...
        </div>
      </div>
    </div>
  );
}

function ClassifierErrorBubble(props: { error: string }) {
  return (
    <div class="flex w-full max-w-3xl items-start gap-4 self-start">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center border border-error bg-error/10 shadow-[0_0_10px_var(--color-error)]">
        <span class="material-symbols-outlined text-error">error</span>
      </div>
      <div class="relative flex-1 border border-error/40 bg-error/10 p-4 font-mono text-[13px] text-error backdrop-blur-md">
        <div class="absolute left-0 top-0 border-b border-r border-error/40 bg-error/10 p-1 font-mono text-[10px] uppercase text-error">
          CLASSIFIER_OUTPUT · ERROR
        </div>
        <div class="mt-4">{props.error}</div>
      </div>
    </div>
  );
}

function LlmBubble(props: { llm: LlmState }) {
  const statusLabel = () => {
    if (props.llm.status === "streaming") return "STREAMING";
    if (props.llm.status === "done") return "DONE";
    if (props.llm.status === "error") return "ERROR";
    return "IDLE";
  };

  return (
    <div class="flex w-full max-w-4xl items-start gap-4 self-start">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center border border-secondary-fixed bg-secondary-fixed/20 shadow-[0_0_10px_var(--color-secondary-fixed)]">
        <span class="material-symbols-outlined text-secondary-fixed">forum</span>
      </div>
      <div class="relative flex-1 border border-secondary-fixed/40 bg-surface-container-high/90 p-4 font-mono text-[13px] text-on-surface backdrop-blur-md">
        <div class="absolute left-0 top-0 border-b border-r border-secondary-fixed/40 bg-secondary-fixed/10 p-1 font-mono text-[10px] uppercase text-secondary-fixed">
          PERSONALIZED_OUTPUT · {statusLabel()}
        </div>
        <div class="mt-4 space-y-3">
          <p class="text-on-surface-variant">
            Respuesta generada por el LLM a partir de los metadatos inferidos por la red neuronal.
          </p>
          <Show when={props.llm.error}>
            {(error) => (
              <div class="border border-error/40 bg-error/10 p-3 text-error">{error()}</div>
            )}
          </Show>
          <div class="border border-outline-variant bg-surface-container-lowest p-3">
            <Show
              when={props.llm.response}
              fallback={
                <span class="text-on-surface-variant">Esperando tokens del backend...</span>
              }
            >
              <MarkdownContent
                source={props.llm.response}
                streaming={props.llm.status === "streaming"}
              />
            </Show>
          </div>
          <Show when={props.llm.usage}>
            {(usage) => (
              <div class="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-outline-variant pt-2 text-[11px] md:grid-cols-4">
                <div>
                  <div class="text-on-surface-variant">PROVEEDOR</div>
                  <div class="uppercase text-secondary-fixed">{usage().provider}</div>
                </div>
                <div>
                  <div class="text-on-surface-variant">TOKENS IN</div>
                  <div class="text-secondary-fixed">{usage().tokens_input}</div>
                </div>
                <div>
                  <div class="text-on-surface-variant">TOKENS OUT</div>
                  <div class="text-secondary-fixed">{usage().tokens_output}</div>
                </div>
                <div>
                  <div class="text-on-surface-variant">LATENCIA</div>
                  <div class="text-secondary-fixed">{usage().latency_ms}ms</div>
                </div>
              </div>
            )}
          </Show>
        </div>
      </div>
    </div>
  );
}
