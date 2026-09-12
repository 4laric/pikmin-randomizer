import asyncio
import json
import tempfile
import unittest
from pathlib import Path
import pytest
import websockets
from randomizer.seed import generate, validate
from randomizer.session import Session, death_link_summary
from randomizer.runner import NativeRun, ap_connect
from randomizer.catalog import ITEM_IDS, REPAIR


def test_manifest_contract():
    m = generate('dl', 'ap', death_link=True, death_link_pikmin=7)
    assert m['death_link'] is True and m['death_link_pikmin'] == 7 and 'death-link-v1' in m['capabilities']
    assert m['schema'] == 9  # Death link implies modern collection checks.
    plain = generate('dl', 'ap')
    assert 'death_link' not in plain and 'death-link-v1' not in plain['capabilities']
    for bad in (dict(death_link=True, death_link_pikmin=0), dict(death_link=True, death_link_pikmin=101), dict(death_link='yes')):
        with pytest.raises(ValueError):
            generate('dl', 'ap', **bad)
    broken = dict(m); broken['death_link_pikmin'] = 0
    with pytest.raises(ValueError):
        validate(broken)
    broken = dict(m); del broken['death_link']
    with pytest.raises(ValueError):
        validate(broken)
    broken = dict(m); broken['capabilities'] = [c for c in m['capabilities'] if c != 'death-link-v1']
    with pytest.raises(ValueError):
        validate(broken)


def test_native_contract_and_journal(tmp_path):
    m = generate('dl', 'ap', death_link=True, death_link_pikmin=5)
    s = Session(m, tmp_path); s.bind_ap('test', 0, 1)
    assert s.data['pikmin_deaths'] == 0 and s.data['death_links_received'] == 0
    r = NativeRun(s)
    assert 'DEATHLINK 5\n' in r.bootstrap.read_text()
    assert s.native_state(r.token, True).endswith(' DEATHLINK 0 END\n')
    s.receive_death_link()
    assert s.native_state(r.token, True).endswith(' DEATHLINK 1 END\n')
    (r.directory / 'hello.txt').write_text(' '.join(['PIKMIN_HELLO', '9', r.token, s.fingerprint, *m['capabilities'], 'END']))
    journal = r.directory / 'deaths.txt'
    journal.write_text('1\n2\n3\n4')  # Incomplete last record is ignored.
    r.poll()
    assert s.data['pikmin_deaths'] == 3
    journal.write_text('1\n2\n3\n4\n5\n6\n7\n')
    r.poll(); r.poll()
    assert s.data['pikmin_deaths'] == 7
    reloaded = Session(m, tmp_path)
    assert reloaded.data['pikmin_deaths'] == 7 and reloaded.data['death_links_received'] == 1
    assert '7 deaths' not in death_link_summary(m, reloaded.data)
    assert death_link_summary(m, reloaded.data) == 'DeathLink 5-Pikmin units: received 1, sent 1, 2/5 deaths toward the next'
    journal.write_text('1\n2\n')
    with pytest.raises(ValueError):
        r.poll()


def test_disabled_seed_rejects_death_state(tmp_path):
    m = generate('plain', 'ap')
    s = Session(m, tmp_path)
    assert 'pikmin_deaths' not in s.data and 'DEATHLINK' not in s.native_state('0' * 64, True)
    with pytest.raises(ValueError):
        s.receive_death_link()
    r = NativeRun(s)
    (r.directory / 'hello.txt').write_text(' '.join(['PIKMIN_HELLO', str(m['schema']), r.token, s.fingerprint, *m['capabilities'], 'END']))
    (r.directory / 'deaths.txt').write_text('1\n')
    r.poll()  # Ignored: no death link in this seed.


class DeathLinkProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_bounce_send_receive_echo_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = generate('dl-protocol', 'ap', death_link=True, death_link_pikmin=3)
            session = Session(m, Path(tmp))
            session.data['pikmin_deaths'] = 4  # One stale link (3) plus a remainder before connecting.
            session.save()
            received = []; ready = [False]; done = asyncio.Event(); sent_time = []
            async def server(ws):
                await ws.send(json.dumps([dict(cmd='RoomInfo', seed_name='room')]))
                connect = json.loads(await ws.recv())[0]
                self.assertEqual(connect['tags'], ['AP', 'DeathLink'])
                await ws.send(json.dumps([dict(cmd='Connected', team=0, slot=1,
                    slot_data=dict(manifest=session.manifest, manifest_fingerprint=session.fingerprint))]))
                self.assertEqual(json.loads(await ws.recv()), [{'cmd': 'Sync'}])
                await ws.send(json.dumps([dict(cmd='ReceivedItems', index=0, items=[])]))
                # A link from another player, then one before authentication would have been dropped.
                await ws.send(json.dumps([dict(cmd='Bounced', tags=['DeathLink'], data=dict(time=1.0, source='Other', cause='Other died'))]))
                while session.data['death_links_received'] < 1:
                    await asyncio.sleep(0.05)
                # Reaching the threshold sends exactly one Bounce, without the stale offline link.
                session.data['pikmin_deaths'] = 6; session.save()
                packet = json.loads(await ws.recv())[0]
                self.assertEqual(packet['cmd'], 'Bounce'); self.assertEqual(packet['tags'], ['DeathLink'])
                self.assertEqual(packet['data']['source'], 'Player1')
                sent_time.append(packet['data']['time'])
                received.append(packet)
                # Server echo of our own link and a repeat from ourselves are ignored.
                await ws.send(json.dumps([dict(cmd='Bounced', tags=['DeathLink'], data=packet['data']),
                                          dict(cmd='Bounced', tags=['DeathLink'], data=dict(time=2.0, source='Player1', cause='x')),
                                          dict(cmd='Bounced', tags=['Other'], data=dict(time=3.0, source='Other'))]))
                session.data['pikmin_deaths'] = 12; session.save()  # Two more units at once.
                for _ in range(2):
                    received.append(json.loads(await ws.recv())[0])
                done.set()
                await ws.wait_closed()
            async with websockets.serve(server, '127.0.0.1', 0) as host:
                task = asyncio.create_task(ap_connect(session, f"ws://127.0.0.1:{host.sockets[0].getsockname()[1]}", None, ready))
                try:
                    await asyncio.wait_for(done.wait(), 5)
                    self.assertEqual(session.data['death_links_received'], 1)
                    self.assertEqual([p['cmd'] for p in received], ['Bounce'] * 3)
                    self.assertTrue(ready[0])
                finally:
                    task.cancel(); await asyncio.gather(task, return_exceptions=True)
