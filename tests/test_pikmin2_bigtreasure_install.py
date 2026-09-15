"""Tests for the opt-in BigTreasure lane install profile (#246)."""
import json
import tempfile
import unittest
from pathlib import Path

from experimental import pikmin2_bigtreasure_install as install_mod


class BigTreasureInstallTest(unittest.TestCase):
    def test_install_and_idempotent_reinstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = install_mod.install(tmp)
            self.assertEqual(payload['status'], 'installed')
            self.assertEqual(payload['enemy_id'], 73)
            self.assertIn('map_trace', payload['bindings'])
            self.assertIn('defeat_teardown', payload['bindings'])
            self.assertIn('models_motions:#128', payload['external_dependencies'])
            run = Path(tmp)
            profile = run / install_mod.PROFILE_TXT
            self.assertTrue(profile.is_file())
            self.assertEqual(profile.read_bytes(), install_mod.profile_text().encode('utf-8'))
            receipt = json.loads((run / install_mod.INSTALL_JSON).read_text(encoding='utf-8'))
            self.assertEqual(receipt['profile_sha256'], payload['profile_sha256'])
            again = install_mod.install(tmp)
            self.assertEqual(again['status'], 'already-installed')

    def test_conflict_refused_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            target = run / install_mod.PROFILE_TXT
            target.write_text('tampered\n', encoding='utf-8')
            before = target.read_bytes()
            with self.assertRaises(SystemExit):
                install_mod.install(tmp)
            self.assertEqual(target.read_bytes(), before)
            self.assertFalse((run / install_mod.INSTALL_JSON).exists())

    def test_missing_run_dir_refused(self):
        with self.assertRaises(SystemExit):
            install_mod.install('nonexistent-run-dir-246')

    def test_profile_contract_tokens(self):
        text = install_mod.profile_text()
        self.assertTrue(text.startswith('P2_BIGTREASURE_SEAM_1\n'))
        self.assertIn('enemy bigtreasure 73 states 12 captured_pellets 5', text)
        self.assertIn('anchor_plus_discharge_le_17', text)
        self.assertIn('pools_first', text)
        self.assertIn('mpellet_drop_code:disc_data', text)

    def test_pellet_configs_recorded(self):
        text = install_mod.profile_text()
        self.assertIn('pellet elec carry 30 40 pokos 1000 dict 197 radius 35 height 50', text)
        self.assertIn('pellet fire carry 30 40 pokos 1000 dict 198 radius 35 height 52', text)
        self.assertIn('pellet gas carry 30 40 pokos 1000 dict 199 radius 37 height 20', text)
        self.assertIn('pellet water carry 30 40 pokos 1000 dict 200 radius 35 height 51', text)
        self.assertIn('pellet loozy carry 1 5 pokos 10 dict 201 radius 12 height 10', text)
        self.assertIn('mpellet_drop_code_null_story', text)
        with tempfile.TemporaryDirectory() as tmp:
            payload = install_mod.install(tmp)
            self.assertEqual(payload['pellet_configs']['loozy']['pokos'], 10)
            self.assertEqual(payload['pellet_configs']['water']['dictionary'], 200)


if __name__ == '__main__':
    unittest.main()
