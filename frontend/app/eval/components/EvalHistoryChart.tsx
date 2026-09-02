import Card from "@/components/ui/Card";
import type { EvalRunResult } from "@/lib/types";

const WIDTH = 480;
const HEIGHT = 140;
const PAD = 10;

function linePoints(values: number[]) {
  return values.map((v, i) => {
    const x = PAD + (values.length === 1 ? 0 : (i / (values.length - 1)) * (WIDTH - PAD * 2));
    const y = HEIGHT - PAD - v * (HEIGHT - PAD * 2);
    return { x, y };
  });
}

function toPath(points: { x: number; y: number }[]) {
  return points.map((p) => `${p.x},${p.y}`).join(" ");
}

function Series({ values, color, id }: { values: number[]; color: string; id: string }) {
  const points = linePoints(values);
  const area = `${PAD},${HEIGHT - PAD} ${toPath(points)} ${WIDTH - PAD},${HEIGHT - PAD}`;
  const last = points[points.length - 1];

  return (
    <g>
      <defs>
        <linearGradient id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#grad-${id})`} />
      <polyline
        points={toPath(points)}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={last.x} cy={last.y} r={3.5} fill={color} stroke="var(--surface)" strokeWidth={1.5} />
    </g>
  );
}

export default function EvalHistoryChart({ runs }: { runs: EvalRunResult[] }) {
  if (runs.length < 2) {
    return (
      <Card>
        <h3 className="mb-1 text-sm font-semibold text-text">Trend over runs</h3>
        <p className="text-sm text-text-faint">Run the eval at least twice to see a trend.</p>
      </Card>
    );
  }

  const ordered = [...runs].reverse();
  const faithfulness = ordered.map((r) => r.ragas_scores.faithfulness);
  const f1 = ordered.map((r) => r.retrieval_metrics.f1_at_k);

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-text">Trend over runs</h3>
      <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full overflow-visible">
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = HEIGHT - PAD - frac * (HEIGHT - PAD * 2);
          return (
            <line
              key={frac}
              x1={PAD}
              x2={WIDTH - PAD}
              y1={y}
              y2={y}
              stroke="var(--border)"
              strokeWidth={1}
              strokeDasharray={frac === 0 ? undefined : "3 3"}
            />
          );
        })}
        <Series values={faithfulness} color="var(--accent)" id="faithfulness" />
        <Series values={f1} color="#f59e0b" id="f1" />
      </svg>
      <div className="mt-3 flex gap-4 text-xs text-text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-accent" /> Faithfulness
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[#f59e0b]" /> F1@k
        </span>
      </div>
    </Card>
  );
}
