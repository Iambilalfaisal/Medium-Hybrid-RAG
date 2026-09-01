import type { EvalRunResult } from "@/lib/types";

export default function EvalHistoryChart({ runs }: { runs: EvalRunResult[] }) {
  if (runs.length < 2) {
    return <p className="text-sm text-zinc-400">Run the eval at least twice to see a trend.</p>;
  }

  const ordered = [...runs].reverse(); // oldest first
  const width = 480;
  const height = 120;
  const padding = 8;

  function points(values: number[]) {
    return values
      .map((v, i) => {
        const x = padding + (i / (values.length - 1)) * (width - padding * 2);
        const y = height - padding - v * (height - padding * 2);
        return `${x},${y}`;
      })
      .join(" ");
  }

  const faithfulness = ordered.map((r) => r.ragas_scores.faithfulness);
  const f1 = ordered.map((r) => r.retrieval_metrics.f1_at_k);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-medium text-zinc-700">Trend over runs</h3>
      <svg width={width} height={height} className="w-full" viewBox={`0 0 ${width} ${height}`}>
        <polyline points={points(faithfulness)} fill="none" stroke="#10b981" strokeWidth={2} />
        <polyline points={points(f1)} fill="none" stroke="#3b82f6" strokeWidth={2} />
      </svg>
      <div className="mt-2 flex gap-4 text-xs">
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-emerald-500" /> Faithfulness
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-blue-500" /> F1@k
        </span>
      </div>
    </div>
  );
}
