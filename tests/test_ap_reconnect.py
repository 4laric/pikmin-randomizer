import asyncio
import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from randomizer.runner import serve


class APReconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_eof_handshake_retries_without_releasing_native(self):
        attempts = 0
        retried = asyncio.Event()
        states = []

        async def reject(reader, writer):
            nonlocal attempts
            await reader.read(4096)
            attempts += 1
            writer.close()
            await writer.wait_closed()
            if attempts >= 2:
                retried.set()

        session = SimpleNamespace(manifest={"mode": "ap"}, goal=False, death_link_unit=0)
        run = SimpleNamespace(handshaken=True, poll=lambda: None,
                              write_state=states.append)
        output = io.StringIO()
        async with await asyncio.start_server(reject, "127.0.0.1", 0) as host:
            port = host.sockets[0].getsockname()[1]
            with redirect_stdout(output):
                task = asyncio.create_task(serve(session, run, server=f"ws://127.0.0.1:{port}"))
                try:
                    await asyncio.wait_for(retried.wait(), 5)
                    self.assertFalse(task.done())
                    self.assertTrue(states)
                    self.assertFalse(any(states))
                finally:
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
        self.assertFalse(states[-1])
        self.assertIn("AP connection handshake failed", output.getvalue())
        self.assertIn("ws:// or wss://", output.getvalue())

    async def test_retry_can_recover_and_release_native(self):
        from websockets.exceptions import InvalidMessage
        attempts = 0
        released = asyncio.Event()
        states = []

        async def connect(session, server, password, ready):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise InvalidMessage("did not receive a valid HTTP response")
            ready[0] = True
            await asyncio.Future()

        def write_state(ready):
            states.append(ready)
            if ready:
                released.set()

        session = SimpleNamespace(manifest={"mode": "ap"}, goal=False, death_link_unit=0)
        run = SimpleNamespace(handshaken=True, poll=lambda: None, write_state=write_state)
        with patch("randomizer.runner.ap_connect", side_effect=connect), redirect_stdout(io.StringIO()):
            task = asyncio.create_task(serve(session, run, server="unused"))
            try:
                await asyncio.wait_for(released.wait(), 5)
                self.assertEqual(attempts, 2)
                self.assertFalse(states[0])
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        self.assertFalse(states[-1])

    async def test_protocol_validation_is_fatal(self):
        session = SimpleNamespace(manifest={"mode": "ap"}, goal=False, death_link_unit=0)
        states = []
        run = SimpleNamespace(handshaken=True, poll=lambda: None, write_state=states.append)
        with patch("randomizer.runner.ap_connect", side_effect=ValueError("slot manifest mismatch")) as connect:
            with self.assertRaisesRegex(ValueError, "slot manifest mismatch"):
                await asyncio.wait_for(serve(session, run, server="unused"), 2)
            self.assertEqual(connect.call_count, 1)
        self.assertFalse(any(states))

