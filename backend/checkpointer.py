"""Async SQLite checkpointer for LangGraph dev server."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Ensure the data directory exists before the async SQLite driver opens the file.
CHECKPOINT_DIR = Path(__file__).resolve().parent / "data"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def generate_checkpointer() -> AsyncIterator[AsyncSqliteSaver]:
    """Yield an AsyncSqliteSaver backed by a local SQLite file.

    LangGraph dev server calls this context manager to obtain the checkpointer
    used for thread persistence.
    """
    db_path = CHECKPOINT_DIR / "langgraph.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        yield saver
