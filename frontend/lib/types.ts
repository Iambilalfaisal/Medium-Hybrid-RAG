export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface FilterParams {
  claps_min?: number | null;
  claps_max?: number | null;
  publication?: string[] | null;
  date_from?: string | null;
  date_to?: string | null;
  reading_time_min?: number | null;
  reading_time_max?: number | null;
}

export interface FilterOptions {
  publications: string[];
  claps_min: number | null;
  claps_max: number | null;
  reading_time_min: number | null;
  reading_time_max: number | null;
  date_min: string | null;
  date_max: string | null;
}

export interface SourceCitation {
  article_id: string;
  title: string;
  url: string;
  publication: string | null;
  claps: number | null;
  chunk_excerpt: string;
}

export interface IngestionRunStarted {
  run_id: number;
  status: string;
}

export interface IngestionStatus {
  run_id: number | null;
  status: "idle" | "running" | "completed" | "failed";
  current_stage: string;
  articles_total: number;
  articles_processed: number;
  articles_scraped_ok: number;
  articles_skipped: number;
  cleaner_rejected_count: number;
  chunks_created: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface IngestionStats {
  total_articles_ingested: number;
  total_chunks: number;
  last_run_at: string | null;
  last_run_status: string | null;
  bm25_index_present: boolean;
}

export interface RagasScores {
  faithfulness: number;
  context_precision: number;
  context_recall: number;
  answer_relevancy: number;
}

export interface RetrievalMetrics {
  precision_at_k: number;
  recall_at_k: number;
  f1_at_k: number;
  k: number;
}

export interface EvalRunResult {
  id: number;
  run_at: string;
  ragas_scores: RagasScores;
  retrieval_metrics: RetrievalMetrics;
}

export interface TitleSuggestion {
  title: string;
  url: string;
  score: number;
  description: string;
}

export type ChatSSEEvent =
  | { event: "sources"; data: { sources: SourceCitation[]; rewritten_query: string } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: Record<string, never> }
  | { event: "abstain"; data: { reason: string } }
  | { event: "suggestions"; data: { reason: string; suggestions: TitleSuggestion[] } }
  | { event: "error"; data: { message: string } };
