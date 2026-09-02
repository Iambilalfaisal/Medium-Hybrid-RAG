"use client";

import { useEffect, useState } from "react";
import { getIngestionStatus } from "@/lib/api";
import type { IngestionStatus } from "@/lib/types";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

const STATUS_TONE = {
  idle: "neutral",
  running: "accent",
  completed: "success",
  failed: "danger",
} as const;

const STAT_ITEMS: { key: keyof IngestionStatus; label: string }[] = [
  { key: "articles_scraped_ok", label: "Scraped OK" },
  { key: "articles_skipped", label: "Skipped" },
  { key: "cleaner_rejected_count", label: "Cleaner rejected" },
  { key: "chunks_created", label: "Chunks created" },
];

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

  if (!status) {
    return (
      <Card className="flex flex-col gap-2">
        <div className="h-4 w-24 animate-pulse rounded bg-surface-2" />
        <div className="h-2 w-full animate-pulse rounded-full bg-surface-2" />
      </Card>
    );
  }

  const pct =
    status.articles_total > 0 ? Math.round((status.articles_processed / status.articles_total) * 100) : 0;

  return (
    <Card className="flex flex-col gap-3 text-sm">
      <div className="flex items-center justify-between">
        <Badge tone={STATUS_TONE[status.status]} pulse={status.status === "running"}>
          {status.status}
        </Badge>
        {status.status === "running" && <span className="text-xs text-text-faint">{status.current_stage}</span>}
      </div>

      {status.articles_total > 0 && (
        <>
          <div className="relative h-2 w-full overflow-hidden rounded-full bg-surface-2">
            <div
              className="relative h-full overflow-hidden rounded-full bg-accent transition-[width] duration-500 ease-out"
              style={{ width: `${pct}%` }}
            >
              {status.status === "running" && (
                <div
                  className="absolute inset-0 animate-shimmer bg-[length:200%_100%]"
                  style={{
                    backgroundImage:
                      "linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)",
                  }}
                />
              )}
            </div>
          </div>
          <div className="flex justify-between text-xs text-text-faint">
            <span>
              {status.articles_processed}/{status.articles_total} processed
            </span>
            <span className="font-mono">{pct}%</span>
          </div>
        </>
      )}

      <div className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border pt-3 sm:grid-cols-4">
        {STAT_ITEMS.map((item) => (
          <div key={item.key}>
            <div className="font-mono text-base font-semibold text-text">{status[item.key] as number}</div>
            <div className="text-[11px] uppercase tracking-wide text-text-faint">{item.label}</div>
          </div>
        ))}
      </div>

      {status.status === "failed" && status.error && (
        <p className="rounded-lg bg-danger-soft px-3 py-2 text-xs text-danger">{status.error}</p>
      )}
    </Card>
  );
}
