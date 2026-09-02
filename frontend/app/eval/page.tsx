"use client";

import { useEffect, useState } from "react";
import { getEvalResults } from "@/lib/api";
import type { EvalRunResult } from "@/lib/types";
import EvalHistoryChart from "./components/EvalHistoryChart";
import EvalRunTrigger from "./components/EvalRunTrigger";
import RagasScoreCards from "./components/RagasScoreCards";
import RetrievalMetricsChart from "./components/RetrievalMetricsChart";

export default function EvalPage() {
  const [runs, setRuns] = useState<EvalRunResult[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getEvalResults()
      .then(setRuns)
      .catch(() => setRuns([]));
  }, [refreshKey]);

  const latest = runs[0];

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-text">Eval Dashboard</h1>
          <p className="mt-1 text-sm text-text-muted">RAGAS + retrieval quality metrics over time.</p>
        </div>
        <EvalRunTrigger onTriggered={() => setRefreshKey((k) => k + 1)} />
      </div>

      {!latest && (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border-strong py-16 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 19V5M4 19h16M9 19V9M14 19v-6M19 19V7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <p className="text-sm text-text-muted">No eval runs yet — trigger one above.</p>
        </div>
      )}

      {latest && (
        <>
          <RagasScoreCards scores={latest.ragas_scores} />
          <RetrievalMetricsChart metrics={latest.retrieval_metrics} />
          <EvalHistoryChart runs={runs} />
        </>
      )}
    </div>
  );
}
