"use client";

import { useEffect, useState } from "react";
import { getFilterOptions } from "@/lib/api";
import type { FilterOptions, FilterParams } from "@/lib/types";
import Card from "@/components/ui/Card";

interface Props {
  value: FilterParams;
  onChange: (filters: FilterParams) => void;
}

const inputClass =
  "rounded-lg border border-border bg-bg px-2.5 py-1.5 text-sm text-text transition-shadow focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20";

export default function FilterPanel({ value, onChange }: Props) {
  const [options, setOptions] = useState<FilterOptions | null>(null);

  useEffect(() => {
    getFilterOptions()
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);

  if (!options) {
    return (
      <Card className="flex flex-col gap-3">
        <div className="h-4 w-16 animate-pulse rounded bg-surface-2" />
        <div className="h-8 w-full animate-pulse rounded-lg bg-surface-2" />
        <div className="h-8 w-full animate-pulse rounded-lg bg-surface-2" />
        <div className="h-8 w-full animate-pulse rounded-lg bg-surface-2" />
      </Card>
    );
  }

  return (
    <Card className="flex flex-col gap-4 text-sm">
      <h2 className="flex items-center gap-1.5 font-semibold text-text">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 6h16M7 12h10M10 18h4" strokeLinecap="round" />
        </svg>
        Filters
      </h2>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-text-faint">Publication</span>
        <select
          className={inputClass}
          value={value.publication?.[0] ?? ""}
          onChange={(e) => onChange({ ...value, publication: e.target.value ? [e.target.value] : null })}
        >
          <option value="">Any</option>
          {options.publications.map((pub) => (
            <option key={pub} value={pub}>
              {pub}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-text-faint">Min claps</span>
        <input
          type="number"
          className={inputClass}
          placeholder={options.claps_min?.toString() ?? "0"}
          value={value.claps_min ?? ""}
          onChange={(e) => onChange({ ...value, claps_min: e.target.value ? Number(e.target.value) : null })}
        />
      </label>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-text-faint">Max reading time (min)</span>
        <input
          type="number"
          className={inputClass}
          placeholder={options.reading_time_max?.toString() ?? ""}
          value={value.reading_time_max ?? ""}
          onChange={(e) =>
            onChange({ ...value, reading_time_max: e.target.value ? Number(e.target.value) : null })
          }
        />
      </label>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-text-faint">Published after</span>
        <input
          type="date"
          className={inputClass}
          min={options.date_min ?? undefined}
          max={options.date_max ?? undefined}
          value={value.date_from ?? ""}
          onChange={(e) => onChange({ ...value, date_from: e.target.value || null })}
        />
      </label>
    </Card>
  );
}
