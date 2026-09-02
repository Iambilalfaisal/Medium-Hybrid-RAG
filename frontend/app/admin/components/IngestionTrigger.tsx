"use client";

import { useState } from "react";
import { startIngestion } from "@/lib/api";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

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
    <Card className="flex flex-col gap-3">
      <label className="flex w-fit items-center gap-2 text-sm text-text-muted">
        <input
          type="checkbox"
          checked={forceRescrape}
          onChange={(e) => setForceRescrape(e.target.checked)}
          className="h-4 w-4 rounded border-border-strong accent-accent"
        />
        Force re-scrape (ignore cache)
      </label>
      <Button onClick={trigger} disabled={busy} className="w-fit">
        {busy && (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
        )}
        {busy ? "Starting…" : "Run Ingestion"}
      </Button>
      {error && <p className="text-sm text-danger">{error}</p>}
    </Card>
  );
}
