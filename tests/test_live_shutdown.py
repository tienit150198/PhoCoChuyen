"""Release async PostgreSQL listener registrations before closing its socket."""
import asyncio
import unittest
from unittest.mock import AsyncMock

from live.app import App
from live.config import Config


class ShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_closes_after_background_listener_finishes(self):
        app = App(Config())
        started = asyncio.Event()
        released = asyncio.Event()

        async def listener():
            started.set()
            try:
                await asyncio.Future()
            finally:
                # Socket readers finish asynchronous cleanup after cancellation.
                await asyncio.sleep(0)
                released.set()

        task = asyncio.create_task(listener())
        app.bg = [task]
        await started.wait()

        async def close_database():
            self.assertTrue(released.is_set(), 'database socket closed while listener still uses it')
            self.assertTrue(task.done())

        app.db = AsyncMock()
        app.db.close.side_effect = close_database
        try:
            await app.stop()
            app.db.close.assert_awaited_once()
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
