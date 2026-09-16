"""Real SQLite atomic planning scope fencing, without a live workflow registry."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from workflow.handoff import Rejected
from workflow.planner_claims import canonical_resource, claim, inspect_claims, release
from workflow.registry import Registry


class PlanningClaimsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.reg = Registry(self.root/'output/registry.sqlite3', self.root,
                            process_probe=lambda p: p.get('health', 'unknown'))
        self.reg.init()
        self.coordinator = {'lane': 'acceptance-backlog-planner', 'generation': 1}
        with self.reg.transaction() as state:
            for name in ('a', 'b', 'acceptance-backlog-planner'):
                state['lanes'][name] = dict(lane=name, generation=1, state='running',
                    process=dict(host='fixture', pid=100 + len(state['lanes']), started='1', health='alive'))
        path = self.root/'output/disposition.txt'
        path.write_text('Proposal reviewed and accepted into manifest')
        self.evidence = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def stop(self, health='dead', state='review_ready'):
        with self.reg.transaction() as registry:
            registry['lanes']['a']['process']['health'] = health
            registry['lanes']['a']['state'] = state
            # Probe uses fixture health rather than changing real OS state.
            for item in registry.get('planning_claims', {}).values():
                if item['lane'] == 'a':
                    item['process']['health'] = health

    def dispose(self, keys=None):
        return release(self.reg, 'a', 1, keys or ['topic:enemy-9'],
                       coordinator=self.coordinator, disposition=self.evidence)

    def test_aliases_file_ancestors_and_batch_rollback(self):
        claim(self.reg, 'a', 1, ['FILE:Native\\PC_Port', 'issue:00132'])
        self.assertEqual(canonical_resource('issue:00132'), 'issue:132')
        for keys in (['topic:new', 'file:native/pc_port/foo.cpp'], ['issue:132'], ['file:native']):
            with self.assertRaises(Rejected):
                claim(self.reg, 'b', 1, keys)
        self.assertEqual(len(inspect_claims(self.reg)), 2)
        for value in ('file:C:/foo', 'file:a/../b', 'file:a//b', 'file:a.', 'file:/foo', 'issue:0'):
            with self.assertRaises(Rejected):
                canonical_resource(value)

    def test_replay_stale_generation_no_expiry(self):
        original = claim(self.reg, 'a', 1, ['topic:enemy-9'])
        self.reg.clock = lambda: 10**12
        self.assertEqual(claim(self.reg, 'a', 1, ['TOPIC:ENEMY-9']), original)
        with self.assertRaises(Rejected):
            claim(self.reg, 'b', 1, ['topic:enemy-9'])
        with self.reg.transaction() as state:
            state['lanes']['a']['generation'] = 2
        for generation in (1, 2):
            with self.assertRaises(Rejected):
                claim(self.reg, 'a', generation, ['topic:enemy-9'])

    def test_race_has_one_winner(self):
        def attempt(lane):
            try:
                claim(self.reg, lane, 1, ['provider:saves', 'topic:shared'])
                return True
            except Rejected:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sum(executor.map(attempt, ('a', 'b'))), 1)
        self.assertEqual(len({v['lane'] for v in inspect_claims(self.reg)}), 1)

    def test_live_owner_release_and_batch_conflict(self):
        claim(self.reg, 'a', 1, ['topic:a'])
        claim(self.reg, 'b', 1, ['topic:b'])
        with self.assertRaises(Rejected):
            release(self.reg, 'a', 1, ['topic:a', 'topic:b'])
        self.assertEqual(len(inspect_claims(self.reg)), 2)
        self.assertEqual(release(self.reg, 'a', 1, ['topic:a']), {'released': ['topic:a']})
        self.assertEqual(release(self.reg, 'a', 1, ['topic:a']), {'released': []})

    def test_coordinator_disposition_stopped_terminal_and_hash(self):
        claim(self.reg, 'a', 1, ['topic:enemy-9'])
        with self.assertRaises(Rejected):
            self.dispose()
        self.stop(health='unknown')
        with self.assertRaises(Rejected):
            self.dispose()
        self.stop(state='blocked')
        with self.assertRaises(Rejected):
            self.dispose()
        self.stop()
        with self.assertRaises(Rejected):
            release(self.reg, 'a', 1, ['topic:enemy-9'])
        good = copy.deepcopy(self.evidence)
        self.evidence['sha256'] = '0'*64
        with self.assertRaises(Rejected):
            self.dispose()
        self.evidence = good
        self.assertEqual(self.dispose(), {'released': ['topic:enemy-9']})
        claim(self.reg, 'b', 1, ['topic:enemy-9'])

    def test_protected_children_and_launches_fence_disposition(self):
        claim(self.reg, 'a', 1, ['topic:enemy-9'])
        self.stop()
        for group in ('leases', 'queue'):
            with self.reg.transaction() as state:
                state[group]['protected'] = dict(lane='a', process={'health': 'alive'})
            with self.assertRaises(Rejected):
                self.dispose()
            with self.reg.transaction() as state:
                state[group].clear()
        with self.reg.transaction() as state:
            state['control'] = {'launches': {'x': {'lane': 'a', 'status': 'intent'}}}
        with self.assertRaises(Rejected):
            self.dispose()
        with self.reg.transaction() as state:
            state['control']['launches'].clear()
        self.dispose()

    def test_coordinator_identity_and_generation_fenced(self):
        claim(self.reg, 'a', 1, ['topic:enemy-9'])
        self.stop()
        for identity in ({'lane': 'b', 'generation': 1},
                         {'lane': 'acceptance-backlog-planner', 'generation': 2}):
            self.coordinator = identity
            with self.assertRaises(Rejected):
                self.dispose()
        self.assertEqual(len(inspect_claims(self.reg)), 1)

    def test_dead_and_unknown_claimants_rejected(self):
        for health in ('dead', 'unknown'):
            self.stop(health=health, state='running')
            with self.assertRaises(Rejected):
                claim(self.reg, 'a', 1, ['topic:enemy-9'])


if __name__ == '__main__':
    unittest.main()
