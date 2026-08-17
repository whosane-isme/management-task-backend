from __future__ import annotations

import asyncio
import sys

from app.core.event_loop import compatible_event_loop_factory, run_async


def test_compatible_event_loop_can_run_coroutine() -> None:
    async def current_loop() -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    loop = run_async(current_loop())

    assert loop.is_closed()
    if sys.platform == "win32":
        assert isinstance(loop, asyncio.SelectorEventLoop)


def test_event_loop_factory_returns_an_open_loop() -> None:
    loop = compatible_event_loop_factory()
    try:
        assert not loop.is_closed()
    finally:
        loop.close()
