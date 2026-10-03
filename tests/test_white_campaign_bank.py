import json
import struct
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from randomizer.white_campaign import add_ivory_supply, bank_files, bind_campaign_mode, stage_campaign


class WhiteCampaignBank(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.bank = self.root / 'bank'; self.bank.mkdir()
        lines = ['P2_WHITE_1', 'stats 1.2 10 1.5 3 .5 1 .4 .22 120', 'ivory_generators 1 25']
        for name in ('wait', 'walk', 'attack1'):
            lines.append(f'{name} 1 1')
            (self.bank / f'white_{name}_00.mod').write_bytes(b'model')
        for name in ('wait', 'walk', 'attack1'):
            lines.append('happa ' + name + ' 0 ' + ' '.join(['0'] * 12))
        for i in range(3):
            (self.bank / f'white_happa_{i}.mod').write_bytes(b'growth')
        (self.bank / 'p2-white.txt').write_text('\n'.join(lines) + '\n')
        self.manifest = {'p2_layout': {'bindings': []}, 'p2_purple_campaign': True, 'p2_white_campaign': True}

    def test_complete_bank_and_same_session_reconnect(self):
        models, _ = bank_files(self.bank); self.assertEqual(len(models), 6)
        session = self.root / 'session'
        bind_campaign_mode(session, self.manifest, self.bank)
        before = (session / 'white-campaign.json').read_bytes()
        bind_campaign_mode(session, self.manifest, self.bank)
        self.assertEqual((session / 'white-campaign.json').read_bytes(), before)

    def test_changed_asset_refuses_reconnect(self):
        session = self.root / 'session'; bind_campaign_mode(session, self.manifest, self.bank)
        (self.bank / 'white_wait_00.mod').write_bytes(b'changed')
        with self.assertRaises(ValueError): bind_campaign_mode(session, self.manifest, self.bank)

    def test_missing_or_legacy_manifest_refuses_bank(self):
        with self.assertRaises(ValueError): bind_campaign_mode(self.root / 's', self.manifest, None)
        with self.assertRaises(ValueError): bind_campaign_mode(self.root / 's', {}, self.bank)

    def test_late_optin_refuses_existing_runs(self):
        session = self.root / 's'; (session / 'runs/old').mkdir(parents=True)
        with self.assertRaises(ValueError): bind_campaign_mode(session, self.manifest, self.bank)
        self.assertFalse((session / 'white-campaign.json').exists())

    def test_treasure_without_its_provider_refuses_before_staging(self):
        manifest = dict(self.manifest, p2_white_treasure_campaign=True)
        with self.assertRaises(ValueError): bind_campaign_mode(self.root / 's', manifest, self.bank)
        self.assertFalse((self.root / 's').exists())

    def test_incomplete_or_duplicate_attachment_refuses(self):
        p = self.bank / 'p2-white.txt'; original = p.read_text()
        p.write_text('\n'.join(original.splitlines()[:-1]))
        with self.assertRaises(ValueError): bank_files(self.bank)
        p.write_text(original + original.splitlines()[-1] + '\n')
        with self.assertRaises(ValueError): bank_files(self.bank)

    def test_nonfinite_profile_and_empty_model_refuse(self):
        p = self.bank / 'p2-white.txt'; original = p.read_text(); p.write_text(original.replace('1.2', 'nan'))
        with self.assertRaises(ValueError): bank_files(self.bank)
        p.write_text(original); (self.bank / 'white_wait_00.mod').write_bytes(b'')
        with self.assertRaises(ValueError): bank_files(self.bank)

    def test_three_actual_generator_records_preserve_payload(self):
        # Synthetic framed Boss record exercises byte layout, not native birth.
        row = bytearray(84); row[:8] = b'    0.0v'; struct.pack_into('<I', row, 8, 17)
        row[72:80] = b'ssob\x02\0\0\0'
        data = b'1.0v' + struct.pack('>4fI', 10, 20, 30, 45, 1) + bytes(row)
        staged, ids = add_ivory_supply(data, row, 2, 1)
        self.assertEqual(staged[:20], data[:20]); self.assertEqual(staged[24:108], data[24:])
        self.assertEqual(struct.unpack_from('>I', staged, 20)[0], 4)
        self.assertEqual(len(set(ids)), 3)
        for i, uid in enumerate(ids):
            added = staged[108 + i * 84:108 + (i + 1) * 84]
            self.assertEqual(struct.unpack_from('<I', added, 8)[0], uid)
            self.assertEqual(added[72:80], row[72:80])
            self.assertEqual(struct.unpack_from('>I', added, 80)[0], 5 | (1 << 6))
        with self.assertRaises(ValueError): add_ivory_supply(staged, row, 2, 1)

    def test_invalid_stage_refuses(self):
        for stage in (-1, 5, True):
            with self.assertRaises(ValueError): add_ivory_supply(b'', b'', stage, 1)

    def source_tree(self, root):
        row = bytearray(84); row[:8] = b'    0.0v'; struct.pack_into('<I', row, 8, 17)
        row[72:80] = b'ssob\x02\0\0\0'
        data = b'1.0v' + struct.pack('>4fI', 10, 20, 30, 45, 1) + bytes(row)
        for folder in ('stage1', 'chal0'):
            p = root / 'dataDir/stages' / folder / 'default.gen'
            p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        return data

    def test_actual_overlay_keeps_preexisting_purple_and_p2_bytes(self):
        assets = self.root / 'retail'; original = self.source_tree(assets)
        run = self.root / 'run'; run.mkdir(); prior = run / 'assets'; self.source_tree(prior)
        p2 = prior / 'dataDir/courses/pikmin2room'; p2.mkdir(parents=True)
        (p2 / 'purple_wait_00.mod').write_bytes(b'previous-purple')
        (p2 / 'enemy.mod').write_bytes(b'previous-P2-enemy')
        (run / 'p2-purple-campaign.txt').write_bytes(b'original-purple-config')
        manifest = dict(self.manifest, profile='foh-day2', starting_color='red')
        receipt = stage_campaign(run, assets, self.bank, manifest)
        self.assertEqual((run / 'assets/dataDir/courses/pikmin2room/purple_wait_00.mod').read_bytes(), b'previous-purple')
        self.assertEqual((run / 'assets/dataDir/courses/pikmin2room/enemy.mod').read_bytes(), b'previous-P2-enemy')
        self.assertEqual((run / 'p2-purple-campaign.txt').read_bytes(), b'original-purple-config')
        self.assertEqual((assets / 'dataDir/stages/stage1/default.gen').read_bytes(), original)
        staged = (run / 'assets/dataDir/stages/stage1/default.gen').read_bytes()
        self.assertEqual(staged[24:len(original)], original[24:])
        expected = [0x57485403, 0x57485404, 0x57485405]
        self.assertEqual(receipt['generators'], expected)
        self.assertEqual((run / 'p2-white-campaign.txt').read_text(),
                         'P2_WHITE_CAMPAIGN_1 3\n' + ''.join(f'1 {uid}\n' for uid in expected))
        self.assertEqual((run / 'p2-white.txt').read_text().splitlines()[2],
                         'ivory_generators 3 ' + ' '.join(map(str, expected)))
        self.assertFalse(receipt['terrain_contact_verified'])

    def test_scheduled_identity_collision_refuses_before_overlay_mutation(self):
        assets = self.root / 'retail'; self.source_tree(assets)
        scheduled = assets / 'dataDir/stages/stage1/1.gen'
        scheduled.write_bytes(struct.pack('<I', 0x57485403))
        run = self.root / 'run'; run.mkdir()
        with self.assertRaises(ValueError):
            stage_campaign(run, assets, self.bank, dict(self.manifest, profile='foh-day2'))
        self.assertFalse((run / 'assets').exists())

    def test_genuine_session_bootstrap_has_white_and_purple_suffix(self):
        from randomizer.seed import generate
        from randomizer.session import Session
        from randomizer.runner import NativeRun
        manifest = generate('white-bank-integration', p2_enemies=True, p2_purple_campaign=True,
                            p2_white_campaign=True, p2_species=[2])
        session = Session(manifest, self.root / 'session'); session.save()
        bind_campaign_mode(session.directory, manifest, self.bank)
        native = NativeRun(session)
        text = native.bootstrap.read_text()
        self.assertTrue(text.endswith('PURPLE 1\nWHITE 1\nEND\n'))
        self.assertIn('FINGERPRINT ' + session.fingerprint + '\n', text)

    def test_cli_white_without_required_modes_refuses_generation(self):
        from randomizer.__main__ import main
        import contextlib
        import io
        for flags in (['--p2-white-campaign'], ['--p2-enemies', '--p2-white-campaign']):
            with patch('sys.argv', ['randomizer', 'generate', '--seed', 'white-cli', *flags]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught: main()
                self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__': unittest.main()
