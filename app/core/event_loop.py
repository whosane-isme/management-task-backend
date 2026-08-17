from __future__ import annotations

import asyncio
import sys
from collections.abc import Coroutine
from typing import Any


def compatible_event_loop_factory() -> asyncio.AbstractEventLoop:
    """Create an event loop supported by Psycopg on every target platform."""
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()


def run_async[T](coroutine: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine with the database-compatible event loop."""
    with asyncio.Runner(loop_factory=compatible_event_loop_factory) as runner:
        return runner.run(coroutine)
