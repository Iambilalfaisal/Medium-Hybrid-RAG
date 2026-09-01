import asyncio
import sys


def use_selector_event_loop_on_windows() -> None:
    """psycopg3's async mode cannot run under Windows' default ProactorEventLoop.
    Call this before any asyncio.run()/uvicorn.run() that touches the DB — every
    entrypoint (init_db.py, main.py's runner, eval scripts) needs it, not just one."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
