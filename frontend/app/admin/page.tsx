"use client";

import { useState } from "react";
import IndexStats from "./components/IndexStats";
import IngestionProgress from "./components/IngestionProgress";
import IngestionTrigger from "./components/IngestionTrigger";

export default function AdminPage() {
  const [pollKey, setPollKey] = useState(0);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">Ingestion Admin</h1>
      <IngestionTrigger onStarted={() => setPollKey((k) => k + 1)} />
      <IngestionProgress pollKey={pollKey} />
      <IndexStats refreshKey={pollKey} />
    </div>
  );
}
