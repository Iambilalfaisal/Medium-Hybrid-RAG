"use client";

import { useEffect, useState } from "react";
import { getIngestionStatus } from "@/lib/api";
import type { IngestionStatus } from "@/lib/types";

export default function IngestionProgress({ pollKey }: { pollKey: number }) {
  const [status, setStatus] = useState<IngestionStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const s = await getIngestionStatus();
        if (cancelled) return;
        setStatus(s);
        if (s.status === "running") {
          timer = setTimeout(poll, 2000);
        }
      } catch {
        if (!cancelled) timer = setTimeout(poll, 3000);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [pollKey]);

  if (!status) return <p className="text-sm text-zinc-400">Loading status…</p>;

  const pct =
    status.articles_total > 0 ? Math.round((status.articles_processed / status.articles_total) * 100) : 0;

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-4 text-sm">
      <div className="flex justify-between">
        <span className="font-medium">Status: {status.status}</span>
        {status.status === "running" && <span>{status.current_stage}</span>}
      </div>

      {status.articles_total > 0 && (
        <div className="h-2 w-full overflow-hidden rounded bg-zinc-100">
          <div className="h-full bg-zinc-900 transition-all" style={{ width: `${pct}%` }} />
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-zinc-600">
        <span>
          Processed: {status.articles_processed}/{status.articles_total}
        </span>
        <span>Scraped OK: {status.articles_scraped_ok}</span>
        <span>Skipped: {status.articles_skipped}</span>
        <span>Cleaner rejected: {status.cleaner_rejected_count}</span>
        <span>Chunks created: {status.chunks_created}</span>
      </div>

      {status.status === "failed" && status.error && <p className="text-red-600">Error: {status.error}</p>}
    </div>
  );
}
