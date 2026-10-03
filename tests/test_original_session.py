import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from randomizer.original_session import OriginalRun, OriginalSession, descriptor, safe_path, sha, source_identity


def manifest(magic, campaign):
    payload = magic + (struct.pack('<I', 64) if magic == b'P2OC1' else b'') + campaign.encode('ascii')
    return payload + hashlib.sha256(payload).digest()


class OriginalSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prepared = self.root / 'prepared'
        (self.prepared / 'assets').mkdir(parents=True)
        (self.prepared / 'assets/body.mod').write_bytes(b'physical model control')
        (self.prepared / 'p2-original').mkdir()
        self.campaign = 'a' * 64
        self.calendar = self.root / 'calendar'
        self.calendar.mkdir()
        stages = b'4\n' + b''.join((' { name ' + course + ' end 0 0 }\n').encode('ascii') for course in ('tutorial', 'forest', 'yakushima', 'last'))
        self.disc = {'game': 'GPVE01', 'revision': 0, 'size': 100, 'header_sha256': 'c' * 64}
        receipt = {'contract': 'p2-original-calendar-source-v1', 'member': 'user/Abe/stages.txt', 'size': len(stages), 'sha256': sha(stages), 'disc': self.disc}
        (self.calendar / 'stages.txt').write_bytes(stages)
        (self.prepared / 'p2-original/stages.txt').write_bytes(stages)
        (self.prepared / 'p2-original/calendar.p2sc').write_text(f'P2_SOURCE_CALENDAR 1 {self.campaign} {sha(stages)} 4 END\n')
        (self.calendar / 'receipt.json').write_text(json.dumps(receipt))
        for course in ('tutorial', 'forest', 'yakushima', 'last'):
            (self.prepared / 'p2-original' / (course + '.p2c')).write_bytes(manifest(b'P2OC1', self.campaign))
        (self.prepared / 'p2-original/campaign.p2pk').write_bytes(manifest(b'P2PK1', self.campaign))

    def tearDown(self):
        self.temp.cleanup()

    def test_source_identity_verifies_complete_calendar(self):
        bundles = []
        for course in ('tutorial', 'forest', 'yakushima', 'last'):
            bundle = self.root / course
            (bundle / 'generators').mkdir(parents=True)
            raw = ('literal later-day source ' + course).encode('ascii')
            (bundle / 'generators/defaultgen.txt').write_bytes(raw)
            receipt = {'schema': 'p2-surface-source-1', 'course': course, 'disc': self.disc, 'files': {'generators/defaultgen.txt': {'size': len(raw), 'sha256': sha(raw)}}}
            (bundle / 'surface-receipt.json').write_text(json.dumps(receipt))
            bundles.append(bundle)
        identity, canonical = source_identity(bundles, self.calendar)
        self.assertEqual(identity, sha(canonical))
        self.assertEqual(source_identity(list(reversed(bundles)), self.calendar)[0], identity)
        (bundles[0] / 'generators/defaultgen.txt').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            source_identity(bundles, self.calendar)

    def test_changed_physical_inputs_cannot_rebind_saved_session(self):
        selected = descriptor(self.prepared, self.campaign)
        session = OriginalSession(self.root / 'session', selected)
        (self.prepared / 'assets/body.mod').write_bytes(b'changed physical model')
        changed = descriptor(self.prepared, self.campaign)
        self.assertNotEqual(sha(selected), sha(changed))
        with self.assertRaises(ValueError):
            OriginalSession(session.directory, changed)
        self.assertEqual((session.directory / 'p2-original-session.txt').read_bytes(), selected)

    def test_fresh_run_has_no_ap_state_and_uses_exact_handshake(self):
        session = OriginalSession(self.root / 'session', descriptor(self.prepared, self.campaign))
        first = OriginalRun(session, self.prepared)
        second = OriginalRun(session, self.prepared)
        self.assertNotEqual(first.token, second.token)
        bootstrap = first.bootstrap.read_text()
        self.assertTrue(bootstrap.startswith('ORIGINAL_P2_CAMPAIGN 1\n'))
        self.assertIn('ORIGINAL_SOURCE ' + self.campaign, bootstrap)
        self.assertNotIn('ENEMY_P2', bootstrap)
        self.assertNotIn('PIKMIN_RANDOMIZER', bootstrap)
        self.assertEqual(first.directory.joinpath('state.txt').read_text().split(), ['ORIGINAL_P2_STATE', '1', first.token, session.identity, '0', 'END'])
        hello = first.directory / 'hello.txt'
        hello.write_text(f'ORIGINAL_P2_HELLO 1 {first.token} {session.identity} ' + ' '.join(first.capabilities) + ' END\n')
        first.poll()
        self.assertTrue(first.handshaken)
        hello = second.directory / 'hello.txt'
        hello.write_text(f'ORIGINAL_P2_HELLO 1 {first.token} {session.identity} ' + ' '.join(second.capabilities) + ' END\n')
        with self.assertRaises(ValueError):
            second.poll()

    def test_calendar_literal_bytes_cannot_change_under_same_descriptor(self):
        descriptor(self.prepared, self.campaign)
        (self.prepared / 'p2-original/stages.txt').write_bytes(b'changed actual calendar')
        with self.assertRaises(ValueError):
            descriptor(self.prepared, self.campaign)

    def test_wrong_manifest_campaign_and_terrain_only_refuse(self):
        with self.assertRaises(ValueError):
            descriptor(self.prepared, 'b' * 64)
        (self.prepared / 'p2-original/campaign.p2pk').unlink()
        with self.assertRaises(FileNotFoundError):
            descriptor(self.prepared, self.campaign)
        for bad in ('assets/../card.sav', '/assets/body.mod', 'assets//body.mod', 'p2-original/./last.p2c', 'assets/a\\b', 'assets/a:b'):
            self.assertFalse(safe_path(bad), bad)


if __name__ == '__main__':
    unittest.main()
