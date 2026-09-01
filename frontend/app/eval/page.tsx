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
        <h1 className="text-xl font-semibold">Eval Dashboard</h1>
        <EvalRunTrigger onTriggered={() => setRefreshKey((k) => k + 1)} />
      </div>

      {!latest && <p className="text-sm text-zinc-400">No eval runs yet — trigger one above.</p>}

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
