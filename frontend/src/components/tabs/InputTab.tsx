import { Show } from "solid-js";
import type { SetStoreFunction } from "solid-js/store";
import type { ConversationStore } from "~/store/conversation";
import type { PipelineTab } from "~/store/ui";

export function InputTab(props: {
  convo: ConversationStore;
  setConvo: SetStoreFunction<ConversationStore>;
  onClassify: () => void | Promise<void>;
  setActiveTab: (tab: PipelineTab) => void;
  disabled: boolean;
}) {
  const handleSubmit = async () => {
    await props.onClassify();
    props.setActiveTab("classification");
  };
  const charCount = () => props.convo.draftQuestion.length;

  return (
    <div class="relative flex flex-1 overflow-y-auto bg-surface">
      <div class="mx-auto flex w-full max-w-300 flex-col gap-margin-md p-margin-md md:p-margin-lg">
        <header class="flex items-end justify-between border-b border-outline-variant pb-margin-sm">
          <div>
            <h2 class="font-display text-[28px] font-bold uppercase tracking-tighter text-on-surface">
              Gestión de Entrada
            </h2>
            <p class="mt-2 font-mono text-[12px] uppercase text-primary-fixed-dim">
              // INGESTION_CONTROL_CENTER
            </p>
          </div>
          <div class="hidden gap-3 md:flex">
            <span class="border border-primary-container bg-primary-container px-3 py-1 font-mono text-[10px] uppercase text-on-primary-container">
              STATUS: ACTIVE
            </span>
            <span class="border border-outline-variant bg-surface-container-highest px-3 py-1 font-mono text-[10px] uppercase text-on-surface-variant">
              SOURCE: BROWSER
            </span>
          </div>
        </header>

        <div class="grid flex-1 grid-cols-1 gap-margin-md lg:grid-cols-12">
          {/* Left: Methods + Privacy */}
          <div class="flex flex-col gap-margin-sm lg:col-span-4">
            <h3 class="mb-2 flex justify-between border-b border-outline-variant pb-2 font-mono text-[12px] uppercase text-on-surface-variant">
              <span>Método de Ingesta</span>
              <span class="material-symbols-outlined text-sm text-primary-fixed-dim">
                settings_input_component
              </span>
            </h3>

            <MethodCard
              active
              icon="code"
              title="Pegado manual"
              subtitle="Ingreso directo por consola del navegador"
            />

            <h3 class="mb-2 mt-margin-md flex justify-between border-b border-outline-variant pb-2 font-mono text-[12px] uppercase text-on-surface-variant">
              <span>Configuración de Privacidad</span>
              <span class="material-symbols-outlined text-sm text-primary-fixed-dim">security</span>
            </h3>
            <div class="flex flex-col gap-4 border border-outline-variant bg-surface-container-lowest p-margin-sm">
              <PrivacyToggle
                title="Inferencia Local Solamente"
                subtitle="El clasificador corre en el navegador, sin enviar texto a la red"
                on
                locked
              />
              <div class="h-px w-full bg-outline-variant" />
              <PrivacyToggle
                title="Sin registro de sesión"
                subtitle="Las consultas no se guardan entre sesiones"
                on
                locked
              />
            </div>
          </div>

          {/* Right: Editor */}
          <div class="flex min-h-125 flex-col lg:col-span-8">
            <div class="relative flex items-center justify-between border border-b-0 border-outline-variant bg-surface-container-highest px-margin-sm py-2">
              <h3 class="font-mono text-[12px] uppercase text-on-surface">
                Configuración de Fuente
              </h3>
              <div class="flex gap-2">
                <span class="border border-outline-variant bg-surface px-2 font-mono text-[10px] text-on-surface-variant">
                  RAW
                </span>
                <span class="border border-primary-fixed-dim bg-surface px-2 font-mono text-[10px] text-primary-fixed-dim">
                  ACTIVE
                </span>
              </div>
            </div>

            <div class="group relative flex grow overflow-hidden border border-outline-variant bg-[#050505]">
              <textarea
                class="grow resize-none bg-transparent p-margin-sm font-mono text-[13px] text-on-surface focus:outline-none focus:ring-0"
                placeholder="// Ingresa tu duda de programación aquí. Se enviará al submodelo TextCNN local."
                value={props.convo.draftQuestion}
                disabled={props.disabled}
                onInput={(e) => props.setConvo("draftQuestion", e.currentTarget.value)}
              />
            </div>

            <div class="flex items-center justify-between border border-t-0 border-outline-variant bg-surface-container-lowest p-margin-sm">
              <div class="flex items-center gap-2 text-primary-fixed-dim">
                <span class="material-symbols-outlined text-sm">memory</span>
                <span class="font-mono text-[11px] uppercase">
                  <Show
                    when={props.disabled}
                    fallback={`${charCount()} CHARS · LISTO PARA INFERENCIA`}
                  >
                    MODELO OCUPADO...
                  </Show>
                </span>
              </div>
              <div class="flex gap-3">
                <button
                  type="button"
                  class="border border-outline-variant bg-surface px-6 py-2 font-mono text-[12px] uppercase text-on-surface transition-colors hover:bg-surface-container-highest"
                  onClick={() => props.setConvo("draftQuestion", "")}
                  disabled={props.disabled || !props.convo.draftQuestion}
                >
                  CANCELAR
                </button>
                <button
                  type="button"
                  class="flex items-center gap-2 border border-on-surface bg-on-surface px-6 py-2 font-mono text-[12px] uppercase text-surface transition-colors hover:border-primary-container hover:bg-primary-container hover:text-on-primary-container disabled:cursor-not-allowed disabled:opacity-30"
                  onClick={() => void handleSubmit()}
                  disabled={props.disabled || !props.convo.draftQuestion.trim()}
                >
                  <span class="material-symbols-outlined text-sm">send</span>
                  INICIAR INGESTA
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MethodCard(props: {
  active?: boolean;
  disabled?: boolean;
  icon: string;
  title: string;
  subtitle: string;
}) {
  const borderCls = () =>
    props.active
      ? "border-primary-fixed"
      : props.disabled
        ? "border-outline-variant opacity-50"
        : "border-outline-variant hover:border-primary-fixed-dim";
  return (
    <div
      class={`relative border bg-surface-container-lowest p-margin-sm ${borderCls()} ${props.disabled ? "cursor-not-allowed" : "cursor-pointer"}`}
    >
      <Show when={props.active}>
        <div class="absolute left-0 top-0 text-xs leading-none text-primary-fixed">+</div>
        <div class="absolute right-0 top-0 text-xs leading-none text-primary-fixed">+</div>
        <div class="absolute bottom-0 left-0 text-xs leading-none text-primary-fixed">+</div>
        <div class="absolute bottom-0 right-0 text-xs leading-none text-primary-fixed">+</div>
      </Show>
      <div class="flex items-start gap-4">
        <div
          class={`border p-2 ${props.active ? "border-primary-fixed bg-primary-container text-on-primary-container" : "border-outline-variant bg-surface-container-highest text-on-surface-variant"}`}
        >
          <span class="material-symbols-outlined">
            {props.icon}
          </span>
        </div>
        <div>
          <h4
            class={`font-mono text-[12px] uppercase ${props.active ? "text-primary-fixed" : "text-on-surface"}`}
          >
            {props.title}
          </h4>
          <p class="mt-1 font-mono text-[11px] text-on-surface-variant">{props.subtitle}</p>
        </div>
      </div>
    </div>
  );
}

function PrivacyToggle(props: {
  title: string;
  subtitle: string;
  on: boolean;
  locked?: boolean;
}) {
  return (
    <div class="flex items-start justify-between gap-3">
      <div>
        <h4 class="font-mono text-[12px] uppercase text-on-surface">{props.title}</h4>
        <p class="font-mono text-[11px] text-on-surface-variant">{props.subtitle}</p>
      </div>
      <div
        class={`flex h-6 w-12 items-center p-1 ${props.on ? "border border-primary-fixed bg-surface-container-highest" : "border border-outline-variant bg-surface"}`}
        title={props.locked ? "Configuración fija del laboratorio" : ""}
      >
        <div class={`h-4 w-4 ${props.on ? "ml-auto bg-primary-container" : "bg-on-surface-variant"}`} />
      </div>
    </div>
  );
}
