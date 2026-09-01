"use client";

import { useState } from "react";
import { triggerEvalRun } from "@/lib/api";

export default function EvalRunTrigger({ onTriggered }: { onTriggered: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await triggerEvalRun();
      onTriggered();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger eval run");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        className="rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-40"
        onClick={run}
        disabled={busy}
      >
        {busy ? "Starting…" : "Run Evaluation"}
      </button>
      {error && <span className="text-sm text-red-600">{error}</span>}
    </div>
  );
}
