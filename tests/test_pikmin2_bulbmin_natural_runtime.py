"""Unit tests for the lane-11 natural Mother Bulbmin / real-whistle validator.

The validator is source-agnostic; the wiring test probes PIKMIN_NATIVE_ROOT (it
skips when the native worktree is not configured)."""
import os
import unittest
from pathlib import Path

from experimental.pikmin2_bulbmin_natural_runtime import validate

TOKEN = 'e844a2c8be554b7299fd6cc9856bc2d2'
WRITE = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_BULBMIN_READY mother_epoch=1 dependents=10 proxy_model=kochappy_proxy',
    'P2_BULBMIN_MOTHER_BIRTH model=kochappy_proxy generator=23 dependents=0 wild=0 recruited=0',
    'P2_BULBMIN_TX_BOUND wild=2',
    'P2_BULBMIN_WHISTLE recruited=1 wild=1 recruited_total=1 via=navi_callPikis',
    'P2_CAVE_BULBMIN_TRANSITION move=descend removed=1 kept=17 exiting=0',
    'P2_CAVE_TRANSFER floor=1 survivors=17 health=0.625 failed=0',
])
READ = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CAVE_RESTORE species=1 maturity=0',
    'P2_CAVE_RESTORE species=5 maturity=0',
    'P2_CAVE_READY floor=2 survivors=17 health=0.625',
    'P2_CAVE_BULBMIN_TRANSITION move=exit removed=0 kept=17 exiting=1',
])
TRANSFER = '\n'.join([f'P2_CAVE_TRANSFER_3', TOKEN, '1 0.625 17',
                      *(['1 0'] * 16), '5 0', ''])


class BulbminNaturalRuntimeTests(unittest.TestCase):
    def test_validate_passes_on_source_logs(self):
        result = validate(WRITE, READ, TRANSFER)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['transfer'][0], 'P2_CAVE_TRANSFER_3')

    def test_real_whistle_must_recruit_someone(self):
        bad = WRITE.replace('P2_BULBMIN_WHISTLE recruited=1',
                            'P2_BULBMIN_WHISTLE recruited=0')
        result = validate(bad, READ, TRANSFER)
        self.assertFalse(result['checks']['natural_whistle'])
        self.assertFalse(result['passed'])

    def test_recruitment_must_not_be_the_api_path(self):
        result = validate(WRITE + '\nP2_BULBMIN_TX_RECRUIT made=1 phase=1', READ, TRANSFER)
        self.assertFalse(result['checks']['whistle_via_real_path'])
        self.assertFalse(result['passed'])

    def test_whistle_must_come_from_the_navi_path(self):
        bad = WRITE.replace('via=navi_callPikis', 'via=direct')
        result = validate(bad, READ, TRANSFER)
        self.assertFalse(result['checks']['whistle_via_real_path'])
        self.assertFalse(result['passed'])

    def test_descend_must_drop_a_wild_dependent(self):
        bad = WRITE.replace('P2_CAVE_BULBMIN_TRANSITION move=descend removed=1',
                            'P2_CAVE_BULBMIN_TRANSITION move=descend removed=0')
        result = validate(bad, READ, TRANSFER)
        self.assertFalse(result['checks']['descend_drops_wild'])
        self.assertFalse(result['passed'])

    def test_transfer_must_carry_the_recruited_bulbmin(self):
        no_bulbmin = '\n'.join([f'P2_CAVE_TRANSFER_3', TOKEN, '1 0.625 16',
                                *(['1 0'] * 16), ''])
        result = validate(WRITE, READ, no_bulbmin)
        self.assertFalse(result['checks']['recruited_persist'])
        self.assertFalse(result['passed'])

    # Strip-a-line flips: each nominated marker must gate exactly its own check.

    def test_mother_host_resolved_requires_a_real_generator(self):
        bad = WRITE.replace('generator=23', 'generator=0')
        result = validate(bad, READ, TRANSFER)
        self.assertFalse(result['checks']['mother_host_resolved'])
        self.assertFalse(result['passed'])

    def test_mother_birth_requires_the_proxy_registered(self):
        bad = WRITE.replace('dependents=0', 'dependents=9')
        result = validate(bad, READ, TRANSFER)
        self.assertFalse(result['checks']['mother_birth'])
        self.assertFalse(result['passed'])

    def test_read_restore_requires_a_live_bulbmin(self):
        bad = READ.replace('P2_CAVE_RESTORE species=5 maturity=0', 'P2_CAVE_RESTORE species=1 maturity=0')
        result = validate(WRITE, bad, TRANSFER)
        self.assertFalse(result['checks']['read_restore'])
        self.assertFalse(result['passed'])

    def test_exit_move_must_run(self):
        bad = READ.replace('P2_CAVE_BULBMIN_TRANSITION move=exit', 'P2_CAVE_BULBMIN_TRANSITION move=descend')
        result = validate(WRITE, bad, TRANSFER)
        self.assertFalse(result['checks']['exit_removes_tracked'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text', READ, TRANSFER)


def _native_root():
    env = os.environ.get('PIKMIN_NATIVE_ROOT')
    if env and (Path(env) / 'pc_port' / 'pc_p2_bulbmin.cpp').is_file():
        return Path(env)
    return None


class BulbminNaturalWiringTests(unittest.TestCase):
    def test_mother_host_resolver_and_lifetime_hook_are_wired(self):
        native = _native_root()
        if native is None:
            self.skipTest('set PIKMIN_NATIVE_ROOT to the native worktree')
        bulbmin = (native / 'pc_port' / 'pc_p2_bulbmin.cpp').read_text(errors='replace')
        header = (native / 'pc_port' / 'pc_p2_bulbmin.h').read_text(errors='replace')
        navi = (native / 'src' / 'plugPikiKando' / 'navi.cpp').read_text(errors='replace')
        preview = (native / 'pc_port' / 'pc_p2_preview.cpp').read_text(errors='replace')
        cave = (native / 'pc_port' / 'pc_p2_cave.cpp').read_text(errors='replace')
        lifetime = (native / 'pc_port' / 'pc_p2_teki_lifetime.cpp').read_text(errors='replace')
        self.assertIn('P2_BULBMIN_MOTHER_BIRTH', bulbmin)
        self.assertIn('generator=%u', bulbmin)
        self.assertIn('P2_BULBMIN_WHISTLE', bulbmin)
        self.assertIn('pc_p2_bulbmin_mother_host', header)
        self.assertIn('pc_p2_bulbmin_call_pikis', navi)
        self.assertIn('navi_callPikis', navi)
        self.assertIn('via=%s', bulbmin)
        self.assertIn('pc_p2_bulbmin_attach_mother', preview)
        self.assertIn('pc_p2_bulbmin_transition', cave)
        self.assertIn('pc_p2_bulbmin_proxy_forget', lifetime)


if __name__ == '__main__':
    unittest.main()
