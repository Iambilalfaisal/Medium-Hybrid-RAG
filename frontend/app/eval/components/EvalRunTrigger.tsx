"use client";

import { useState } from "react";
import { triggerEvalRun } from "@/lib/api";
import Button from "@/components/ui/Button";

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
      <Button onClick={run} disabled={busy}>
        {busy && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
        {busy ? "Starting…" : "Run Evaluation"}
      </Button>
      {error && <span className="text-sm text-danger">{error}</span>}
    </div>
  );
}
