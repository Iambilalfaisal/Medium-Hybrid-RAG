import type { TitleSuggestion } from "@/lib/types";

function cleanTitle(title: string): string {
  return title.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

function dedupeByTitle(suggestions: TitleSuggestion[]): TitleSuggestion[] {
  const seen = new Set<string>();
  const result: TitleSuggestion[] = [];
  for (const s of suggestions) {
    const key = cleanTitle(s.title).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(s);
  }
  return result;
}

export default function SuggestionList({ suggestions }: { suggestions: TitleSuggestion[] }) {
  const unique = dedupeByTitle(suggestions);
  if (unique.length === 0) return null;

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
      <span className="text-xs font-semibold uppercase tracking-wide text-text-faint">
        Not ingested yet — might be worth reading
      </span>
      {unique.map((s) => (
        <a
          key={s.url}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="group rounded-lg border border-dashed border-border-strong bg-bg p-2.5 text-xs transition-all duration-150 hover:-translate-y-0.5 hover:border-accent/40 hover:bg-accent-soft/40 hover:shadow-sm"
        >
          <div className="flex items-start justify-between gap-2">
            <span className="font-medium text-text group-hover:text-accent">{cleanTitle(s.title)}</span>
            <span className="shrink-0 rounded-full bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-faint">
              {Math.round(s.score * 100)}%
            </span>
          </div>
          {s.description && <div className="mt-1 text-text-muted">{s.description}</div>}
        </a>
      ))}
    </div>
  );
}
