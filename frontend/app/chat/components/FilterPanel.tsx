"use client";

import { useEffect, useState } from "react";
import { getFilterOptions } from "@/lib/api";
import type { FilterOptions, FilterParams } from "@/lib/types";

interface Props {
  value: FilterParams;
  onChange: (filters: FilterParams) => void;
}

export default function FilterPanel({ value, onChange }: Props) {
  const [options, setOptions] = useState<FilterOptions | null>(null);

  useEffect(() => {
    getFilterOptions()
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);

  if (!options) {
    return <div className="text-sm text-zinc-400">Loading filters…</div>;
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4 text-sm">
      <h2 className="font-medium text-zinc-700">Filters</h2>

      <label className="flex flex-col gap-1">
        Publication
        <select
          className="rounded border border-zinc-300 px-2 py-1"
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

      <label className="flex flex-col gap-1">
        Min claps
        <input
          type="number"
          className="rounded border border-zinc-300 px-2 py-1"
          placeholder={options.claps_min?.toString() ?? "0"}
          value={value.claps_min ?? ""}
          onChange={(e) => onChange({ ...value, claps_min: e.target.value ? Number(e.target.value) : null })}
        />
      </label>

      <label className="flex flex-col gap-1">
        Max reading time (min)
        <input
          type="number"
          className="rounded border border-zinc-300 px-2 py-1"
          placeholder={options.reading_time_max?.toString() ?? ""}
          value={value.reading_time_max ?? ""}
          onChange={(e) =>
            onChange({ ...value, reading_time_max: e.target.value ? Number(e.target.value) : null })
          }
        />
      </label>

      <label className="flex flex-col gap-1">
        Published after
        <input
          type="date"
          className="rounded border border-zinc-300 px-2 py-1"
          min={options.date_min ?? undefined}
          max={options.date_max ?? undefined}
          value={value.date_from ?? ""}
          onChange={(e) => onChange({ ...value, date_from: e.target.value || null })}
        />
      </label>
    </div>
  );
}
