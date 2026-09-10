import asyncio
import json
import tempfile
import unittest
from pathlib import Path
import websockets
from randomizer.catalog import ITEM_IDS, REPAIR, LOCATION_IDS, NAMES
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import ap_connect


class APProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_auth_receipts_check_replay_and_goal(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Session(generate("ap-protocol", "ap"), Path(tmp))
            session.collect(NAMES[0])
            received = []; ready = [False]; done = asyncio.Event()
            async def server(ws):
                await ws.send(json.dumps([dict(cmd="RoomInfo", seed_name="room")]))
                connect = json.loads(await ws.recv())[0]
                self.assertEqual(connect["game"], "Pikmin Randomizer")
                self.assertEqual(connect["items_handling"], 7)
                await ws.send(json.dumps([dict(cmd="Connected", team=0, slot=1,
                    slot_data=dict(manifest=session.manifest, manifest_fingerprint=session.fingerprint))]))
                self.assertEqual(json.loads(await ws.recv()), [{"cmd": "Sync"}])
                self.assertFalse(ready[0])
                items = [dict(item=ITEM_IDS[REPAIR], location=0, player=2, flags=1)] * 25
                await ws.send(json.dumps([dict(cmd="ReceivedItems", index=0, items=items),
                                          dict(cmd="ReceivedItems", index=0, items=items)]))
                while len(received) < 2:
                    received.extend(json.loads(await ws.recv()))
                done.set()
                await ws.wait_closed()
            async with websockets.serve(server, "127.0.0.1", 0) as host:
                task = asyncio.create_task(ap_connect(session, f"ws://127.0.0.1:{host.sockets[0].getsockname()[1]}", None, ready))
                try:
                    await asyncio.wait_for(done.wait(), 5)
                    self.assertTrue(ready[0]);self.assertTrue(session.goal)
                    self.assertEqual(session.inventory[REPAIR], 25)
                    self.assertIn(dict(cmd="LocationChecks", locations=[LOCATION_IDS[NAMES[0]]]), received)
                    self.assertIn(dict(cmd="StatusUpdate", status=30), received)
                finally:
                    task.cancel(); await asyncio.gather(task, return_exceptions=True)

    async def test_wrong_slot_manifest_never_releases_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Session(generate("ap-protocol", "ap"), Path(tmp)); ready = [False]
            async def server(ws):
                await ws.send(json.dumps([dict(cmd="RoomInfo", seed_name="wrong-room")]))
                await ws.recv()
                await ws.send(json.dumps([dict(cmd="Connected", team=0, slot=1, slot_data={})]))
                await ws.wait_closed()
            async with websockets.serve(server, "127.0.0.1", 0) as host:
                with self.assertRaises(ValueError):
                    await ap_connect(session, f"ws://127.0.0.1:{host.sockets[0].getsockname()[1]}", None, ready)
            self.assertFalse(ready[0]);self.assertIsNone(session.data["ap_identity"])
