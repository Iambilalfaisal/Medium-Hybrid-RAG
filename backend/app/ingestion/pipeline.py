import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import Article, Chunk, IngestionRun, ParentChunk
from app.ingestion.chunker import split_into_parent_and_child_chunks
from app.ingestion.cleaner import clean_text
from app.ingestion.csv_loader import load_rows
from app.ingestion.embedder import Embedder
from app.ingestion.progress import ProgressTracker
from app.ingestion.scrape_cache import ScrapeCache
from app.ingestion.scraper import Scraper, ScrapeError


class IngestionAlreadyRunningError(Exception):
    def __init__(self, active_run_id: int):
        self.active_run_id = active_run_id
        super().__init__(f"Ingestion run {active_run_id} is already in progress")


class IngestionPipeline:
    """Constructed once with injected dependencies (not module-level singletons), per
    the plan's testability/clarity rationale. `bm25_store` is duck-typed here
    (only `.rebuild(rows)` is called) rather than imported for a type hint, so this
    module doesn't need retrieval/bm25_store.py to exist to be importable on its own.
    Guards against a second concurrent run via ingestion_runs.status; the BM25 rebuild
    at the end must run off the event loop (bm25_store.rebuild is expected to do that
    itself) so it never blocks concurrent /chat requests.
    """

    def __init__(self, session_factory, scrape_cache: ScrapeCache, embedder: Embedder, scraper: Scraper, bm25_store, progress: ProgressTracker):
        self._session_factory = session_factory
        self._scrape_cache = scrape_cache
        self._embedder = embedder
        self._scraper = scraper
        self._bm25_store = bm25_store
        self._progress = progress

    async def run(self, force_rescrape: bool = False) -> int:
        async with self._session_factory() as session:
            active = await session.scalar(select(IngestionRun).where(IngestionRun.status == "running"))
            if active is not None:
                raise IngestionAlreadyRunningError(active.id)

            run = IngestionRun(started_at=datetime.now(timezone.utc), status="running")
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        asyncio.create_task(self._execute(run_id, force_rescrape))
        return run_id

    async def _execute(self, run_id: int, force_rescrape: bool) -> None:
        rows = list(load_rows())
        await self._progress.start(run_id, articles_total=len(rows))

        scraped_ok = skipped = cleaner_rejected = chunks_created = 0

        try:
            for row in rows:
                if not force_rescrape and await self._already_ingested(row.id):
                    scraped_ok += 1
                    await self._progress.increment(articles_processed=1, articles_scraped_ok=1)
                    continue

                await self._progress.update(current_stage="scraping")
                text = await self._get_article_text(row, force_rescrape)

                if text is None:
                    skipped += 1
                    await self._progress.increment(articles_processed=1, articles_skipped=1)
                    continue

                cleaned = clean_text(text)
                if cleaned is None:
                    cleaner_rejected += 1
                    skipped += 1
                    await self._progress.increment(
                        articles_processed=1, articles_skipped=1, cleaner_rejected_count=1
                    )
                    continue

                await self._progress.update(current_stage="chunking+embedding")
                n_chunks = await self._chunk_embed_store(row, cleaned)
                chunks_created += n_chunks
                scraped_ok += 1
                await self._progress.increment(
                    articles_processed=1, articles_scraped_ok=1, chunks_created=n_chunks
                )

            await self._progress.update(current_stage="rebuilding BM25 index")
            await self._rebuild_bm25()

            await self._finalize(run_id, "completed", len(rows), scraped_ok, skipped, cleaner_rejected, chunks_created)
            await self._progress.finish("completed")
        except Exception as exc:  # top-level run guard: a failure here must still finalize the run row
            await self._finalize(run_id, "failed", len(rows), scraped_ok, skipped, cleaner_rejected, chunks_created)
            await self._progress.finish("failed", error=str(exc))
        # Deliberately no scraper.aclose() here: IngestionPipeline is a long-lived
        # singleton reused across runs (see api/deps.py) — closing the shared httpx
        # client after the first run would break every run after it. The client is
        # closed once at app shutdown instead (see main.py's lifespan).

    async def _already_ingested(self, article_id: str) -> bool:
        """Lets an interrupted run (embedding-provider quota exhausted mid-run, crash,
        manual stop) resume cheaply: articles that already have chunks are skipped
        entirely rather than re-scraped and re-embedded — a scarce free-tier embed
        budget can't afford to redo already-finished work on every retry."""
        async with self._session_factory() as session:
            result = await session.execute(select(Chunk.id).where(Chunk.article_id == article_id).limit(1))
            return result.first() is not None

    async def _get_article_text(self, row, force_rescrape: bool) -> str | None:
        if not force_rescrape:
            cached = await self._scrape_cache.get(row.id)
            if cached is not None:
                return cached.text if cached.status == "success" else None

        try:
            text = await self._scraper.fetch_text(row.url)
        except (ScrapeError, Exception) as exc:
            await self._scrape_cache.put_failed(row.id, row.url, str(exc))
            return None

        await self._scrape_cache.put_success(row.id, row.url, text)
        return text

    async def _chunk_embed_store(self, row, text: str) -> int:
        parent_child_pairs = split_into_parent_and_child_chunks(text)
        chunk_count = 0

        async with self._session_factory() as session:
            article = await session.get(Article, row.id) or Article(id=row.id, scraped_at=datetime.now(timezone.utc))
            article.url = row.url
            article.title = row.title
            article.subtitle = row.subtitle
            article.claps = row.claps
            article.responses = row.responses
            article.reading_time = row.reading_time
            article.publication = row.publication
            article.published_date = row.published_date
            article.scraped_at = datetime.now(timezone.utc)
            article.full_text_len = len(text)
            session.add(article)
            await session.flush()

            # Re-ingestion / force_rescrape: drop this article's old chunks first.
            # ON DELETE CASCADE on chunks.parent_id takes the children with it.
            await session.execute(ParentChunk.__table__.delete().where(ParentChunk.article_id == article.id))

            parents = []
            for parent_index, (parent_text, _) in enumerate(parent_child_pairs):
                parent = ParentChunk(article_id=article.id, chunk_index=parent_index, text=parent_text)
                session.add(parent)
                parents.append(parent)
            await session.flush()

            # One batched embed call per article instead of one per parent chunk —
            # the API accepts many texts per call, so this cuts the request count by
            # roughly the average number of parent chunks per article. Matters more
            # now than it used to: the embedding provider's free-tier call budget is
            # the actual bottleneck for ingesting the full dataset, not article count.
            all_child_texts = [t for _, child_texts in parent_child_pairs for t in child_texts]
            all_embeddings = await self._embedder.embed_texts(all_child_texts)

            offset = 0
            for parent, (_, child_texts) in zip(parents, parent_child_pairs):
                embeddings = all_embeddings[offset : offset + len(child_texts)]
                offset += len(child_texts)
                for child_index, (child_text, embedding) in enumerate(zip(child_texts, embeddings)):
                    session.add(
                        Chunk(
                            parent_id=parent.id,
                            article_id=article.id,
                            chunk_index=child_index,
                            text=child_text,
                            embedding=embedding,
                        )
                    )
                    chunk_count += 1

            await session.commit()

        return chunk_count

    async def _rebuild_bm25(self) -> None:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        Chunk.id,
                        Chunk.text,
                        Chunk.article_id,
                        Article.claps,
                        Article.publication,
                        Article.published_date,
                        Article.reading_time,
                    ).join(Article, Article.id == Chunk.article_id)
                )
            ).all()

        await self._bm25_store.rebuild(rows)

    async def _finalize(self, run_id: int, status: str, total: int, scraped_ok: int, skipped: int, cleaner_rejected: int, chunks_created: int) -> None:
        async with self._session_factory() as session:
            run = await session.get(IngestionRun, run_id)
            run.status = status
            run.finished_at = datetime.now(timezone.utc)
            run.articles_total = total
            run.articles_scraped_ok = scraped_ok
            run.articles_skipped = skipped
            run.cleaner_rejected_count = cleaner_rejected
            run.chunks_created = chunks_created
            await session.commit()
