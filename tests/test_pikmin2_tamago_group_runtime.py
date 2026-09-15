"""Unit tests for the TamagoMushi (68) manager-driven group-birth validator.

No native build, disc assets, GL or player session are touched: the pure-log
`validate` is exercised against the natural `GOOD_LOG` and negative logs for
each required gate.
"""
import unittest

from experimental.pikmin2_tamago_group_runtime import (
    GOOD_LOG, REQUIRED_CHECKS, TAMAGO_HOST_GEN, TAMAGO_SOURCE_ID, validate)


class TamagoGroupRuntimeTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(TAMAGO_HOST_GEN, 346020)
        self.assertEqual(TAMAGO_SOURCE_ID, 68)

    def test_validate_passes_on_natural_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(all(result['checks'][name] for name in REQUIRED_CHECKS))
        self.assertEqual(result['births'], 10)
        self.assertEqual(result['astonish_hits'], 1)

    def test_removing_birth_fails_manager_birth(self):
        bad = GOOD_LOG.replace(
            'P2_TAMAGO_BIRTH host=346020 leader=346020 follow=9 count=10 source=manager\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['manager_birth'])
        self.assertFalse(result['passed'])

    def test_removing_birth_once_fails_exactly_once(self):
        bad = GOOD_LOG.replace('P2_TAMAGO_BIRTH_ONCE host=346020 births=10 duplicate=0\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['exactly_once'])
        self.assertFalse(result['passed'])

    def test_duplicate_birth_fails_exactly_once(self):
        bad = GOOD_LOG.replace('duplicate=0', 'duplicate=1')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['exactly_once'])
        self.assertFalse(result['passed'])

    def test_removing_astonish_fails_natural_astonish(self):
        bad = GOOD_LOG.replace('P2_TAMAGO_ASTONISH generator=346021 pikmin=1\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['natural_astonish'])
        self.assertFalse(result['passed'])

    def test_removing_group_forget_fails_group_cleanup(self):
        bad = GOOD_LOG.replace(
            'P2_TAMAGO_GROUP_FORGET host=346020 group=10 remaining=0\n', '')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['group_cleanup'])
        self.assertFalse(result['passed'])

    def test_stragglers_fail_group_cleanup(self):
        bad = GOOD_LOG.replace('remaining=0', 'remaining=3')
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['group_cleanup'])
        self.assertFalse(result['passed'])

    def test_inject_marker_fails_no_inject(self):
        spoof = GOOD_LOG + '\nmHealth=0.5f injected_health=0 not_natural_combat=1'
        result = validate(spoof, code=0)
        self.assertFalse(result['checks']['no_inject'])
        self.assertFalse(result['passed'])

    def test_non_text_fails(self):
        with self.assertRaises(ValueError):
            validate(b'not text')

    def test_extinction_fails_no_extinction(self):
        bad = GOOD_LOG + '\nGAMEEND_PikminExtinction'
        result = validate(bad, code=0)
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
