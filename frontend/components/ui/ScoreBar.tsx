export default function ScoreBar({ label, value, max = 1 }: { label: string; value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-zinc-500">
        <span>{label}</span>
        <span>{max === 1 ? `${(value * 100).toFixed(1)}%` : value.toFixed(3)}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded bg-zinc-100">
        <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
