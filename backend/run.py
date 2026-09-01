"""Entrypoint (not `uvicorn main:app` directly). Setting an event loop POLICY
(app.utils.winloop) is not enough for uvicorn specifically: uvicorn's own
loop-factory selection hard-codes ProactorEventLoop on Windows whenever
use_subprocess is False (see uvicorn.loops.asyncio.asyncio_loop_factory), which
overrides any policy we set beforehand — psycopg3's async mode still breaks under
it. The `loop="asyncio:SelectorEventLoop"` argument below is what actually fixes it
for uvicorn: it points uvicorn's loop factory straight at SelectorEventLoop instead
of going through its own Windows auto-selection.

`reload=True` is deliberately not used: uvicorn's reloader runs the server in a
subprocess that re-imports the app independently, which could reintroduce this same
problem in a way this fix doesn't reach. Restart manually after changes.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, loop="asyncio:SelectorEventLoop")
