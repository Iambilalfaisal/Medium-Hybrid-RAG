"use client";

import { useEffect, useState } from "react";
import { getIngestionStats } from "@/lib/api";
import type { IngestionStats } from "@/lib/types";

export default function IndexStats({ refreshKey }: { refreshKey: number }) {
  const [stats, setStats] = useState<IngestionStats | null>(null);

  useEffect(() => {
    getIngestionStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, [refreshKey]);

  if (!stats) return <p className="text-sm text-zinc-400">Loading stats…</p>;

  return (
    <div className="grid grid-cols-2 gap-4 rounded-lg border border-zinc-200 bg-white p-4 text-sm sm:grid-cols-4">
      <Stat label="Articles" value={stats.total_articles_ingested} />
      <Stat label="Chunks" value={stats.total_chunks} />
      <Stat label="BM25 index" value={stats.bm25_index_present ? "ready" : "not built"} />
      <Stat label="Last run" value={stats.last_run_status ?? "none"} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-2xl font-semibold text-zinc-900">{value}</div>
      <div className="text-xs uppercase tracking-wide text-zinc-400">{label}</div>
    </div>
  );
}
