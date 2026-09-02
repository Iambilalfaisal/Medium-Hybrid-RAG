import ScoreBar from "@/components/ui/ScoreBar";
import Card from "@/components/ui/Card";
import type { RetrievalMetrics } from "@/lib/types";

export default function RetrievalMetricsChart({ metrics }: { metrics: RetrievalMetrics }) {
  return (
    <Card className="flex flex-col gap-4">
      <h3 className="text-sm font-semibold text-text">Retrieval metrics @k={metrics.k}</h3>
      <ScoreBar label="Precision@k" value={metrics.precision_at_k} />
      <ScoreBar label="Recall@k" value={metrics.recall_at_k} />
      <ScoreBar label="F1@k" value={metrics.f1_at_k} />
    </Card>
  );
}
