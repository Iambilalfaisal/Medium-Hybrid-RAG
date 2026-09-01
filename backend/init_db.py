"""One-off script: create the pgvector extension and all tables on the configured
database. Safe to re-run (CREATE EXTENSION IF NOT EXISTS, create_all only creates
missing tables). Run from backend/: `python init_db.py`.
"""

import asyncio

from sqlalchemy import text

from app.utils.winloop import use_selector_event_loop_on_windows

use_selector_event_loop_on_windows()

from app.db.models import Base
from app.db.session import engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    print("Schema ready: vector extension enabled, tables created.")


if __name__ == "__main__":
    asyncio.run(main())
