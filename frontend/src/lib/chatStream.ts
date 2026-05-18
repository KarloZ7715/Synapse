import type { ChatRequest, ChatStreamEvent, ChatUsage } from "~/types/chat";

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

function parseEventData(chunk: string): ChatStreamEvent | null {
  const dataLines = chunk
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());

  if (dataLines.length === 0) {
    return null;
  }

  const payload = dataLines.join("\n");
  if (payload === "[DONE]") {
    return null;
  }

  return JSON.parse(payload) as ChatStreamEvent;
}

export async function streamChat(
  request: ChatRequest,
  handlers: {
    onToken: (token: string) => void;
    onUsage: (usage: ChatUsage) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  const init: RequestInit = {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  };

  if (signal) {
    init.signal = signal;
  }

  const response = await fetch(apiUrl("/api/chat"), init);

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Backend respondió ${response.status}`);
  }

  if (!response.body) {
    throw new Error("El backend no devolvió un stream legible");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      if (!rawEvent.trim()) {
        continue;
      }
      const event = parseEventData(rawEvent);
      if (!event) {
        continue;
      }
      if ("token" in event) {
        handlers.onToken(event.token);
        continue;
      }
      if ("type" in event && event.type === "usage") {
        handlers.onUsage(event);
        continue;
      }
      if ("error" in event) {
        throw new Error(event.detail ?? event.error);
      }
    }

    if (done) {
      break;
    }
  }
}