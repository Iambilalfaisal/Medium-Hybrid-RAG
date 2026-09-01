import type { SourceCitation } from "@/lib/types";

export default function SourceList({ sources }: { sources: SourceCitation[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2 flex flex-col gap-2 border-t border-zinc-100 pt-2">
      <span className="text-xs font-medium uppercase tracking-wide text-zinc-400">Sources</span>
      {sources.map((s) => (
        <a
          key={s.article_id}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded border border-zinc-200 bg-zinc-50 p-2 text-xs hover:border-zinc-300"
        >
          <div className="font-medium text-zinc-800">{s.title}</div>
          <div className="text-zinc-500">
            {s.publication ?? "Unknown"} · {s.claps ?? 0} claps
          </div>
          <div className="mt-1 text-zinc-600">{s.chunk_excerpt}…</div>
        </a>
      ))}
    </div>
  );
}
