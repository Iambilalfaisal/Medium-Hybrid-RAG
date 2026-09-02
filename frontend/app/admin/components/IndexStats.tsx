"use client";

import { useEffect, useState } from "react";
import { getIngestionStats } from "@/lib/api";
import type { IngestionStats } from "@/lib/types";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

export default function IndexStats({ refreshKey }: { refreshKey: number }) {
  const [stats, setStats] = useState<IngestionStats | null>(null);

  useEffect(() => {
    getIngestionStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, [refreshKey]);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i}>
            <div className="h-7 w-12 animate-pulse rounded bg-surface-2" />
            <div className="mt-2 h-3 w-16 animate-pulse rounded bg-surface-2" />
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <NumberStat label="Articles" value={stats.total_articles_ingested} />
      <NumberStat label="Chunks" value={stats.total_chunks} />
      <StatusStat
        label="BM25 index"
        tone={stats.bm25_index_present ? "success" : "neutral"}
        text={stats.bm25_index_present ? "ready" : "not built"}
      />
      <StatusStat
        label="Last run"
        tone={stats.last_run_status === "completed" ? "success" : stats.last_run_status === "failed" ? "danger" : "neutral"}
        text={stats.last_run_status ?? "none"}
      />
    </div>
  );
}

function NumberStat({ label, value }: { label: string; value: number }) {
  return (
    <Card interactive>
      <div className="font-mono text-2xl font-semibold text-text">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-text-faint">{label}</div>
    </Card>
  );
}

function StatusStat({ label, tone, text }: { label: string; tone: "success" | "danger" | "neutral"; text: string }) {
  return (
    <Card interactive className="flex flex-col gap-2">
      <Badge tone={tone}>{text}</Badge>
      <div className="text-xs uppercase tracking-wide text-text-faint">{label}</div>
    </Card>
  );
}
