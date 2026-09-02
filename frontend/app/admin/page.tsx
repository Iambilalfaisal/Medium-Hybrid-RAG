"use client";

import { useState } from "react";
import IndexStats from "./components/IndexStats";
import IngestionProgress from "./components/IngestionProgress";
import IngestionTrigger from "./components/IngestionTrigger";

export default function AdminPage() {
  const [pollKey, setPollKey] = useState(0);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-text">Ingestion Admin</h1>
        <p className="mt-1 text-sm text-text-muted">Scrape, chunk, and embed the source dataset into the index.</p>
      </div>
      <IngestionTrigger onStarted={() => setPollKey((k) => k + 1)} />
      <IngestionProgress pollKey={pollKey} />
      <IndexStats refreshKey={pollKey} />
    </div>
  );
}
