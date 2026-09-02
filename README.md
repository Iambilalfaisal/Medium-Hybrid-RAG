# Medium Hybrid RAG

A hybrid-search Retrieval-Augmented Generation system over the [Kaggle Medium Articles dataset](https://www.kaggle.com/) (~2,498 articles: `id, url, title, subtitle, claps, responses, reading_time, publication, date`). Modular FastAPI backend, Next.js frontend.

It combines dense vector search (pgvector) + sparse BM25, Reciprocal Rank Fusion, Cohere cross-encoder reranking, parent-child chunking, multi-turn chat with query rewriting, streamed generation with forced citations, abstention on low-confidence retrieval, and a title-only semantic fallback for articles that haven't been fully ingested yet.

---

## 1. The core idea: two tiers of data, by design

The dataset only gives you a `url` per article — no body text. Getting real, groundable answers means visiting every one of ~2,500 URLs, scraping the article, chunking it, and embedding every chunk. That's expensive (network time, and API calls) and doesn't happen instantly.

So the system runs on **two tiers of data coverage**, and is explicit with the user about which tier answered their question:

### Tier 1 — Fully ingested articles (real, cited answers)

For an article that has gone through the full pipeline:

```
CSV row → scrape the real url → extract article body (trafilatura)
        → clean text → split into parent chunks (~2048 chars) and child chunks (~512 chars, 128 overlap)
        → embed every child chunk (Cohere embed-v4.0)
        → store in Postgres (articles / parent_chunks / chunks w/ pgvector HNSW index)
```

A chat query against this tier runs the full retrieval pipeline: dense (pgvector cosine) + sparse (BM25) search over child chunks → Reciprocal Rank Fusion → resolve to parent chunks (deduped by max fused score) → Cohere rerank → **abstain if the top rerank score is below `RERANK_ABSTAIN_THRESHOLD` (0.3)** → otherwise stream a generated answer with forced inline citations (title/publication/year) built only from the retrieved parent-chunk text.

This is real RAG: the answer is grounded in text the system actually read.

### Tier 2 — Everything else (title-only suggestions, no scraping)

Visiting and embedding all ~2,500 articles' full text is the expensive path — it's what actually burns API budget and wall-clock time (scraping is deliberately rate-limited to avoid getting the IP blocked by Cloudflare). Most of the corpus won't be ingested at any given moment.

Instead, **article titles cost nothing to have on hand** — they're already sitting in the CSV, no network fetch required — so the whole 2,498-title set is embedded once, up front, into a small on-disk vector index (`artifacts/title_index.pkl`, plain cosine similarity over a NumPy array, no database). This costs on the order of ~25 batched embedding calls total (titles batch up to 96/call), a few minutes, versus the ~1,250+ calls a full scrape-and-embed run of the whole dataset would need.

When Tier 1 retrieval abstains (nothing relevant has been ingested yet), the system falls back to Tier 2:

```
query → embed the query → cosine-match against the title index
      → dedupe near-duplicate CSV rows by normalized title
      → keep matches above TITLE_SUGGEST_THRESHOLD (0.4)
      → one LLM call to write a one-line "why this might help" per candidate title
      → return as `suggestions`, not as a generated answer
```

This is intentionally **not** presented as a grounded answer — the frontend renders it as a distinct "not ingested yet, but these might help" block with clickable links, never mixed into the cited-answer UI. Semantic title matching (not keyword search) is what lets a query like *"how can I earn $100 a day"* surface a differently-worded title like *"From Zero to $100 a Day: The Ultimate Guide to Launching a Content-Based Business"* — cosine similarity in embedding space catches the meaning, not just shared words.

### Why this two-tier design, concretely

| | Tier 1 (ingested) | Tier 2 (title-only) |
|---|---|---|
| Data used | Full scraped article text | Just the title |
| Cost per article | 1 scrape + 1 batched embed call | Shared across ~25 calls for the whole dataset |
| Answer type | Generated, cited, grounded in real text | A list of possibly-relevant links + one-line guesses |
| Coverage | Only what's been ingested (grows over time) | The entire dataset, always |
| Abstention | Yes — refuses rather than guessing | N/A — suggestions are explicitly labeled as guesses |

The system always tells you which tier answered. It never blends an ungrounded title guess into a cited answer.

---

## 2. What depends on which API key

Three external providers are used, each for a different job — deliberately not overlapping, so a quota problem on one doesn't take down the whole system:

| Key | Used for | If missing / exhausted |
|---|---|---|
| `GOOGLE_API_KEY` (Gemini) | Primary chat generation + query rewriting | Falls back to OpenRouter automatically (before the first streamed token only — see §5) |
| `OPENROUTER_API_KEY` | Fallback chat generation only (`z-ai/glm-5.2:free`) | No fallback if Gemini also fails — chat generation stops working, but retrieval/reranking/abstention still function |
| `COHERE_API_KEY` | **Reranking** (`rerank-v3.5`) **and all embeddings** (`embed-v4.0`, 1536-dim) — both the real ingestion pipeline and the title-only index | **Hard blocker.** Without this key, nothing can be embedded or reranked: ingestion can't run, the title index can't be built, and every chat query fails retrieval (query embedding itself needs this key) |

### Why Cohere carries both rerank and embeddings

This wasn't the original design — Gemini did embeddings and Cohere did reranking. Both Gemini's free embedding tier and OpenRouter's free-model embedding tier were tried first and both hit hard daily quota walls in practice (Gemini: an undocumented daily cap well below its published per-minute figure; OpenRouter: a flat 50 requests/day shared across every free model on the account, including chat fallback usage). Cohere's trial key turned out to have a **separate embed allowance from its rerank allowance** — 1,000 calls/month for embeddings — with real headroom left after both failed. See `app/ingestion/embedder.py`'s docstring for the specifics.

### What you can do with which keys present

- **All three keys, valid** → full functionality: real ingestion, Tier 1 cited chat, Tier 2 title suggestions, reranking, provider failover.
- **Cohere key only** → nothing works end-to-end (embeddings are load-bearing for everything: ingestion, retrieval, title index).
- **Cohere + Gemini, no OpenRouter** → everything works, just no generation fallback if Gemini has an outage.
- **Cohere + OpenRouter, no Gemini** → generation runs on OpenRouter's free model only (lower quality, and shares the same 50/day account-wide cap with nothing to fall back to).

---

## 3. Cost-control design decisions

Because every embedding/rerank/generation call draws from a real, finite free-tier budget, several parts of the pipeline exist specifically to spend that budget efficiently rather than to add features:

- **Batched embedding per article, not per chunk.** `IngestionPipeline._chunk_embed_store` collects every child chunk across an entire article and embeds them in one call (or a few, at the provider's batch cap) instead of one call per parent chunk. This alone cuts embedding calls by roughly the average number of parent chunks per article (~8–13x in practice).
- **Resumability.** `IngestionPipeline._already_ingested` skips any article that already has chunks in the database before touching the scraper or the embedder. An interrupted run (quota exhaustion, crash, manual stop) can be restarted without re-spending budget on articles that already finished.
- **Rate limiting matched to each provider's real limits**, not guessed defaults — `RateLimiter` (token-bucket, `app/utils/rate_limiter.py`) paces embedding calls (`EMBEDDING_RPM`), reranking during eval loops (`COHERE_EVAL_RPM`), and scraping (`SCRAPE_RATE_LIMIT_DELAY_MS`) independently.
- **The title-index fallback itself** is the biggest cost lever: it gives full-dataset coverage for suggestion purposes at the cost of embedding ~2,498 short titles once, instead of scraping and embedding full article text for articles that may never get a query relevant to them.
- **Abstention.** A query that doesn't retrieve anything relevant never reaches the generation step — no wasted LLM call on an answer that would have been refused anyway.
- **Scrape caching.** `ScrapeCache` (SQLite) persists both successful and failed scrape attempts by URL, so re-running ingestion never re-fetches a URL it already resolved (success or failure).

---

## 4. Architecture

### Backend (`backend/`, FastAPI)

```
app/
├── config.py              Pydantic settings, loaded from backend/.env
├── db/                    SQLAlchemy 2.0 async models + session (Postgres + pgvector)
├── ingestion/
│   ├── csv_loader.py       reads medium_data.csv, cleans title/subtitle (strips stray HTML)
│   ├── scraper.py          low-concurrency, rate-limited httpx + trafilatura extraction
│   ├── scrape_cache.py     SQLite success/failure cache keyed by article id
│   ├── cleaner.py          normalizes scraped text, rejects too-short extracts
│   ├── chunker.py          parent/child splitting
│   ├── embedder.py         Cohere embed-v4.0, batched, rate-limited, retried on 429
│   └── pipeline.py         IngestionPipeline — orchestrates the above, resumable
├── retrieval/
│   ├── dense.py             pgvector cosine search
│   ├── sparse_bm25.py       BM25 over child chunks (rank_bm25, rebuilt after each ingestion run)
│   ├── fusion.py            Reciprocal Rank Fusion (RRF, k=60)
│   ├── parent_resolver.py   resolves fused child hits to parent chunks (max-score dedup)
│   ├── reranker.py          Cohere rerank-v3.5, fail-safe (errors → abstain, no local fallback)
│   ├── title_index.py       the Tier-2 title-only vector index (see §1)
│   └── pipeline.py          RetrievalPipeline — wires the above into one run() call
├── generation/
│   ├── llm.py                Gemini + OpenRouter clients
│   ├── provider_router.py    failover between them (pre-first-token only)
│   ├── query_rewrite.py      rewrites multi-turn follow-ups into standalone queries
│   ├── prompt.py              citation-forcing prompt template
│   └── chain.py               ties retrieval + generation + the title-suggestion fallback together
└── api/                     FastAPI routes (chat, ingestion, eval, health) + DI singletons in deps.py
```

### Frontend (`frontend/`, Next.js App Router)

- `/chat` — multi-turn streaming chat, metadata filters, source citations, title-suggestion fallback UI
- `/admin` — trigger ingestion runs, live progress, index stats
- `/eval` — RAGAS-style + classic retrieval metrics dashboard, trend chart across runs

### Eval harness (`eval/`, sibling to `backend/`)

RAGAS metrics are **not** computed via the `ragas` package — the only PyPI release available fails to import in this environment (a stale `langchain_community` reference). Instead, `eval/run_eval.py` computes the same four RAGAS-style dimensions (faithfulness, context precision/recall, answer relevancy) via a single LLM-judge call per query, plus objective precision/recall/F1@k computed independently (each synthetic question's known source article is the ground truth).

---

## 5. Request flows

### Ingestion (`POST /ingestion/run`)

```
for each CSV row (unless already ingested):
    scrape (cached) → clean → chunk → batch-embed the whole article → upsert into Postgres
finally: rebuild the BM25 index off the event loop
```

Guarded against concurrent runs via `ingestion_runs.status`. Progress is polled live at `GET /ingestion/status`.

### Chat (`POST /chat`, SSE stream)

```
rewrite query (if multi-turn) →
resolve metadata filters → dense + sparse search (concurrent) → RRF fuse → resolve parents → rerank
  ├─ below threshold / rerank failed → embed query against the title index (Tier 2)
  │     ├─ matches found → yield `suggestions` event (titles + links + one-line reasons)
  │     └─ no matches → yield `abstain` event
  └─ above threshold → yield `sources` event, then stream a cited answer token-by-token → `done`
```

Provider failover (Gemini → OpenRouter) can only happen **before the first streamed token** — a failure mid-stream ends the stream with an explicit `error` event rather than silently retrying, since a partially-streamed answer can't be safely restarted from a different provider.

---

## 6. Data model

- **`articles`** — one row per ingested CSV row: metadata (title, url, claps, publication, reading_time, published_date) + scrape bookkeeping. Indexed on the four filterable fields.
- **`parent_chunks`** — paragraph-scale chunks (~2048 chars). Never embedded directly; returned as LLM context once one of their children matches.
- **`chunks`** — child chunks (~512 chars, 128-char overlap) with a 1536-dim pgvector embedding column (HNSW index, cosine ops). This is what dense search actually matches against.
- **`ingestion_runs`** — one row per run; `status='running'` doubles as the concurrency guard.
- **`eval_runs`** — JSONB-stored RAGAS + retrieval metrics per evaluation run.
- **`artifacts/title_index.pkl`** — the Tier-2 title vectors (not in Postgres — a flat NumPy array is simpler and plenty fast at ~2,500 rows).
- **`artifacts/bm25_index.pkl`** — the sparse index, rebuilt after every ingestion run.

---

## 7. API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/ingestion/run` | POST | Start an ingestion run (`409` if one's already running) |
| `/ingestion/status` | GET | Live progress of the current/last run |
| `/ingestion/stats` | GET | Total articles/chunks ingested, BM25 index presence |
| `/chat` | POST | SSE stream: `sources` \| `token`\* \| `done` \| `abstain` \| `suggestions` \| `error` |
| `/filters/options` | GET | Distinct publication list + claps/reading-time/date ranges, for the filter UI |
| `/eval/run` | POST | Trigger an evaluation run against `eval/eval_queries.json` |
| `/eval/results` | GET | Historical eval runs |

No auth on any endpoint — fine for local use, not for exposing beyond localhost.

---

## 8. Setup

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, GOOGLE_API_KEY, OPENROUTER_API_KEY, COHERE_API_KEY
python init_db.py                    # creates the pgvector extension + tables
python build_title_index.py          # one-time: embeds all ~2,498 titles (Tier 2)
python run.py                        # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
cp .env.local.example .env.local     # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev                          # http://localhost:3000 (or next free port)
```

Then either trigger a small or full ingestion run from `/admin`, or just start chatting — out-of-scope queries will correctly fall back to Tier-2 suggestions or abstain rather than hallucinate.

---

## 9. Known limitations

- **No auth** on any endpoint.
- **Scrape success rate is roughly 50%** in practice — Medium sits behind Cloudflare and some publications block scraping outright; this is expected, not a bug, and shows up as `articles_skipped` in ingestion stats.
- **Synthetic eval ground truth** (`eval/generate_eval_set.py`) is itself LLM-generated, since there's no human-labeled ground truth for this dataset — useful for regression-testing pipeline changes, not an independent quality bar.
- **The source CSV has data-quality artifacts**: some duplicate rows (same article twice, different ids), and a handful of titles with raw HTML markup baked in (cleaned at load time in `csv_loader.py`, and deduped by title in both the title index and the frontend suggestion list).
- **Windows + psycopg3 async** requires the selector event loop, not the default `ProactorEventLoop` — handled in `app/utils/winloop.py` and via `loop="asyncio:SelectorEventLoop"` in `run.py` (uvicorn hardcodes Proactor on Windows otherwise).
