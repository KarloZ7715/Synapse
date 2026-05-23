import prompts from "./examplePrompts.json";

/** Umbral mínimo de confianza geométrica validada contra el ONNX local. */
export const EXAMPLE_PROMPT_MIN_CONFIDENCE = 0.88;

export type ExamplePrompt = {
  id: string;
  text: string;
  domain: string;
  nivel: string;
  emotion: string;
  /** Confianza medida offline con `pnpm validate:examples` (referencia). */
  validatedConfidence?: number;
};

export const EXAMPLE_PROMPTS: ReadonlyArray<ExamplePrompt> = prompts as ExamplePrompt[];
