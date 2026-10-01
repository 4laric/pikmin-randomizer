"""Checkpoint/receipt atomicity and native handoff boundaries, without game assets."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_campaign import initial, validate, transition, load, entry_text, read_ledger, ledger_text
from randomizer.session import atomic_write, SessionLock

CONTENT = 'a' * 64
TOKEN = 'b' * 32


def transfer(state, squad=None, health=.75, token=TOKEN):
    state = dict(state, squad=state['squad'] if squad is None else squad, health=health)
    return entry_text(state, token).replace('P2_CAVE_ENTRY_', 'P2_CAVE_TRANSFER_')


class CaveCheckpointTests(unittest.TestCase):
    def test_descent_exit_and_resume_preserve_survivors_and_receipts(self):
        state = initial(CONTENT)
        squad = deepcopy(state['squad'][:19]);squad[0]['maturity'] = 2
        next_state = transition(state, TOKEN, transfer(state, squad), {'treasure:citrus': 180}, {'treasure:citrus': 180})
        self.assertEqual((next_state['floor'], next_state['revision'], next_state['status']), (2, 1, 'active'))
        self.assertEqual(next_state['squad'], squad)
        self.assertEqual(next_state['health'], .75)
        purple = deepcopy(squad)
        for p in purple[:10]: p['species'] = 'purple'
        end = transition(next_state, TOKEN, transfer(next_state, purple), {'treasure:citrus': 180, 'treasure:atlas': 200}, {'treasure:atlas': 200})
        self.assertEqual(end['status'], 'exited')
        self.assertEqual(end['squad'], purple)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json'
            atomic_write(path, json.dumps(end))
            self.assertEqual(load(path, CONTENT), end)
        with self.assertRaisesRegex(ValueError, 'already ended'):
            transition(end, TOKEN, transfer(end), end['receipts'], {})

    def test_runtime_gains_and_casualties_rollback_as_one_unit(self):
        state = initial(CONTENT)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json';atomic_write(path, json.dumps(state))
            ledger = Path(directory)/'runtime.txt'
            ledger.write_text(ledger_text({'treasure:citrus':180}))
            candidate = transition(state, TOKEN, transfer(state, state['squad'][:12]), read_ledger(ledger), {'treasure:citrus':180})
            self.assertEqual(len(candidate['squad']), 12)
            # Process/launcher dies before the single checkpoint replacement.
            self.assertEqual(load(path, CONTENT), state)
            self.assertEqual(ledger_text(load(path, CONTENT)['receipts']), 'P2_ECONOMY_1\n')
            with patch('randomizer.session.os.replace', side_effect=OSError('interrupted replace')):
                with self.assertRaises(OSError): atomic_write(path, json.dumps(candidate))
            self.assertEqual(load(path, CONTENT), state)
            atomic_write(path, json.dumps(candidate))
            self.assertEqual(load(path, CONTENT), candidate)

    def test_stale_malformed_and_unexpected_rewards_rejected(self):
        state = initial(CONTENT)
        for text in (transfer(state, token='c'*32), transfer(state)+'1 0\n', transfer(state).replace('\n1 0.75 20', '\n2 0.75 20'), 'P2_CAVE_TRANSFER_1\n'):
            with self.subTest(text=text), self.assertRaises(ValueError): transition(state, TOKEN, text, {}, {})
        with self.assertRaises(ValueError): transition(state, TOKEN, transfer(state), {'treasure:unknown':1}, {})
        state['receipts'] = {'treasure:previous':180}
        with self.assertRaisesRegex(ValueError,'regressed'): transition(state, TOKEN, transfer(state), {}, {})
        with self.assertRaisesRegex(ValueError,'regressed'): transition(state, TOKEN, transfer(state), {'treasure:previous':181}, {})

    def test_extinction_commits_failure_without_replacement_pikmin(self):
        state = initial(CONTENT)
        for text in (f'P2_CAVE_TRANSFER_1\n{TOKEN}\n1 0.75 0\n', f'P2_CAVE_TRANSFER_1\n{TOKEN}\n1 0 0\n'):
            result = transition(state, TOKEN, text, {}, {})
            self.assertEqual(result['status'], 'failed');self.assertEqual(result['squad'], [])
            validate(result)

    def test_species_limits_invalid_numbers_and_content_mismatch(self):
        state = initial(CONTENT)
        for species in ('blue','yellow','purple'):
            squad = deepcopy(state['squad']);squad[0]['species'] = species
            with self.assertRaisesRegex(ValueError,'species increase'): transition(state,TOKEN,transfer(state,squad),{}, {})
        for health in (float('nan'), float('inf'), -1, 2, True):
            bad = dict(state, health=health)
            with self.assertRaises(ValueError): validate(bad)
        for field, value in [('floor',True),('schema',True),('revision',9),('status','unknown')]:
            with self.assertRaises(ValueError): validate(dict(state, **{field:value}))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json';atomic_write(path,json.dumps(state))
            with self.assertRaisesRegex(ValueError,'changed'):load(path,'c'*64)
            path.write_text('{"schema":1,"schema":1}')
            with self.assertRaisesRegex(ValueError,'Duplicate'):load(path,CONTENT)
            path.write_text('{')
            with self.assertRaises(ValueError):load(path,CONTENT)

    def test_duplicate_runtime_ledger_and_concurrent_writer_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'runtime.txt'
            path.write_text('P2_ECONOMY_1\ntreasure:x 1\ntreasure:x 1\n')
            with self.assertRaises(ValueError):read_ledger(path)
            with SessionLock(directory):
                with self.assertRaises(ValueError):
                    with SessionLock(directory):pass
            with SessionLock(directory):pass

