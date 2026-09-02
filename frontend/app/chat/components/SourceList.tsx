import type { SourceCitation } from "@/lib/types";

export default function SourceList({ sources }: { sources: SourceCitation[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
      <span className="text-xs font-semibold uppercase tracking-wide text-text-faint">Sources</span>
      {sources.map((s, i) => (
        <a
          key={`${s.article_id}-${i}`}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="group rounded-lg border border-border bg-bg p-2.5 text-xs transition-all duration-150 hover:-translate-y-0.5 hover:border-accent/40 hover:bg-accent-soft/40 hover:shadow-sm"
        >
          <div className="flex items-start justify-between gap-2">
            <span className="font-medium text-text group-hover:text-accent">{s.title}</span>
            <svg
              width="11"
              height="11"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              className="mt-0.5 shrink-0 text-text-faint opacity-0 transition-opacity group-hover:opacity-100"
            >
              <path d="M7 17 17 7M9 7h8v8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="mt-1 text-text-faint">
            {s.publication ?? "Unknown"} · {s.claps ?? 0} claps
          </div>
          <div className="mt-1.5 text-text-muted">{s.chunk_excerpt}…</div>
        </a>
      ))}
    </div>
  );
}
