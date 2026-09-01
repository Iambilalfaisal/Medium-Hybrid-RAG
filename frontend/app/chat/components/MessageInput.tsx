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
    <div className="flex gap-2 border-t border-zinc-200 bg-white p-4">
      <input
        className="flex-1 rounded border border-zinc-300 px-3 py-2 text-sm"
        placeholder="Ask about an article…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        disabled={disabled}
      />
      <button
        className="rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-40"
        onClick={submit}
        disabled={disabled}
      >
        Send
      </button>
    </div>
  );
}
