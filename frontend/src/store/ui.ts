import { createStore } from "solid-js/store";

export type PipelineTab =
  | "input"
  | "tokenizer"
  | "neural-network"
  | "classification"
  | "prompt"
  | "llm";

export type UIStore = {
  activeTab: PipelineTab;
  terminalOpen: boolean;
};

export function createUIStore() {
  const [state, setState] = createStore<UIStore>({
    activeTab: "classification",
    terminalOpen: false,
  });
  return { state, setState } as const;
}
