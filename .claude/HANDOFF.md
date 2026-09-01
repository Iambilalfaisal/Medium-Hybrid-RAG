# HANDOFF — Medium-Hybrid-RAG — 5 tasks (backend build, ingestion module done)

## GOAL
Production-grade hybrid RAG pipeline over the Kaggle Medium Articles CSV (~2,498 rows,
metadata only — no body text, no tags). Modular FastAPI backend + Next.js frontend.
Full approved architecture lives in the plan file — treat it as authoritative, don't
re-derive: `C:\Users\PC\.claude\plans\role-and-context-dazzling-pudding.md`

## STACK / ENV
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 async (`postgresql+psycopg` driver,
  psycopg3) + pgvector, `rank_bm25`, Cohere Rerank, Gemini (`google-genai`) for
  embeddings + primary generation, OpenRouter (`openai` SDK against its base_url) as
  generation fallback. Venv at `backend/.venv`, all deps from `requirements.txt`
  installed and confirmed importable.
- DB: local Postgres 18 (`C:\Program Files\PostgreSQL\18\bin`), database `medium_rag`
  created, `vector` extension enabled, all 5 tables created and confirmed via `\dt`.
- Frontend: Next.js App Router — not started yet.
- No test suite in scope (explicit decision).
- **Windows-specific gotcha, already fixed once, will resurface**: psycopg3 async mode
  cannot run under Windows' default `ProactorEventLoop` — every new asyncio entrypoint
  that touches the DB (main.py's runner, eval scripts) must call
  `app.utils.winloop.use_selector_event_loop_on_windows()` before `asyncio.run(...)`,
  same pattern already applied in `backend/init_db.py`.

## ARCHIVE (compressed earlier work)
- Plan went through several revisions during planning (dataset has no body text →
  scrape full text from URLs; free-tier Gemini+OpenRouter failover instead of Azure
  OpenAI; parent-child chunking; multi-turn chat with query rewriting; SSE streaming;
  RAGAS + classic retrieval-metric eval dashboard; an external architecture review's
  14 findings mostly accepted — BM25 lock, executor-bound rebuild, ingestion mutex,
  post-scrape cleaner, explicit chunk overlap, shared rate-limiter, pre-first-token
  streaming failover, typed retrieval intermediates, locked eval JSONB schemas,
  correlation-ID logging, SSE reconnect-with-backoff). Two findings explicitly
  rejected: no local cross-encoder reranker fallback (abstain on Cohere failure
  instead), and the protocol layer scoped to `GeneratorProtocol` only.
- User pasted a `.env` from an unrelated prior project ("OmniTest") with a working
  `GOOGLE_API_KEY`/`OPENROUTER_API_KEY` — reused in this project's `backend/.env`.
  That file's comments revealed real free-tier rate-limit behavior (Gemini per-model
  **daily** caps as low as 20/day; OpenRouter free tier 50/day under $10 lifetime
  spend, 1,000/day after) — folded into the plan and model choice
  (`gemini-3.5-flash-lite` / `z-ai/glm-5.2:free`, both already confirmed working).
- Repo had no `.gitignore` and the pasted `.env` was untracked/unprotected — fixed
  first, before anything else.
- Backend scaffold (T1): package layout, `config.py` (`Settings`), `.env`/`.env.example`,
  `GeneratorProtocol`, typed retrieval dataclasses in `schemas/retrieval.py`, all
  `__init__.py` markers including `backend/__init__.py` (so the top-level `eval/`
  scripts can `from backend.app...` when run from repo root). Decision made silently
  here, not yet said to the user outside this file: using `langchain-text-splitters`
  only for `RecursiveCharacterTextSplitter`, not the full `langchain` chain framework
  — our own `IngestionPipeline`/`RetrievalPipeline` classes replace what `langchain`
  chains would do. (`ragas` pulls in full `langchain` transitively anyway — harmless,
  we still don't import or use its chain abstractions ourselves.)
- DB schema (T2): `db/models.py` (`Article`, `ParentChunk`, `Chunk` with
  `Vector(768)` + HNSW cosine index, `IngestionRun`, `EvalRun`), `db/session.py`
  (async engine/sessionmaker), `init_db.py` (creates extension + tables, idempotent).
  **Verified**: ran `init_db.py` against the real `medium_rag` DB, confirmed all 5
  tables exist via `psql \dt`.

## RECENT TASKS (full detail)
- T3 Ingestion leaf modules — `csv_loader.py` (parses the real CSV, handles the
  `DD-MM-YYYY` date format, nullable claps/responses/reading_time/subtitle/publication),
  `cleaner.py` (pure `clean_text`: HTML-unescape, NFKC, strip control chars, collapse
  whitespace, reject below `MIN_TEXT_LENGTH`), `scrape_cache.py` (SQLite-backed,
  keyed by article id, `ScrapeCache.get/put_success/put_failed`), `scraper.py`
  (`Scraper.fetch_text`: semaphore(2) + `RateLimiter` + random jitter + rotating
  User-Agent + tenacity retry + trafilatura extraction), `chunker.py`
  (`split_into_parent_and_child_chunks`: parent splitter no-overlap, child splitter
  `CHILD_CHUNK_OVERLAP`), `embedder.py` (Gemini batched embeddings via
  `asyncio.to_thread`), `utils/rate_limiter.py` (generic async token bucket, reused
  for scraper pacing; eval-time Cohere pacing will reuse the same class later).
  **Verified**: real smoke test — loaded all 2,498 CSV rows correctly, `clean_text`
  correctly rejects short text, `split_into_parent_and_child_chunks` produced sane
  parent/child counts on a real sample. Scraper/embedder logic is NOT live-tested
  (no real HTTP/Gemini calls made — would burn time and API quota; do that
  deliberately in the next session, on a handful of URLs first, not the full 2,498).
- T4 `IngestionPipeline` (`ingestion/pipeline.py`) + `ProgressTracker`
  (`ingestion/progress.py`) + `schemas/ingestion.py`. Orchestrates
  csv_loader → scrape_cache → scraper → cleaner → chunker → embedder → Postgres
  upsert → BM25 rebuild → finalize `ingestion_runs` row. Concurrency guard: `run()`
  checks for an existing `status='running'` row and raises
  `IngestionAlreadyRunningError(active_run_id)` — the route layer (not yet built)
  must turn that into a 409. Deliberately does NOT import `BM25Store` (which doesn't
  exist yet) — `bm25_store` is a duck-typed constructor param (only `.rebuild(rows)`
  is called), so this module is importable and testable independent of the retrieval
  module being finished. **Verified**: `python -c "from app.ingestion.pipeline import
  IngestionPipeline; ..."` succeeds — full import graph is clean. NOT run end-to-end
  (needs `BM25Store.rebuild()` to actually exist, plus live scrape/embed calls).

## CURRENT STATE
- Verified working: Postgres connection + schema (real run against `medium_rag`);
  CSV loading, text cleaning, and chunking logic (real smoke tests, see T3); full
  import graph of every ingestion module including `pipeline.py` (see T4).
- Unverified: scraper against a real Medium URL; embedder against the real Gemini
  API; the full `IngestionPipeline.run()`/`_execute()` end-to-end (blocked on
  `BM25Store` not existing yet — next task).
- Broken: nothing currently broken. (Earlier Windows event-loop issue in `init_db.py`
  is fixed — see STACK/ENV gotcha above, must be reapplied in every new asyncio
  entrypoint.)
- Uncommitted changes in: everything created this session — the entire `backend/`
  tree, `.gitignore`, `.claude/HANDOFF.md`. Nothing has been committed. Do not commit
  without being asked.

## KEY FILES
- Plan file (authoritative spec): `C:\Users\PC\.claude\plans\role-and-context-dazzling-pudding.md`
- `backend/.env` — real values, including `COHERE_API_KEY=` **blank** (user must supply their own; nothing reranker-related can be verified until this is filled in).
- `backend/app/config.py` — `Settings`, loads `.env`.
- `backend/app/db/models.py` — `Article`/`ParentChunk`/`Chunk`(`VECTOR(768)`+HNSW)/`IngestionRun`/`EvalRun`.
- `backend/app/protocols/generator.py` — `GeneratorProtocol`; `try_stream` MUST be a coroutine that fully resolves (including the first chunk) before returning an iterator — not a plain async generator — or pre-first-token failover breaks.
- `backend/app/schemas/retrieval.py` — typed dataclasses every `RetrievalPipeline` stage will consume/produce (`FilterClause`, `DenseResults`, `SparseResults`, `FusedResults`, `ResolvedParents`, `RankedParents`, `Abstain`).
- `backend/app/ingestion/pipeline.py` — `IngestionPipeline`, the orchestrator for the whole ingestion flow; needs `BM25Store` next to be runnable end-to-end.
- `backend/app/ingestion/progress.py` — `ProgressTracker`, in-memory live status mirror for `GET /ingestion/status`.
- `backend/app/utils/rate_limiter.py` — generic `RateLimiter`, reused by scraper and (later) eval-time Cohere pacing.
- `backend/app/utils/winloop.py` — `use_selector_event_loop_on_windows()`, call at the top of every new asyncio entrypoint.
- `backend/init_db.py` — idempotent schema setup script, already run successfully once.

## DECISIONS & CONSTRAINTS
- Plan file is authoritative — don't re-litigate scope (fixed to the one Medium CSV,
  no user-uploads, no Docker, no test suite, no local reranker fallback, protocol
  layer scoped to `GeneratorProtocol` only).
- `langchain-text-splitters` only, not full `langchain`, for the reason above — flag
  to the user in the next session's first response if not already done.
- `GEMINI_CHAT_MODEL=gemini-3.5-flash-lite`, `OPENROUTER_FALLBACK_MODEL=z-ai/glm-5.2:free`,
  `GEMINI_EMBEDDING_DIMS=768` (matches `chunks.embedding VECTOR(768)`) — all set in
  `backend/.env`, don't change without updating the DB column type too.
- `IngestionPipeline` deletes and re-creates all chunks for an article on re-ingestion
  (`ParentChunk` delete cascades to `Chunk` via `ON DELETE CASCADE`) — re-running
  ingestion on an already-scraped article re-embeds it from scratch rather than
  diffing; acceptable at this corpus size.

## NEXT STEP
1. Build `backend/app/retrieval/bm25_store.py` — `BM25Store` class wrapping an
   `asyncio.Lock` guarding both the in-memory `BM25Okapi` object swap and the atomic
   on-disk pickle replace (`os.replace`) together; expose `rebuild(rows)` (called by
   `IngestionPipeline._rebuild_bm25`, must run the actual `BM25Okapi(...)` construction
   via `run_in_executor` so it doesn't block the loop) and a query-path `score(query,
   eligible_chunk_ids)` method that reads the in-memory object without the lock.
2. Then `dense.py`, `fusion.py`, `parent_resolver.py` (dedup by **max**, not sum, fused
   RRF score per parent), `reranker.py` (Cohere only, propagates errors up rather than
   swallowing them), and `retrieval/pipeline.py`'s `RetrievalPipeline` class with the
   named step methods from the plan.
3. Once retrieval compiles and imports cleanly, do a real (not just import-level)
   smoke test: run `IngestionPipeline` against a **small manually-truncated copy** of
   `medium_data.csv` (5-10 rows) to get real scraped/embedded data into Postgres, then
   exercise `RetrievalPipeline` against it before moving to generation/API/frontend.
4. Continue the todo list (generation → API wiring → frontend → eval) per the plan's
   Build Order, checking back against handoff thresholds again once ~10 more files or
   ~40 more tool calls accumulate — this session has already run long, so hand off
   again at the next natural stopping point rather than pushing through everything.

## COMMANDS FOR THE USER TO RUN
- Fill in `COHERE_API_KEY` in `backend/.env` — still blank, blocks reranker/abstention verification.
- No DB setup command needed anymore — `medium_rag` exists and schema is created.

## GOTCHAS
- psycopg3 + Windows `ProactorEventLoop` incompatibility — see STACK/ENV above. Easy to forget in a new script.
- `backend/.env` contains live API keys reused from a different, unrelated project ("OmniTest") — protected by `.gitignore`, never commit it.
- The repo-root `.env` (the original pasted OmniTest one, separate from `backend/.env`) points at a different database (`OmniTest`) — don't confuse the two.
- `eval/` (top-level, sibling to `backend/`) needs repo root on `sys.path` (or `python -m eval.run_eval` from repo root) for `from backend.app...` imports — still untested, nothing in `eval/` written yet.
- The dataset's `subtitle` column has a pre-existing mangled character (`�`) on at least row 1 — confirmed this is in the source CSV itself (file is valid UTF-8 overall), not a parsing bug. Cosmetic only, not worth fixing unless asked.
