"use client";

import { useState } from "react";

export default function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState("");

  const submit = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <div className="border-t border-border bg-surface p-4">
      <div className="mx-auto flex max-w-3xl items-center gap-2 rounded-full border border-border bg-bg px-2 py-2 transition-shadow focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
        <input
          className="flex-1 bg-transparent px-3 text-sm text-text placeholder:text-text-faint focus:outline-none disabled:opacity-50"
          placeholder="Ask about an article…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          disabled={disabled}
        />
        <button
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-white transition-all duration-150 hover:bg-accent-hover active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100"
          onClick={submit}
          disabled={disabled}
          aria-label="Send"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M22 2 11 13" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M22 2 15 22l-4-9-9-4 20-7Z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
