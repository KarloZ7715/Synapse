import type { ClassificationMetadata } from "~/types/classifier";
import type { HeadConfidences } from "~/types/chat";

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return import.meta.env.DEV ? "http://localhost:8000" : "";
}

function apiUrl(path: string): string {
  const base = apiBaseUrl();
  return base ? `${base}${path}` : path;
}

export type PromptPreviewResponse = {
  system_prompt: string;
};

export async function fetchPromptPreview(
  metadata: ClassificationMetadata,
  headConfidences?: HeadConfidences,
  signal?: AbortSignal,
): Promise<string> {
  const init: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      metadata,
      head_confidences: headConfidences ?? undefined,
    }),
  };
  if (signal) {
    init.signal = signal;
  }

  const response = await fetch(apiUrl("/api/prompt/preview"), init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Preview respondio ${response.status}`);
  }

  const data = (await response.json()) as PromptPreviewResponse;
  return data.system_prompt;
}
