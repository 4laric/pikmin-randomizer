"""Unit tests for the lane-15 Honeywisp source lifecycle contract (#166)."""
import unittest

import experimental.pikmin2_qurione_lifecycle as life
from experimental.pikmin2_qurione_lifecycle import (
    ANIM_IDS, BIRTH, GATES, PARMS, REWARD, SCHEMA, SOURCE_FSM, SOURCE_ID, STATE_ORDER)


GOOD_LOG = '\n'.join([
    'P2_QURIONE_BIND generator=160001 source_id=16 visual_only=0',
    'P2_ENEMY_READY species=Qurione native_family=Qurione generator=160001 x=0.0 y=60.0 '
    'z=0.0 health=9999.0 max_health=9999.0 behavior=native source_FSM=implemented reward=P2_Egg',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_QURIONE_EGG generator=160001 action=attach',
    'P2_QURIONE_STATE generator=160001 state=stay',
    'P2_QURIONE_STATE generator=160001 state=appear',
    'P2_QURIONE_STATE generator=160001 state=move',
    'P2_QURIONE_POS generator=160001 state=move clip=waitl phase=0.31 x=0.00 y=61.00 z=10.00',
    'P2_QURIONE_POS generator=160001 state=move clip=waitl phase=0.61 x=0.00 y=62.00 z=20.00',
    'P2_QURIONE_POS generator=160001 state=move clip=waitl phase=0.91 x=0.00 y=63.00 z=30.00',
    'P2_QURIONE_EGG generator=160001 action=drop',
    'P2_QURIONE_STATE generator=160001 state=drop',
    'P2_QURIONE_STATE generator=160001 state=dead',
    'P2_QURIONE_STATE generator=160001 state=disappear',
])


def drop(fragment):
    return '\n'.join(line for line in GOOD_LOG.splitlines() if fragment not in line)


REAL_LOG = (GOOD_LOG
            .replace('P2_QURIONE_EGG generator=160001 action=attach',
                     'P2_QURIONE_EGG generator=160001 action=attach\n'
                     'P2_QURIONE_EGG_REAL generator=160001 born=1 drop_group=0')
            .replace('P2_QURIONE_EGG generator=160001 action=drop',
                     'P2_QURIONE_EGG generator=160001 action=drop\n'
                     'P2_QURIONE_EGG_REAL generator=160001 released=1\n'
                     'P2_QURIONE_EGG_BREAK generator=160001 type=2 items=1 real=1\n'
                     'P2_QURIONE_EGG_ITEM generator=160001 index=0 kind=2 real=1 '
                     'fallback=0 item=nectar x=0.0 y=30.0 z=0.0'))


class QurioneLifecycleTests(unittest.TestCase):
    def test_schema_and_identity(self):
        self.assertEqual(SCHEMA, 'p2-qurione-lifecycle-v1')
        self.assertEqual(SOURCE_ID, 16)
        self.assertEqual(life.INTERNAL, 'Qurione')

    def test_source_state_machine_complete(self):
        self.assertEqual(set(SOURCE_FSM), set(STATE_ORDER))
        for name, entry in SOURCE_FSM.items():
            self.assertTrue(entry['entry'], name)
            self.assertTrue(entry['exit'], name)

    def test_anim_ids_and_parms(self):
        self.assertEqual(ANIM_IDS, {'wait': 0, 'damage': 1, 'run': 2, 'appear': 3, 'hide': 4})
        self.assertEqual(PARMS['fp01'], 'flight_height=60')
        self.assertEqual(PARMS['fp04'], 'death_rate=100')

    def test_birth_invariants(self):
        self.assertTrue(BIRTH['invulnerable'])
        self.assertFalse(BIRTH['leave_carcass'])
        self.assertEqual(BIRTH['spawn_count'], 2)
        self.assertAlmostEqual(BIRTH['scale_step'], 0.05)

    def test_reward_is_carried_egg(self):
        self.assertEqual(REWARD['kind'], 'Egg')
        self.assertEqual(REWARD['source_id'], 37)
        self.assertEqual(REWARD['attach_joint'], 'water')
        self.assertIn('P2Egg policy', REWARD['real'])
        self.assertIn('P2_QURIONE_EGG_BREAK', REWARD['markers'])
        self.assertIn('P2_QURIONE_EGG_ITEM', REWARD['markers'])

    def test_sequences(self):
        self.assertEqual(life.lifecycle_sequence(),
                         ['stay', 'appear', 'move', 'disappear', 'stay'])
        self.assertEqual(life.drop_sequence(), ['move', 'drop', 'dead'])

    def test_gates_cover_all(self):
        self.assertEqual(set(life.GATE_STATUS), set(GATES))

    def test_gate_status_matches_handoff(self):
        # GATE_STATUS must not silently drift from the handoff six-gate table.
        from pathlib import Path
        import re
        doc = Path(life.__file__).resolve().parents[1] / 'docs' / 'PIKMIN2_LANE15_DEEPSEEK_HANDOFF.md'
        text = doc.read_text(encoding='utf-8')
        rows = re.findall(r'^\|\s*(\d)\.\s*[^|]*\|\s*(PASS|PARTIAL|FAIL|BLOCKED|UNTESTED|N/A)', text, re.M)
        self.assertTrue(rows, 'handoff gate table not found')
        by_num = {int(n): s for n, s in rows}
        for index, gate in enumerate(life.GATES, start=1):
            self.assertIn(index, by_num, gate)
            token = by_num[index]
            self.assertTrue(life.GATE_STATUS[gate].upper().startswith(token.upper()),
                            f'{gate}: GATE_STATUS={life.GATE_STATUS[gate]!r} handoff={token}')

    def test_acceptance_contract(self):
        contract = life.acceptance_contract()
        self.assertIn('P2_QURIONE_BIND', contract['identity'])
        self.assertIn('source_id=16', contract['identity'])
        self.assertIn('P2_Egg', contract['ready'])
        self.assertEqual(contract['required_states'], list(STATE_ORDER))

    def test_validate_passes_on_lifecycle_log(self):
        result = life.validate_lifecycle(GOOD_LOG)
        self.assertTrue(result['passed'], result['checks'])
        self.assertTrue(result['checks']['source_cycle'])
        self.assertTrue(result['checks']['drop_path'])
        self.assertTrue(result['checks']['exactly_one_drop'])

    def test_validate_detects_real_egg_reward(self):
        result = life.validate_lifecycle(REAL_LOG)
        self.assertTrue(result['passed'], result['checks'])
        rr = result['checks']['reward_real']
        self.assertTrue(rr['born'], rr)
        self.assertTrue(rr['released'], rr)
        self.assertTrue(rr['break_'], rr)
        self.assertTrue(rr['item'], rr)
        self.assertTrue(rr['nectar'], rr)
        self.assertTrue(result['passed_real'], result['checks'])

    def test_validate_reward_real_absent_in_proxy_log(self):
        result = life.validate_lifecycle(GOOD_LOG)
        self.assertFalse(any(result['checks']['reward_real'].values()))
        self.assertFalse(result['passed_real'])

    def test_validate_passed_real_requires_full_chain(self):
        bad = '\n'.join(line for line in REAL_LOG.splitlines()
                        if 'P2_QURIONE_EGG_BREAK' not in line)
        result = life.validate_lifecycle(bad)
        self.assertFalse(result['passed_real'])
        self.assertFalse(result['checks']['reward_real']['break_'])

    def test_validate_rejects_missing_cycle_state(self):
        bad = drop('state=disappear')
        self.assertFalse(life.validate_lifecycle(bad)['checks']['source_cycle'])

    def test_validate_rejects_missing_egg_drop(self):
        bad = drop('action=drop')
        result = life.validate_lifecycle(bad)
        self.assertFalse(result['checks']['egg_drop'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_duplicate_egg_drop(self):
        bad = GOOD_LOG + '\nP2_QURIONE_EGG generator=160001 action=drop'
        self.assertFalse(life.validate_lifecycle(bad)['checks']['exactly_one_drop'])

    def test_validate_rejects_wrong_id(self):
        bad = GOOD_LOG.replace('source_id=16', 'source_id=17')
        self.assertFalse(life.validate_lifecycle(bad)['checks']['identity'])

    def test_validate_rejects_extinction(self):
        result = life.validate_lifecycle(GOOD_LOG + '\nExtinction')
        self.assertFalse(result['checks']['no_extinction'])
        self.assertFalse(result['passed'])

    def test_validate_rejects_nan_movement(self):
        bad = GOOD_LOG + '\nP2_QURIONE_POS generator=160001 state=stay clip=appear1 phase=1.00 x=nan y=nan z=nan'
        result = life.validate_lifecycle(bad)
        self.assertFalse(result['checks']['no_movement_nan'])
        self.assertFalse(result['passed'])

    def test_validate_accepts_finite_movement(self):
        self.assertTrue(life.validate_lifecycle(GOOD_LOG)['checks']['no_movement_nan'])

    def test_validate_moved_requires_distinct_positions(self):
        pos = 'P2_QURIONE_POS generator=160001 state=move clip=wait phase=1.00 '
        log = GOOD_LOG + '\n' + '\n'.join(
            [pos + 'x=0.0 y=60.0 z=0.0', pos + 'x=10.0 y=60.0 z=0.0', pos + 'x=20.0 y=60.0 z=0.0'])
        result = life.validate_lifecycle(log)
        self.assertIs(result['checks']['moved'], True)

    def test_validate_moved_rejects_frozen_position(self):
        pos = 'P2_QURIONE_POS generator=160001 state=move clip=wait phase=1.00 x=0.0 y=60.0 z=0.0'
        base = '\n'.join(l for l in GOOD_LOG.splitlines() if not l.startswith('P2_QURIONE_POS '))
        log = base + '\n' + '\n'.join([pos, pos, pos])
        result = life.validate_lifecycle(log)
        self.assertIs(result['checks']['moved'], False)
        self.assertFalse(result['passed'])

    def test_moved_ignores_dead_flyaway(self):
        dead_lines = '\n'.join(
            'P2_QURIONE_POS generator=160001 state=dead clip=run phase=1.00 x=0.0 y=%s z=0.0' % y
            for y in (100.0, 200.0, 300.0))
        log = GOOD_LOG + '\n' + dead_lines
        result = life.validate_lifecycle(log)
        self.assertIs(result['checks']['moved'], True)

        base = '\n'.join(l for l in GOOD_LOG.splitlines() if not l.startswith('P2_QURIONE_POS '))
        no_move = base + '\n' + dead_lines
        self.assertIs(life.validate_lifecycle(no_move)['checks']['moved'], False)

    def test_moved_false_without_move_displacement(self):
        pos = 'P2_QURIONE_POS generator=160001 state=move clip=wait phase=1.00 x=0.0 y=60.0 z=0.0'
        log = '\n'.join([pos, pos, pos])
        self.assertIs(life.validate_lifecycle(log)['checks']['moved'], False)

    def test_full_chain_requires_drop_and_reward(self):
        result = life.validate_lifecycle(REAL_LOG)
        self.assertIs(result['passed_real'], True)
        self.assertIs(result['full_chain'], True)
        no_break = '\n'.join(line for line in REAL_LOG.splitlines()
                             if 'P2_QURIONE_EGG_BREAK' not in line)
        self.assertIs(life.validate_lifecycle(no_break)['full_chain'], False)

    def test_full_chain_false_when_missing_drop_path(self):
        log = '\n'.join(line for line in GOOD_LOG.splitlines()
                        if 'state=drop' not in line and 'state=dead' not in line)
        self.assertIs(life.validate_lifecycle(log)['full_chain'], False)

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            life.validate_lifecycle(b'not text')


if __name__ == '__main__':
    unittest.main()
