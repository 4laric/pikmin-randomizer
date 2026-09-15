from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts.test_pikmin2_terminal_native import fork_boundary,assert_terminal_preserved,run_test


class NativeTerminalDriverTests(unittest.TestCase):
    def test_fork_copies_boundary_only_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'original';(source/'session').mkdir(parents=True)
            state=dict(phase='surface',trip=None,revision=8)
            (source/'session/surface-ledger.json').write_text(json.dumps(state))
            (source/'loop-identity.json').write_text('{"campaign":"original"}')
            (source/'pending-surface-entry.json').write_text('old live command')
            destination=root/'case';self.assertEqual(fork_boundary(source,destination),state)
            self.assertFalse((destination/'pending-surface-entry.json').exists())
            self.assertEqual((source/'pending-surface-entry.json').read_text(),'old live command')
            self.assertEqual((destination/'session/surface-ledger.json').read_bytes(),(source/'session/surface-ledger.json').read_bytes())
            with self.assertRaises(FileExistsError):fork_boundary(source,destination)

    def test_inflight_baseline_refused_before_fork(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'session').mkdir()
            (root/'session/surface-ledger.json').write_text('{"phase":"cave","trip":{}}')
            with self.assertRaises(ValueError):fork_boundary(root,root/'case')
            self.assertFalse((root/'case').exists())

    def test_terminal_requires_no_living_party_and_unchanged_credit(self):
        before=dict(surface=dict(receipts={'treasure:a':480}))
        after=dict(phase='failed',surface=deepcopy(before['surface']),trip=dict(token=None,checkpoint=dict(squad=[],receipts={'treasure:a':480})))
        assert_terminal_preserved(before,after)
        for mutate in ('party','credit','token','phase'):
            changed=deepcopy(after)
            if mutate=='party':changed['trip']['checkpoint']['squad']=[dict(species='red',maturity=0)]
            if mutate=='credit':changed['trip']['checkpoint']['receipts']['treasure:a']=960
            if mutate=='token':changed['trip']['token']='still-active'
            if mutate=='phase':changed['phase']='surface'
            with self.subTest(mutate=mutate),self.assertRaises(AssertionError):assert_terminal_preserved(before,changed)

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):run_test(SimpleNamespace(output=Path(d)))


if __name__=='__main__':unittest.main()
