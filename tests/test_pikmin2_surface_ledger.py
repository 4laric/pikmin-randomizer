"""Surface/cave exactly-once handoffs without native assets or a surface scene."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_campaign import entry_text, validate as validate_cave
from experimental.pikmin2_surface_ledger import SurfaceLedger, validate
from randomizer.session import SessionLock

CONTENT, CAMPAIGN, TRIP = 'a'*64, 'b'*32, 'c'*32


def snapshot():
    return dict(region='valley_of_repose', day=3, time=11.25, position=[100, 25, -90],
                squad=[dict(species='red', maturity=i % 3) for i in range(20)],
                health=.8, receipts={'surface:treasure:carrot':100})


def native_handoff(state, squad=None, health=.7):
    checkpoint = deepcopy(state['trip']['checkpoint'])
    checkpoint['health'] = health
    if squad is not None:
        checkpoint['squad'] = squad
    return entry_text(checkpoint, state['trip']['token']).replace('P2_CAVE_ENTRY_1', 'P2_CAVE_TRANSFER_1')


class SurfaceLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.ledger = SurfaceLedger(self.directory, CONTENT, CAMPAIGN)
        self.start = self.ledger.create(snapshot())

    def enter(self):
        return self.ledger.enter_cave(0, TRIP)

    def floor1(self, entered):
        crew = deepcopy(entered['trip']['checkpoint']['squad'][:19])
        receipts = dict(snapshot()['receipts'], **{'treasure:citrus':180})
        text = native_handoff(entered, crew)
        state = self.ledger.apply_floor(1, entered['trip']['token'], text, receipts, {'treasure:citrus':180})
        return state, text, receipts

    def exited(self):
        entered = self.enter()
        floor2, _, receipts = self.floor1(entered)
        crew = deepcopy(floor2['trip']['checkpoint']['squad'])
        for p in crew[:10]: p['species'] = 'purple'
        receipts = dict(receipts, **{'treasure:atlas':200})
        return self.ledger.apply_floor(2, floor2['trip']['token'], native_handoff(floor2, crew, .6),
                                       receipts, {'treasure:atlas':200})

    def test_roundtrip_preserves_destination_and_applies_survivors_once(self):
        exited = self.exited()
        self.assertEqual(exited['phase'], 'return_ready')
        self.assertEqual(exited['surface'], snapshot()) # Still suspended, no half-applied gains.
        result = self.ledger.return_to_surface(3, TRIP)
        self.assertEqual((result['phase'], result['revision'], result['trip']), ('surface', 4, None))
        for field in ('region', 'day', 'time', 'position'):
            self.assertEqual(result['surface'][field], snapshot()[field])
        self.assertEqual(len(result['surface']['squad']), 19)
        self.assertEqual(sum(p['species']=='purple' for p in result['surface']['squad']), 10)
        self.assertEqual([p['maturity'] for p in result['surface']['squad']], [i%3 for i in range(19)])
        self.assertEqual(result['surface']['health'], .6)
        self.assertEqual(sum(result['surface']['receipts'].values()), 480)
        self.assertEqual(self.ledger.return_to_surface(3, TRIP), result)
        self.assertEqual(SurfaceLedger(self.directory, CONTENT, CAMPAIGN).read(), result)
        # Replaying initial creation does not restore the original squad or erase earnings.
        self.assertEqual(self.ledger.create(snapshot()), result)

    def test_floor_replay_retains_next_token_and_cannot_duplicate_reward(self):
        entered = self.enter()
        validate_cave(entered['trip']['checkpoint'])
        floor2, text, receipts = self.floor1(entered)
        replay = self.ledger.apply_floor(1, entered['trip']['token'], text, receipts, {'treasure:citrus':180})
        self.assertEqual(replay, floor2)
        self.assertNotEqual(entered['trip']['token'], floor2['trip']['token'])
        self.assertEqual(self.ledger.enter_cave(0, TRIP), floor2)
        with self.assertRaisesRegex(ValueError, 'Conflicting replay'):
            self.ledger.apply_floor(1, entered['trip']['token'], text, {'treasure:citrus':181}, {'treasure:citrus':181})

    def test_interrupted_entry_floor_and_return_leave_entire_previous_state(self):
        with patch('randomizer.session.os.replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError): self.enter()
        self.assertEqual(self.ledger.read(), self.start)
        entered = self.enter()
        with patch('randomizer.session.os.replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError): self.floor1(entered)
        self.assertEqual(self.ledger.read(), entered)
        floor2, _, receipts = self.floor1(entered)
        exited = self.ledger.apply_floor(2, floor2['trip']['token'], native_handoff(floor2), receipts, {})
        with patch('randomizer.session.os.replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError): self.ledger.return_to_surface(3, TRIP)
        self.assertEqual(self.ledger.read(), exited)
        self.assertEqual(self.ledger.return_to_surface(3, TRIP)['phase'], 'surface')

    def test_failed_cave_stays_failed_without_replenishing_surface(self):
        entered = self.enter()
        token = entered['trip']['token']
        text = f'P2_CAVE_TRANSFER_1\n{token}\n1 0 0\n'
        failed = self.ledger.apply_floor(1, token, text, snapshot()['receipts'], {})
        self.assertEqual(failed['phase'], 'failed')
        self.assertEqual(failed['trip']['checkpoint']['squad'], [])
        with self.assertRaisesRegex(ValueError, 'No successful'):
            self.ledger.return_to_surface(2, TRIP)
        with self.assertRaisesRegex(ValueError, 'already suspended'):
            self.ledger.enter_cave(2, 'd'*32)
        self.assertEqual(self.ledger.read(), failed)

    def test_conflicting_identity_and_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, 'different content/campaign'):
            SurfaceLedger(self.directory, 'd'*64, CAMPAIGN).read()
        with self.assertRaisesRegex(ValueError, 'different content/campaign'):
            SurfaceLedger(self.directory, CONTENT, 'd'*32).read()
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.ledger.enter_cave(1, TRIP)
        altered = snapshot(); altered['day'] += 1
        with self.assertRaisesRegex(ValueError, 'Conflicting initial'):
            self.ledger.create(altered)
        entered = self.enter()
        with self.assertRaisesRegex(ValueError, 'Conflicting replay'):
            self.ledger.enter_cave(1, TRIP)
        with self.assertRaisesRegex(ValueError, 'Wrong or stale'):
            self.ledger.apply_floor(1, 'e'*32, native_handoff(entered), snapshot()['receipts'], {})

    def test_concurrent_session_writer_is_rejected(self):
        with SessionLock(self.directory):
            with self.assertRaisesRegex(ValueError, 'another runner'):
                self.enter()
        self.assertEqual(self.ledger.read(), self.start)

    def test_untrusted_native_receipts_and_incomplete_return_rejected(self):
        entered = self.enter()
        with self.assertRaisesRegex(ValueError, 'Unexpected cave receipt'):
            self.ledger.apply_floor(1, entered['trip']['token'], native_handoff(entered),
                                   dict(snapshot()['receipts'], **{'unknown':500}), {})
        with self.assertRaisesRegex(ValueError, 'No successful'):
            self.ledger.return_to_surface(1, TRIP)
        self.assertEqual(self.ledger.read(), entered)

    def test_missing_corrupt_and_duplicate_ledger_never_reset(self):
        self.ledger.path.write_text('{"schema":1,"schema":1}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'): self.ledger.read()
        self.ledger.path.write_text('{')
        with self.assertRaises(ValueError): self.ledger.create(snapshot())
        self.ledger.path.unlink()
        (self.directory/'surface-ledger.json.tmp').write_text('interrupted candidate')
        with self.assertRaisesRegex(ValueError, 'Missing ledger'): self.ledger.create(snapshot())

    def test_validation_and_caller_mutation_cannot_change_saved_state(self):
        changed = deepcopy(self.start); changed['surface']['position'][0] = float('nan')
        with self.assertRaises(ValueError): validate(changed)
        changed = deepcopy(self.start); changed['revision'] = True
        with self.assertRaises(ValueError): validate(changed)
        changed = deepcopy(self.start); changed['phase'] = 'cave'
        with self.assertRaises(ValueError): validate(changed)
        self.start['surface']['squad'].clear()
        self.assertEqual(len(self.ledger.read()['surface']['squad']), 20)

    def test_next_trip_uses_current_survivors_and_old_trip_cannot_reenter(self):
        self.exited()
        result = self.ledger.return_to_surface(3, TRIP)
        next_trip = self.ledger.enter_cave(4, 'd'*32)
        self.assertEqual(next_trip['trip']['checkpoint']['squad'], result['surface']['squad'])
        self.assertEqual(next_trip['trip']['checkpoint']['receipts'], result['surface']['receipts'])
        self.assertEqual(self.ledger.return_to_surface(3, TRIP), next_trip)
        self.assertEqual(self.ledger.enter_cave(0, TRIP), next_trip)
