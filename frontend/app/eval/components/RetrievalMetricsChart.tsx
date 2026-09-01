import ScoreBar from "@/components/ui/ScoreBar";
import type { RetrievalMetrics } from "@/lib/types";

export default function RetrievalMetricsChart({ metrics }: { metrics: RetrievalMetrics }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="text-sm font-medium text-zinc-700">Retrieval metrics @k={metrics.k}</h3>
      <ScoreBar label="Precision@k" value={metrics.precision_at_k} />
      <ScoreBar label="Recall@k" value={metrics.recall_at_k} />
      <ScoreBar label="F1@k" value={metrics.f1_at_k} />
    </div>
  );
}
