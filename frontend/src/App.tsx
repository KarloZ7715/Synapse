import { Show, onCleanup } from "solid-js";
import { AppHeader } from "~/components/layout/AppHeader";
import { AppLayout } from "~/components/layout/AppLayout";
import { MobileTabBar } from "~/components/layout/MobileTabBar";
import { PipelineNav } from "~/components/layout/PipelineNav";
import { ClassificationTab } from "~/components/tabs/ClassificationTab";
import { InputTab } from "~/components/tabs/InputTab";
import { LLMTab } from "~/components/tabs/LLMTab";
import { NeuralKernelTerminal } from "~/components/tabs/NeuralKernelTerminal";
import { NeuralNetworkTab } from "~/components/tabs/NeuralNetworkTab";
import { PromptTab } from "~/components/tabs/PromptTab";
import { TokenizerTab } from "~/components/tabs/TokenizerTab";
import { useBreakpoint } from "~/hooks/useBreakpoint";
import { useClassifier } from "~/hooks/useClassifier";
import { buildHistorial } from "~/lib/buildHistorial";
import { streamChat } from "~/lib/chatStream";
import { scheduleStreamingUpdate } from "~/lib/scheduleUpdate";
import {
  type ConversationTurn,
  type LlmState,
  createConversationStore,
  createEmptyLlmState,
} from "~/store/conversation";
import { createUIStore } from "~/store/ui";
import type { ChatOptions, HeadConfidences } from "~/types/chat";
import type { ClassificationMetadata } from "~/types/classifier";

const DEFAULT_LLM_OPTIONS: ChatOptions = {
  model_id: "llama-3.1-8b-instant",
  temperature: 0.7,
  top_p: 0.9,
  max_tokens: 1024,
};

export default function App() {
  const classifier = useClassifier();
  const { state: convo, setState: setConvo } = createConversationStore();
  const ui = createUIStore();
  const isMobile = useBreakpoint(768);
  let activeChatRun: { controller: AbortController; turnId: string } | null = null;

  onCleanup(() => activeChatRun?.controller.abort());

  const makeTurnId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

  const findTurnIndex = (turnId: string) => convo.turns.findIndex((turn) => turn.id === turnId);

  const replaceTurnLlm = (turnId: string, llm: LlmState) => {
    const turnIndex = findTurnIndex(turnId);
    if (turnIndex >= 0) {
      setConvo("turns", turnIndex, "llm", llm);
    }
  };

  const patchTurnLlm = <K extends keyof LlmState>(
    turnId: string,
    key: K,
    value: LlmState[K] | ((current: LlmState[K]) => LlmState[K]),
  ) => {
    const turnIndex = findTurnIndex(turnId);
    if (turnIndex < 0) return;
    if (typeof value === "function") {
      setConvo("turns", turnIndex, "llm", key, value as (current: LlmState[K]) => LlmState[K]);
      return;
    }
    setConvo("turns", turnIndex, "llm", key, value);
  };

  const setTurnClassification = (
    turnId: string,
    classification: ConversationTurn["classification"],
  ) => {
    const turnIndex = findTurnIndex(turnId);
    if (turnIndex >= 0) {
      setConvo("turns", turnIndex, "classification", classification);
    }
  };

  const stopActiveChat = () => {
    if (!activeChatRun) return;
    activeChatRun.controller.abort();
    const turnIndex = findTurnIndex(activeChatRun.turnId);
    if (turnIndex >= 0 && convo.turns[turnIndex]?.llm.status === "streaming") {
      const hasPartialResponse = Boolean(convo.turns[turnIndex]?.llm.response);
      setConvo("turns", turnIndex, "llm", "status", hasPartialResponse ? "done" : "error");
      if (!hasPartialResponse) {
        setConvo(
          "turns",
          turnIndex,
          "llm",
          "error",
          "Respuesta interrumpida por una nueva consulta.",
        );
      }
    }
    activeChatRun = null;
  };

  const runLlm = async (
    turnId: string,
    pregunta: string,
    metadata: ClassificationMetadata,
    options: ChatOptions,
    headConfidences?: HeadConfidences,
  ) => {
    stopActiveChat();
    const controller = new AbortController();
    activeChatRun = { controller, turnId };

    const nextLlmState = { ...createEmptyLlmState(), status: "streaming" as const };
    setConvo("llm", nextLlmState);
    replaceTurnLlm(turnId, nextLlmState);

    try {
      const chatRequest = {
        pregunta,
        metadata,
        historial: buildHistorial(convo.turns, turnId),
        options,
        ...(headConfidences !== undefined ? { head_confidences: headConfidences } : {}),
      };
      await streamChat(
        chatRequest,
        {
          onToken: (token) => {
            scheduleStreamingUpdate(() => {
              setConvo("llm", "response", (current) => `${current}${token}`);
              patchTurnLlm(turnId, "response", (current) => `${current}${token}`);
            });
          },
          onUsage: (usage) => {
            setConvo("llm", "usage", usage);
            patchTurnLlm(turnId, "usage", usage);
          },
        },
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setConvo("llm", "status", "done");
        patchTurnLlm(turnId, "status", "done");
      }
    } catch (e) {
      if (controller.signal.aborted) {
        return;
      }
      const message = e instanceof Error ? e.message : String(e);
      setConvo("llm", "status", "error");
      setConvo("llm", "error", message);
      patchTurnLlm(turnId, "status", "error");
      patchTurnLlm(turnId, "error", message);
    } finally {
      if (activeChatRun?.controller === controller) {
        activeChatRun = null;
      }
    }
  };

  const onClassify = async () => {
    const text = convo.draftQuestion.trim();
    if (!text) return;
    stopActiveChat();
    const turnId = makeTurnId();
    setConvo("lastSubmittedText", text);
    setConvo("draftQuestion", "");
    setConvo("lastResult", null);
    setConvo("llm", createEmptyLlmState());
    setConvo("turns", (turns) => [
      ...turns,
      {
        id: turnId,
        submittedText: text,
        classification: {
          status: "pending",
          result: null,
          error: null,
        },
        llm: createEmptyLlmState(),
      },
    ]);
    try {
      const r = await classifier.classify(text);
      setConvo("lastResult", r);
      setTurnClassification(turnId, {
        status: "done",
        result: r,
        error: null,
      });
      await runLlm(turnId, text, r.metadata, DEFAULT_LLM_OPTIONS, r.headConfidences);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setTurnClassification(turnId, {
        status: "error",
        result: null,
        error: message,
      });
      console.error(e);
    }
  };

  const onRunLlm = async (options: ChatOptions) => {
    const pregunta = convo.lastSubmittedText?.trim();
    const metadata = convo.lastResult?.metadata;
    const currentTurnId = convo.turns[convo.turns.length - 1]?.id;
    if (!pregunta || !metadata) {
      setConvo("llm", {
        status: "error",
        response: "",
        usage: null,
        error: "Primero clasifica una consulta antes de invocar el LLM.",
      });
      return;
    }

    if (!currentTurnId) {
      return;
    }

    const headConfidences = convo.lastResult?.headConfidences;
    await runLlm(currentTurnId, pregunta, metadata, options, headConfidences);
  };

  const busy = () =>
    classifier.status() === "loading_model" || classifier.status() === "classifying";

  return (
    <AppLayout
      header={
        <AppHeader
          status={classifier.status()}
          loadMs={classifier.loadMs()}
          inferenceMs={convo.lastResult?.inferenceMs ?? null}
          backend={convo.lastResult?.ortBackend ?? classifier.ortBackend() ?? null}
          onToggleTerminal={() => ui.setState("terminalOpen", (v) => !v)}
        />
      }
      nav={
        <Show when={!isMobile()}>
          <PipelineNav
            active={ui.state.activeTab}
            onSelect={(t) => ui.setState("activeTab", t)}
            status={classifier.status()}
          />
        </Show>
      }
    >
      <Show when={isMobile()}>
        <MobileTabBar active={ui.state.activeTab} onSelect={(t) => ui.setState("activeTab", t)} />
      </Show>
      <Show when={ui.state.activeTab === "classification"}>
        <ClassificationTab
          classifier={classifier}
          convo={convo}
          setConvo={setConvo}
          onClassify={onClassify}
          busy={busy()}
          isMobile={isMobile()}
        />
      </Show>
      <Show when={ui.state.activeTab === "input"}>
        <InputTab
          convo={convo}
          setConvo={setConvo}
          onClassify={onClassify}
          setActiveTab={(t) => ui.setState("activeTab", t)}
          disabled={busy() || classifier.status() === "error"}
        />
      </Show>
      <Show when={ui.state.activeTab === "tokenizer"}>
        <TokenizerTab convo={convo} />
      </Show>
      <Show when={ui.state.activeTab === "neural-network"}>
        <NeuralNetworkTab classifier={classifier} convo={convo} />
      </Show>
      <Show when={ui.state.activeTab === "prompt"}>
        <PromptTab convo={convo} />
      </Show>
      <Show when={ui.state.activeTab === "llm"}>
        <LLMTab convo={convo} onRun={onRunLlm} />
      </Show>

      <Show when={ui.state.terminalOpen}>
        <NeuralKernelTerminal
          classifier={classifier}
          convo={convo}
          onClose={() => ui.setState("terminalOpen", false)}
        />
      </Show>
    </AppLayout>
  );
}
