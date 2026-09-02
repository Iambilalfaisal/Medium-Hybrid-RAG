import asyncio

from app.utils.winloop import use_selector_event_loop_on_windows

use_selector_event_loop_on_windows()

from app.config import settings
from app.ingestion.embedder import Embedder
from app.retrieval.title_index import TitleIndex


async def main() -> None:
    index = TitleIndex(settings.TITLE_INDEX_PATH)
    embedder = Embedder()
    await index.build(embedder)
    print(f"Built title index with {len(index)} titles at {settings.TITLE_INDEX_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
