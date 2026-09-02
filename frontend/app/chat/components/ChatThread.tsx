import type { SourceCitation, TitleSuggestion } from "@/lib/types";
import SourceList from "./SourceList";
import SuggestionList from "./SuggestionList";

export interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  suggestions?: TitleSuggestion[];
  status?: "streaming" | "done" | "abstain" | "error" | "reconnecting";
}

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-text-faint"
          style={{ animation: "pulse-soft 1.2s ease-in-out infinite", animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 3a9 9 0 1 0 9 9 9.01 9.01 0 0 0-9-9Z" opacity="0.25" />
          <path d="M8 12h.01M12 12h.01M16 12h.01" strokeLinecap="round" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium text-text">Ask about the ingested Medium articles</p>
        <p className="mt-1 text-xs text-text-faint">Retrieval is grounded — out-of-scope questions get real citations or a clear abstention.</p>
      </div>
    </div>
  );
}

export default function ChatThread({ messages }: { messages: DisplayMessage[] }) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-6">
      {messages.length === 0 && <EmptyState />}
      {messages.map((m, i) => (
        <div
          key={i}
          className={`flex max-w-2xl animate-fade-up gap-2.5 ${m.role === "user" ? "self-end flex-row-reverse" : "self-start"}`}
        >
          {m.role === "assistant" && (
            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2 9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5Z" />
              </svg>
            </div>
          )}
          <div
            className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              m.role === "user"
                ? "rounded-tr-sm bg-accent text-white"
                : "rounded-tl-sm border border-border bg-surface shadow-sm shadow-black/[0.03]"
            }`}
          >
            <div className="whitespace-pre-wrap">
              {m.content || (m.status === "streaming" ? <ThinkingDots /> : "")}
            </div>
            {m.status === "reconnecting" && (
              <div className="mt-2 flex items-center gap-1.5 text-xs font-medium text-warning">
                <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-warning" />
                Reconnecting…
              </div>
            )}
            {m.status === "error" && (
              <div className="mt-2 flex items-center gap-1.5 text-xs font-medium text-danger">
                <span className="h-1.5 w-1.5 rounded-full bg-danger" />
                Connection error
              </div>
            )}
            {m.sources && <SourceList sources={m.sources} />}
            {m.suggestions && <SuggestionList suggestions={m.suggestions} />}
          </div>
        </div>
      ))}
    </div>
  );
}
