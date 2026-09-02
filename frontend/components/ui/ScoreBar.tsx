function toneFor(pct: number): { bar: string; text: string } {
  if (pct >= 70) return { bar: "bg-success", text: "text-success" };
  if (pct >= 40) return { bar: "bg-warning", text: "text-warning" };
  return { bar: "bg-danger", text: "text-danger" };
}

export default function ScoreBar({ label, value, max = 1 }: { label: string; value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const tone = toneFor(pct);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-text-muted">{label}</span>
        <span className={`font-mono font-medium ${tone.text}`}>
          {max === 1 ? `${(value * 100).toFixed(1)}%` : value.toFixed(3)}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className={`h-full rounded-full transition-[width] duration-700 ease-out ${tone.bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
