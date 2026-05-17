import { Brain } from "~/components/icons";
import { Badge } from "~/components/ui/badge";
import { ChatBubble } from "./ChatBubble";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: {
    nivel_tecnico: string;
    urgencia: string;
    emocion: string;
    dominio: string;
  };
  isStreaming?: boolean;
};

export function ChatMessage(props: { message: Message }) {
  const m = props.message;

  return (
    <div class={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
      <ChatBubble variant={m.role}>
        {m.role === "assistant" && (
          <div class="mb-1.5 flex items-center gap-2">
            <Brain color="#c084fc" size={14} />
            <span class="text-xs font-mono font-bold text-[#c084fc]">Synapse</span>
          </div>
        )}
        <div class="whitespace-pre-wrap">
          {m.content}
          {m.isStreaming && <span class="animate-blink text-[#22d3ee]">█</span>}
        </div>
        {m.metadata && (
          <div class="mt-2 flex flex-wrap gap-1.5">
            <Badge variant="blue">{m.metadata.nivel_tecnico}</Badge>
            <Badge variant="amber">{m.metadata.urgencia}</Badge>
            <Badge variant="purple">{m.metadata.emocion}</Badge>
            <Badge variant="emerald">{m.metadata.dominio}</Badge>
          </div>
        )}
      </ChatBubble>
    </div>
  );
}
