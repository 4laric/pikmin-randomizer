import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from randomizer.purple_campaign import add_violet, bank_files, bind_campaign_mode, split_records, stage_campaign


def generator():
    row = bytearray(100)
    row[:8] = b'    0.0v'
    struct.pack_into('<I', row, 8, 27)
    row[72:80] = b'ssob\x02\x00\x00\x00'
    return b'1.0v' + struct.pack('>4fI', 5, 10, 15, 45, 1) + row


def banks(root):
    bank, motion = root / 'bank', root / 'motion'
    bank.mkdir(); motion.mkdir()
    matrix = '1 0 0 0 0 1 0 0 0 0 1 0'
    lines = ['P2_PURPLE_1', 'stats 1 1 1 1 1 1 1 1 1']
    lines += [f'{name} 1 1' for name in ('wait', 'walk', 'attack1')]
    lines += [f'happa {name} 0 {matrix}' for name in ('wait', 'walk', 'attack1')]
    for name in ('wait_00', 'walk_00', 'attack1_00', 'happa_0', 'happa_1', 'happa_2'):
        (bank / f'purple_{name}.mod').write_bytes(b'model')
    (bank / 'p2-purple.txt').write_text('\n'.join(lines) + '\n')
    lines = ['P2_PURPLE_MOTION_1', 'rolljmp 14 0.466667', 'fall 20 0.666667']
    for name, count in (('rolljmp', 14), ('fall', 20)):
        for i in range(count):
            lines.append(f'happa {name} {i} {matrix}')
            (motion / f'purple_{name}_{i:02}.mod').write_bytes(b'model')
    (motion / 'p2-purple-motion.txt').write_text('\n'.join(lines) + '\n')
    return bank, motion


class PurpleCampaignTests(unittest.TestCase):
    def test_real_p2_bootstrap_optin_and_legacy_unchanged(self):
        # Seed admission is explicitly injected by the existing fixture helper;
        # this verifies protocol construction, not receiver gameplay admission.
        from tests.test_p2_campaign_fixture import real_manifest
        from randomizer.session import Session
        from randomizer.runner import NativeRun
        from randomizer.seed import generate
        with tempfile.TemporaryDirectory() as tmp:
            session = Session(real_manifest(), Path(tmp) / 'p2')
            vanilla = NativeRun(session).bootstrap.read_text()
            purple = NativeRun(session, purple_campaign=True).bootstrap.read_text()
            self.assertIn('ENEMY_P2 ', purple)
            self.assertTrue(purple.endswith('PURPLE 1\nEND\n'))
            self.assertNotIn('PURPLE', vanilla)
            legacy = Session(generate('purple-default-control'), Path(tmp) / 'legacy')
            with self.assertRaises(ValueError):
                NativeRun(legacy, purple_campaign=True)

    def test_append_preserves_offsets_and_binds_selected_color(self):
        data = generator()
        template = split_records(data)[0]
        for color in range(3):
            result = add_violet(data, template, 900, color)
            self.assertEqual(result[:20], data[:20])
            self.assertEqual(result[24:len(data)], data[24:])
            rows = split_records(result)
            self.assertEqual(len(rows), 2)
            # Native readID swaps the big-endian numeric readInt result.
            native_id = int.from_bytes(struct.unpack_from('>I', rows[1], 8)[0].to_bytes(4, 'little'), 'big')
            self.assertEqual(native_id, 900)
            self.assertEqual(struct.unpack_from('>I', rows[1], 80)[0], 5 | color << 6)
            self.assertEqual(struct.unpack_from('>6f', rows[1], 48), (105, 10, 15, 0, 0, 0))
        with self.assertRaises(ValueError):
            add_violet(data, template, 27)

    def test_inactive_records_count_toward_identity_and_offsets(self):
        data = bytearray(generator()); data[24:28] = b'txen'
        result = add_violet(data, split_records(generator())[0], 800)
        self.assertEqual(result[24:len(data)], data[24:])
        self.assertEqual(len(split_records(result)), 2)

    def test_bank_fail_closed_and_session_reconnect_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bank, motion = banks(root)
            manifest = {'p2_layout': {'bindings': []}}
            session = root / 'session'
            bind_campaign_mode(session, manifest, bank, motion)
            bind_campaign_mode(session, manifest, bank, motion)
            with self.assertRaises(ValueError):
                bind_campaign_mode(session, manifest, None, None)
            (bank / 'purple_wait_00.mod').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                bind_campaign_mode(session, manifest, bank, motion)
            (motion / 'purple_fall_19.mod').unlink()
            with self.assertRaises(FileNotFoundError):
                bank_files(bank, motion)

    def test_no_retroactive_enable_or_half_optin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bank, motion = banks(root)
            (root / 'session/runs/old').mkdir(parents=True)
            with self.assertRaises(ValueError):
                bind_campaign_mode(root / 'session', {'p2_layout': True}, bank, motion)
            with self.assertRaises(ValueError):
                bind_campaign_mode(root / 'session', {'p2_layout': True}, bank, None)
            with self.assertRaises(ValueError):
                bind_campaign_mode(root / 'fresh', {}, bank, motion)

    def test_private_layer_retains_existing_content_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bank, motion = banks(root)
            assets, run = root / 'retail', root / 'run'
            for folder in ('chal0', 'stage1'):
                target = assets / f'dataDir/stages/{folder}/default.gen'
                target.parent.mkdir(parents=True); target.write_bytes(generator())
            # Deliberately use a real pre-staged source, not just retail assets.
            staged = run / 'assets/dataDir/stages/stage1/default.gen'
            staged.parent.mkdir(parents=True)
            existing = bytearray(generator()); existing[40:48] = b'existing'
            staged.write_bytes(existing)
            def copy_overlay(source, dest, overrides):
                self.assertEqual(source, run / 'purple-base-assets')
                for name, value in overrides.items():
                    path = dest / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
            with patch('scripts.preview_pikmin2_room.overlay', side_effect=copy_overlay):
                result = stage_campaign(run, assets, bank, motion,
                                        {'p2_layout': True, 'profile': 'foh-day2', 'starting_color': 'blue'})
            self.assertEqual(staged.read_bytes()[24:len(existing)], existing[24:])
            self.assertEqual((assets / 'dataDir/stages/stage1/default.gen').read_bytes(), generator())
            self.assertEqual((run / 'purple-base-assets/dataDir/stages/stage1/default.gen').read_bytes(), existing)
            self.assertEqual((run / 'p2-purple-campaign.txt').read_text(), f"P2_PURPLE_CAMPAIGN_1 1\n1 {result['generator']}\n")
            self.assertFalse(result['runtime_placement_verified'])
            self.assertIn('impact red_earthquake_v1', (run / 'p2-purple.txt').read_text())


if __name__ == '__main__':
    unittest.main()
