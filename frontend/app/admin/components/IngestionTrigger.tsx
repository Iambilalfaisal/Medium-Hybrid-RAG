"use client";

import { useState } from "react";
import { startIngestion } from "@/lib/api";

export default function IngestionTrigger({ onStarted }: { onStarted: () => void }) {
  const [forceRescrape, setForceRescrape] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function trigger() {
    setBusy(true);
    setError(null);
    try {
      await startIngestion(forceRescrape);
      onStarted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start ingestion");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-4">
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={forceRescrape} onChange={(e) => setForceRescrape(e.target.checked)} />
        Force re-scrape (ignore cache)
      </label>
      <button
        className="w-fit rounded bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-40"
        onClick={trigger}
        disabled={busy}
      >
        {busy ? "Starting…" : "Run Ingestion"}
      </button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
