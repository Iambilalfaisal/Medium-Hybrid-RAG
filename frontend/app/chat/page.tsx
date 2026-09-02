"use client";

import { useState } from "react";
import { streamChatWithReconnect } from "@/lib/api";
import type { ChatMessage, FilterParams } from "@/lib/types";
import ChatThread, { type DisplayMessage } from "./components/ChatThread";
import FilterPanel from "./components/FilterPanel";
import MessageInput from "./components/MessageInput";

export default function ChatPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [filters, setFilters] = useState<FilterParams>({});
  const [isStreaming, setIsStreaming] = useState(false);

  function updateLastMessage(patch: Partial<DisplayMessage>) {
    setMessages((prev) => {
      const copy = [...prev];
      copy[copy.length - 1] = { ...copy[copy.length - 1], ...patch };
      return copy;
    });
  }

  function appendToLastMessage(text: string) {
    setMessages((prev) => {
      const copy = [...prev];
      const last = copy[copy.length - 1];
      copy[copy.length - 1] = { ...last, content: last.content + text, status: "streaming" };
      return copy;
    });
  }

  async function handleSend(text: string) {
    const history: ChatMessage[] = messages.map((m) => ({ role: m.role, content: m.content }));
    const allMessages: ChatMessage[] = [...history, { role: "user", content: text }];

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "", status: "streaming" },
    ]);
    setIsStreaming(true);

    try {
      for await (const event of streamChatWithReconnect(allMessages, filters, 5, () =>
        updateLastMessage({ status: "reconnecting" }),
      )) {
        if (event.event === "sources") {
          updateLastMessage({ sources: event.data.sources, status: "streaming" });
        } else if (event.event === "token") {
          appendToLastMessage(event.data.text);
        } else if (event.event === "done") {
          updateLastMessage({ status: "done" });
        } else if (event.event === "abstain") {
          updateLastMessage({
            content: `I don't have enough information to answer that. (${event.data.reason})`,
            status: "abstain",
          });
        } else if (event.event === "suggestions") {
          updateLastMessage({
            content: "I don't have that ingested yet, but these articles look related:",
            suggestions: event.data.suggestions,
            status: "abstain",
          });
        } else if (event.event === "error") {
          updateLastMessage({ content: `Something went wrong: ${event.data.message}`, status: "error" });
        }
      }
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="flex flex-1 bg-bg">
      <div className="hidden w-64 shrink-0 p-4 md:block">
        <FilterPanel value={filters} onChange={setFilters} />
      </div>
      <div className="flex flex-1 flex-col border-l border-border bg-surface/40">
        <ChatThread messages={messages} />
        <MessageInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
