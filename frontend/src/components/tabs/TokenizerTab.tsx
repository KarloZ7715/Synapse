import { For, Show, createMemo, createResource } from "solid-js";
import { MODEL_ASSETS_SUBPATH, MODEL_MAX_LEN } from "~/config/model";
import type { ConversationStore } from "~/store/conversation";
import { tokenize, type Word2Idx } from "~/utils/tokenizer";

type VocabFile = { word2idx: Record<string, number> };

async function fetchVocab(): Promise<Word2Idx> {
  const base = `${window.location.origin}${import.meta.env.BASE_URL}${MODEL_ASSETS_SUBPATH}`;
  const res = await fetch(`${base}vocab.json`);
  if (!res.ok) throw new Error(`vocab.json: ${res.status}`);
  const data = (await res.json()) as VocabFile;
  return data.word2idx;
}

export function TokenizerTab(props: { convo: ConversationStore }) {
  const [vocab] = createResource<Word2Idx>(fetchVocab);

  const sourceText = createMemo(
    () => props.convo.lastSubmittedText ?? props.convo.draftQuestion ?? "",
  );

  const tokens = createMemo(() => tokenize(sourceText()));

  const tokenIds = createMemo(() => {
    const v = vocab();
    if (!v) return null;
    const unk = v["<unk>"] ?? 1;
    return tokens().map((t) => ({
      token: t,
      id: v[t] ?? unk,
      isUnk: v[t] === undefined,
    }));
  });

  const tokensWithIds = () => tokenIds();
  const vocabSize = () => (vocab() ? Object.keys(vocab() as Word2Idx).length : null);

  return (
    <div class="relative flex flex-1 overflow-y-auto bg-surface">
      <div class="mx-auto flex w-full max-w-[1400px] flex-col gap-margin-md p-margin-md md:p-margin-lg">
        <header class="flex items-end justify-between border-b-2 border-outline-variant pb-margin-sm">
          <div>
            <h2 class="font-display text-[28px] font-bold uppercase tracking-tighter text-on-surface">
              Visualizador de Tokens
            </h2>
            <p class="mt-2 font-mono text-[12px] uppercase text-primary-fixed-dim">
              // TOKEN_STREAM_VIEWER
            </p>
          </div>
          <div class="flex items-center gap-2 border border-outline-variant bg-surface px-3 py-1">
            <span
              class="inline-block h-2 w-2"
              classList={{
                "bg-primary-container": !!vocab(),
                "bg-error animate-pulse": !!vocab.error,
                "bg-on-surface-variant animate-pulse": vocab.loading,
              }}
            />
            <span class="font-mono text-[10px] uppercase text-primary-container">
              {vocab.loading ? "VOCAB.LOADING" : vocab.error ? "VOCAB.ERROR" : "VOCAB.ONLINE"}
            </span>
          </div>
        </header>

        {/* Input display */}
        <section class="border border-outline-variant bg-surface">
          <div class="flex items-center justify-between border-b border-outline-variant bg-surface-container-high p-2">
            <span class="font-mono text-[10px] uppercase text-on-surface-variant">
              STREAM_ENTRADA · {sourceText() ? "RAW" : "EMPTY"}
            </span>
            <span class="font-mono text-[10px] uppercase text-on-surface-variant">ES-ES</span>
          </div>
          <div class="p-6">
            <Show
              when={sourceText().trim()}
              fallback={
                <p class="font-mono text-[12px] uppercase text-on-surface-variant">
                  // Escribe una consulta en la pestaña Input o Classification
                </p>
              }
            >
              <p class="font-display text-[20px] font-bold text-primary md:text-[24px]">
                {sourceText()}
              </p>
            </Show>
          </div>
        </section>

        {/* Token map */}
        <section class="flex flex-col gap-4">
          <h3 class="flex items-center gap-2 font-mono text-[12px] uppercase text-on-surface-variant">
            <span class="material-symbols-outlined text-base">account_tree</span>
            Mapa de Tokenización
            <span class="ml-auto text-primary-container">
              {tokens().length} {tokens().length === 1 ? "token" : "tokens"}
              {tokens().length >= MODEL_MAX_LEN && " (truncado)"}
            </span>
          </h3>

          <Show
            when={tokens().length > 0}
            fallback={
              <div class="border border-dashed border-outline-variant bg-surface p-margin-lg text-center font-mono text-[12px] uppercase text-on-surface-variant">
                // Aún no hay tokens. Escribe una consulta para visualizarlos.
              </div>
            }
          >
            <div class="grid grid-cols-2 gap-1 border border-outline-variant bg-outline-variant p-px md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-7">
              <For each={tokensWithIds() ?? tokens().map((t) => ({ token: t, id: -1, isUnk: false }))}>
                {(tok, i) => <TokenCard token={tok.token} id={tok.id} isUnk={tok.isUnk} index={i()} />}
              </For>
            </div>
          </Show>
        </section>

        {/* Vocab preview */}
        <section class="border border-outline-variant bg-surface">
          <div class="flex items-center justify-between border-b border-outline-variant bg-surface-container-high p-2">
            <span class="font-mono text-[10px] uppercase text-on-surface-variant">
              VOCABULARIO · {vocabSize() ? `${vocabSize()?.toLocaleString()} entradas` : "—"}
            </span>
            <span class="font-mono text-[10px] uppercase text-outline">MUESTRA SEMÁNTICA</span>
          </div>
          <Show
            when={vocab()}
            fallback={
              <p class="p-4 font-mono text-[11px] uppercase text-on-surface-variant">
                {vocab.loading
                  ? "// Cargando vocab.json..."
                  : "// vocab.json no disponible — verifica pnpm sync:model"}
              </p>
            }
          >
            {(v) => (
              <div class="grid max-h-32 grid-cols-2 gap-x-4 gap-y-1 overflow-hidden p-4 font-mono text-[11px] md:grid-cols-4">
                <For each={tokensWithIds() ?? []}>
                  {(t) => (
                    <div class="flex gap-2 text-on-surface-variant">
                      <span class="text-outline">[{t.id}]</span>
                      <span
                        class={t.isUnk ? "text-error" : "text-primary-container font-bold"}
                      >
                        {t.token}
                      </span>
                    </div>
                  )}
                </For>
                <For each={Object.entries(v()).slice(0, 16)}>
                  {([word, id]) => (
                    <Show when={!tokens().includes(word)}>
                      <div class="flex gap-2 text-on-surface-variant opacity-60">
                        <span>[{id}]</span>
                        <span>{word}</span>
                      </div>
                    </Show>
                  )}
                </For>
              </div>
            )}
          </Show>
        </section>

        {/* Tokenizer metrics */}
        <section class="grid grid-cols-1 gap-3 md:grid-cols-3">
          <MetricCell
            label="Conteo de tokens"
            value={tokens().length.toString()}
            accent={tokens().length > 0 ? "primary" : "muted"}
          />
          <MetricCell label="Codificación" value="UTF-8" accent="muted" />
          <MetricCell label="Max length" value={MODEL_MAX_LEN.toString()} accent="muted" />
        </section>
      </div>
    </div>
  );
}

function TokenCard(props: { token: string; id: number; isUnk: boolean; index: number }) {
  const isHighlight = props.index === 0 || props.isUnk;
  return (
    <article
      class={`relative flex min-h-[120px] cursor-crosshair flex-col justify-between p-4 transition-colors ${
        isHighlight
          ? props.isUnk
            ? "border border-error bg-error/10"
            : "border border-primary-container bg-surface-container-highest"
          : "bg-surface hover:bg-surface-container-high"
      }`}
    >
      <div class="flex w-full items-start justify-between">
        <span
          class={`font-mono text-[10px] ${props.isUnk ? "text-error font-bold" : props.id < 0 ? "text-on-surface-variant" : "text-on-surface-variant"}`}
        >
          ID: {props.id >= 0 ? props.id : "—"}
        </span>
        <span class="font-mono text-[10px] text-outline">
          [{props.isUnk ? "UNK" : "WORD"}]
        </span>
      </div>
      <div
        class={`mt-2 break-all font-display text-[20px] font-bold ${
          props.isUnk ? "text-error" : "text-on-surface"
        }`}
      >
        {props.token}
      </div>
      <div class="mt-4 font-mono text-[10px] text-on-surface-variant">
        {props.isUnk ? "fuera de vocab" : "en vocab"}
      </div>
    </article>
  );
}

function MetricCell(props: { label: string; value: string; accent: "primary" | "muted" }) {
  const valueCls =
    props.accent === "primary" ? "text-primary-container" : "text-on-surface";
  return (
    <div class="border border-outline-variant bg-surface-container-lowest p-4">
      <div class="font-mono text-[10px] uppercase text-on-surface-variant">{props.label}</div>
      <div class={`mt-2 font-display text-[28px] font-bold ${valueCls}`}>{props.value}</div>
    </div>
  );
}
