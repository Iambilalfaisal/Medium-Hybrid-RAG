import type { SourceCitation } from "@/lib/types";
import SourceList from "./SourceList";

export interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  status?: "streaming" | "done" | "abstain" | "error" | "reconnecting";
}

export default function ChatThread({ messages }: { messages: DisplayMessage[] }) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-6">
      {messages.length === 0 && (
        <p className="text-sm text-zinc-400">Ask a question about the ingested Medium articles.</p>
      )}
      {messages.map((m, i) => (
        <div
          key={i}
          className={`max-w-2xl rounded-lg p-3 text-sm ${
            m.role === "user" ? "self-end bg-zinc-900 text-white" : "self-start border border-zinc-200 bg-white"
          }`}
        >
          <div className="whitespace-pre-wrap">{m.content || (m.status === "streaming" ? "…" : "")}</div>
          {m.status === "reconnecting" && <div className="mt-1 text-xs italic text-amber-600">Reconnecting…</div>}
          {m.status === "error" && <div className="mt-1 text-xs text-red-600">Connection error</div>}
          {m.sources && <SourceList sources={m.sources} />}
        </div>
      ))}
    </div>
  );
}
