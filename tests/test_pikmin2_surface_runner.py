import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experimental.pikmin2_surface_ledger import SurfaceLedger
from experimental.pikmin2_surface_runner import SurfaceRunner
from experimental.pikmin2_campaign import entry_text, ledger_text
from randomizer.session import SessionLock


class Content:
    identity = 'a'*64
    def __init__(self): self.calls = []
    def stage(self, checkpoint, token, runs):
        self.calls.append(checkpoint['floor'])
        run = runs/str(len(self.calls))
        run.mkdir(parents=True)
        (run/'p2-cave-entry.txt').write_text(entry_text(checkpoint, token))
        (run/'p2-economy.txt').write_text(ledger_text(checkpoint['receipts']))
        return run, {'treasure:test': 100}


def transfer(args, cwd, **kwargs):
    (cwd/'p2-cave-transfer.txt').write_text((cwd/'p2-cave-entry.txt').read_text().replace('ENTRY', 'TRANSFER'))
    (cwd/'p2-economy.txt').write_text(ledger_text({'treasure:test': 100}))
    return SimpleNamespace(returncode=42)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = SurfaceLedger(Path(self.tmp.name)/'save', 'a'*64, 'b'*32)
        self.ledger.create(dict(region='valley', day=2, time=8.5, position=[1,2,3],
                                squad=[dict(species='red', maturity=1)], health=.8, receipts={}))
        self.ledger.enter_cave(0, 'c'*32)
        self.content = Content()
    def runner(self, process=transfer):
        return SurfaceRunner(self.ledger, self.content, 'unused.exe', process)
    def test_roundtrip_and_no_relaunch(self):
        result = self.runner().resume()
        self.assertEqual(result['phase'], 'surface')
        self.assertEqual(result['surface']['receipts'], {'treasure:test':100})
        self.assertEqual(result['surface']['position'], [1,2,3])
        self.assertEqual(self.content.calls, [1,2])
        self.runner().resume()
        self.assertEqual(self.content.calls, [1,2])
        self.assertFalse((self.ledger.directory/'checkpoint.json').exists())
    def test_launch_failure_and_unexpected_exit(self):
        before = self.ledger.read()
        with self.assertRaises(OSError): self.runner(lambda *a, **k: (_ for _ in ()).throw(OSError('launch'))).resume()
        with self.assertRaises(RuntimeError): self.runner(lambda *a, **k: SimpleNamespace(returncode=99)).resume()
        self.assertEqual(before, self.ledger.read())
    def test_close_then_resume(self):
        self.runner(lambda *a, **k: SimpleNamespace(returncode=0)).resume()
        self.assertEqual(self.ledger.read()['trip']['checkpoint']['floor'], 1)
        self.assertEqual(self.runner().resume()['phase'], 'surface')
    def test_floor_two_resume(self):
        def process(*a, **k):
            return transfer(*a, **k) if self.content.calls[-1] == 1 else SimpleNamespace(returncode=0)
        self.runner(process).resume()
        self.assertEqual(self.ledger.read()['trip']['checkpoint']['floor'], 2)
        self.assertEqual(self.runner().resume()['phase'], 'surface')
    def test_interrupted_commit_replays_pending(self):
        original = self.ledger.apply_floor
        def uncertain(*args):
            original(*args)
            raise OSError('lost acknowledgement')
        with patch.object(self.ledger, 'apply_floor', side_effect=uncertain):
            with self.assertRaises(OSError): self.runner().resume()
        self.assertEqual(self.ledger.read()['trip']['checkpoint']['floor'], 2)
        self.assertEqual(self.runner().resume()['phase'], 'surface')
        self.assertEqual(self.content.calls, [1,2])
        self.assertEqual(self.ledger.read()['revision'], 4)
    def test_write_failure_retries_entry(self):
        with patch('experimental.pikmin2_surface_runner.atomic_write', side_effect=OSError('disk')):
            with self.assertRaises(OSError): self.runner().resume()
        self.assertEqual(self.ledger.read()['revision'], 1)
        self.assertEqual(self.runner().resume()['phase'], 'surface')
    def test_content_and_lease_conflicts(self):
        self.content.identity = 'd'*64
        with self.assertRaises(ValueError): self.runner().resume()
        self.content.identity = 'a'*64
        with SessionLock(self.ledger.directory/'native-runner-lease'):
            with self.assertRaises(ValueError): self.runner().resume()
        self.assertEqual(self.content.calls, [])
    def test_return_ready_resume(self):
        self.assertEqual(self.runner().resume(return_to_surface=False)['phase'], 'return_ready')
        self.assertEqual(self.runner().resume()['phase'], 'surface')
        self.assertEqual(self.content.calls, [1,2])
    def test_failed_party_does_not_restore_suspended_surface(self):
        def death(args, cwd, **kwargs):
            lines = (cwd/'p2-cave-entry.txt').read_text().splitlines()
            (cwd/'p2-cave-transfer.txt').write_text(f'P2_CAVE_TRANSFER_1\n{lines[1]}\n1 0 0\n')
            return SimpleNamespace(returncode=42)
        self.assertEqual(self.runner(death).resume()['phase'], 'failed')
        self.assertEqual(self.runner().resume()['phase'], 'failed')
        self.assertEqual(self.content.calls, [1])

if __name__ == '__main__': unittest.main()
