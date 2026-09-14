"""Unit tests for the lane-11 two-process cave restart validator (#131/#112)."""
import unittest

from experimental.pikmin2_cave_restart_runtime import validate

TOKEN = 'e844a2c8be554b7299fd6cc9856bc2d2'
WRITE = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CAVE_READY floor=2 survivors=19 health=0.625',
    'P2_LANE11_SQUAD red=16 yellow=1 purple=1 bulbmin=1',
    'P2_CAVE_TRANSFER floor=2 survivors=19 health=0.625 failed=0',
    'P2_LANE11_WRITE ok=1',
])
READ = '\n'.join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_CAVE_RESTORE species=1 maturity=0',
    'P2_CAVE_RESTORE species=5 maturity=0',
    'P2_CAVE_READY floor=2 survivors=19 health=0.625',
    'P2_LANE11_READ bulbmin=1 observed=60',
    'PASS P2_LANE11_RESTORE',
])
TRANSFER = '\n'.join([f'P2_CAVE_TRANSFER_3', TOKEN, '2 0.625 19',
                      *(['1 0'] * 16), '2 1', '3 2', '5 0', ''])


class CaveRestartRuntimeTests(unittest.TestCase):
    def test_validate_passes_on_source_logs(self):
        result = validate(WRITE, READ, TRANSFER)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['transfer'][0], 'P2_CAVE_TRANSFER_3')

    def test_engine_write_must_confirm(self):
        result = validate(WRITE.replace('P2_LANE11_WRITE ok=1', 'P2_LANE11_WRITE ok=0'), READ, TRANSFER)
        self.assertFalse(result['checks']['write_ok'])
        self.assertFalse(result['passed'])

    def test_transfer_must_be_schema_3(self):
        result = validate(WRITE, READ, TRANSFER.replace('P2_CAVE_TRANSFER_3', 'P2_CAVE_TRANSFER_2'))
        self.assertFalse(result['checks']['transfer_header'])
        self.assertFalse(result['passed'])

    def test_restore_requires_a_live_bulbmin(self):
        bad = READ.replace('P2_LANE11_READ bulbmin=1', 'P2_LANE11_READ bulbmin=0')
        result = validate(WRITE, bad, TRANSFER)
        self.assertFalse(result['checks']['read_bulbmin'])
        self.assertFalse(result['passed'])

    def test_abort_fails(self):
        result = validate(WRITE, READ + '\nInvalid P2 cave entry: Pikmin', TRANSFER)
        self.assertFalse(result['checks']['no_abort'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text', READ, TRANSFER)


if __name__ == '__main__':
    unittest.main()


def test_tutorial_replacement_supports_current_object_graph():
    from experimental.pikmin2_elecbug_immunity_behavior import replace_tutorial_input
    original = ['g++', 'private/17-newPikiGame.cpp.obj', 'private/18-teki.cpp.obj', '-lSDL2']
    assert replace_tutorial_input(original, 'tutorial.obj') == ['g++', 'tutorial.obj', 'private/18-teki.cpp.obj', '-lSDL2']
    assert original[1] == 'private/17-newPikiGame.cpp.obj'
    assert replace_tutorial_input(['g++', 'private/1-libpikmin_legacy.a'], 'tutorial.obj') == ['g++', 'tutorial.obj', 'private/1-libpikmin_legacy.a']
    import pytest
    for bad in (['g++'], ['a-newPikiGame.cpp.obj', 'b-newPikiGame.cpp.obj'], ['a-newPikiGame.cpp.obj', 'a-libpikmin_legacy.a']):
        with pytest.raises(ValueError):
            replace_tutorial_input(bad, 'tutorial.obj')
