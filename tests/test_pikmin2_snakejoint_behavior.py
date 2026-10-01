"""Unit tests for the SnakeCrow/SnakeWhole source-behavior validator (#407/#174)."""
import unittest

from experimental.pikmin2_snakejoint_behavior import (
    BEHAVIOR_POSITION, BITE_FRAME, PRIVATE_RADIUS, SIGHT, SNAKES,
    plan_positions, squad_distance, validate)

ARENA_POSITIONS = (SNAKES[0]['arena_position'], SNAKES[1]['arena_position'],
                   (50.0, 30.0, 1850.0), (150.0, 30.0, 1550.0))


def good_log():
    lines = ['Experimental preview window set to 960x540 windowed and centered']
    for snake in SNAKES:
        generator = snake['generator']
        species = snake['species']
        lines += [
            f'P2_SNAKEJOINT_BIND generator={generator} species={species} '
            f'source_id={snake["source_id"]} visual_only=0',
            f'P2_ENEMY_READY species={species} native_family=Chappy generator={generator} '
            f'x=-150.0 y=30.0 z=1850.0 health=100.0 max_health=100.0 behavior=native '
            f'source_FSM=implemented attack=animation_event',
            f'P2_SNAKEJOINT_STATE generator={generator} state=stay',
            f'P2_SNAKEJOINT_STATE generator={generator} state=appear2',
            f'P2_SNAKEJOINT_STATE generator={generator} state=wait',
            f'P2_SNAKEJOINT_STATE generator={generator} state=attack',
            f'P2_SNAKEJOINT_BITE generator={generator} frame={BITE_FRAME} pikmin=1',
            f'P2_SNAKEJOINT_STATE generator={generator} state=eat',
            f'P2_SNAKEJOINT_EAT generator={generator} pikmin=1',
            f'P2_SNAKEJOINT_STATE generator={generator} state=wait',
            f'P2_SNAKEJOINT_POS generator={generator} state=walk clip=run1 '
            f'phase=0.30 x=-150.00 z=1850.00',
            f'P2_SNAKEJOINT_POS generator={generator} state=attack clip=hit '
            f'phase=0.40 x=-140.00 z=1840.00',
            f'P2_SNAKEJOINT_DAMAGE_REJECTED generator={generator} state=stay',
            f'P2_SNAKEJOINT_DAMAGE_ACCEPTED generator={generator} state=attack',
            f'P2_SNAKEJOINT_JOINTS generator={generator} species={species} '
            f'source_joints=6 host_joints=1 pose=clip_override',
        ]
    lines.append('P2_SNAKEJOINT_DEAD generator=376001 source_id=34 health=0')
    return '\n'.join(lines)


GOOD_LOG = good_log()


class SnakeJointBehaviorTests(unittest.TestCase):
    def test_identity(self):
        self.assertEqual([s['generator'] for s in SNAKES], [376001, 376002])
        self.assertEqual([s['source_id'] for s in SNAKES], [34, 70])
        self.assertEqual([s['species'] for s in SNAKES], ['SnakeCrow', 'SnakeWhole'])
        self.assertEqual(BITE_FRAME, 34)

    def test_arena_defaults_are_inside_private_and_sight(self):
        for snake in SNAKES:
            distance = squad_distance(snake['arena_position'])
            self.assertLess(distance, PRIVATE_RADIUS)
            self.assertLess(distance, SIGHT[snake['species']])

    def test_plan_positions_keeps_arena_defaults_when_already_near(self):
        planned, overrides = plan_positions(ARENA_POSITIONS)
        self.assertIsNone(overrides)
        self.assertEqual(planned, tuple(tuple(p) for p in ARENA_POSITIONS))

    def test_plan_positions_overrides_a_far_actor(self):
        positions = list(ARENA_POSITIONS)
        positions[SNAKES[1]['index']] = (900.0, 30.0, 1850.0)
        planned, overrides = plan_positions(positions)
        self.assertIsNotNone(overrides)
        self.assertEqual(planned[SNAKES[1]['index']], BEHAVIOR_POSITION)
        self.assertFalse(overrides[0]['production_placement'])
        self.assertLess(squad_distance(planned[SNAKES[1]['index']]), PRIVATE_RADIUS)

    def test_validate_passes_on_source_log(self):
        result = validate(GOOD_LOG, code=0)
        self.assertTrue(result['passed'], result['species'])
        self.assertTrue(result['window'])
        self.assertTrue(result['no_extinction'])
        for species in ('SnakeCrow', 'SnakeWhole'):
            checks = result['species'][species]['checks']
            self.assertTrue(checks['identity'])
            self.assertTrue(checks['ready'])
            self.assertTrue(checks['bite_in_window'])
            self.assertTrue(checks['eat_in_window'])
            self.assertTrue(checks['eat_bounded'])
            self.assertTrue(checks['damage_rejected'])
            self.assertTrue(checks['damage_accepted'])
            self.assertTrue(checks['joint_gap_measured'])
            self.assertGreater(result['species'][species]['motion_spread'], 5.0)
        self.assertTrue(result['snakecrow_dead'])
        self.assertTrue(result['species']['SnakeCrow']['natural_death'])

    def test_bite_outside_attack_window_fails(self):
        injected = GOOD_LOG.replace(
            'P2_SNAKEJOINT_BIND generator=376001 species=SnakeCrow source_id=34 visual_only=0',
            'P2_SNAKEJOINT_BIND generator=376001 species=SnakeCrow source_id=34 visual_only=0\n'
            'P2_SNAKEJOINT_BITE generator=376001 frame=34 pikmin=1')
        result = validate(injected, code=0)
        self.assertFalse(result['species']['SnakeCrow']['checks']['bite_in_window'])
        self.assertFalse(result['passed'])
        self.assertTrue(result['species']['SnakeWhole']['passed'])

    def test_eat_exceeding_bites_fails(self):
        result = validate(GOOD_LOG + '\nP2_SNAKEJOINT_EAT generator=376002 pikmin=1', code=0)
        self.assertFalse(result['species']['SnakeWhole']['checks']['eat_bounded'])
        self.assertFalse(result['passed'])

    def test_missing_damage_rejected_fails_snakecrow(self):
        stripped = GOOD_LOG.replace(
            'P2_SNAKEJOINT_DAMAGE_REJECTED generator=376001 state=stay\n', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['species']['SnakeCrow']['checks']['damage_rejected'])
        self.assertFalse(result['species']['SnakeCrow']['passed'])
        self.assertFalse(result['passed'])
        self.assertTrue(result['species']['SnakeWhole']['passed'])

    def test_missing_joints_fails_snakecrow(self):
        stripped = GOOD_LOG.replace(
            'P2_SNAKEJOINT_JOINTS generator=376001 species=SnakeCrow '
            'source_joints=6 host_joints=1 pose=clip_override\n', '')
        result = validate(stripped, code=0)
        self.assertFalse(result['species']['SnakeCrow']['checks']['joint_gap_measured'])
        self.assertFalse(result['species']['SnakeCrow']['passed'])
        self.assertFalse(result['passed'])
        self.assertTrue(result['species']['SnakeWhole']['passed'])

    def test_validate_rejects_non_text(self):
        with self.assertRaises(ValueError):
            validate(b'not text')


if __name__ == '__main__':
    unittest.main()
