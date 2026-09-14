import unittest

from experimental.pikmin2_projectile_engine_receiver import (
    ENGINE_STRIKE_RE, MAGIC, build_config, evaluate, parse_engine_strikes,
    stone_config, kabuto_config)


SAMPLE_LOG = """\
Experimental preview window set to 960x540 windowed and centered
[Pikipelago] P2_ROOM_READY treasure=bolt carry=5
P2_PROJECTILES_READY stone=1 egg=0 kabuto=1 rock=0 seed=1
P2_PROJECTILE_KABUTO_READY species=Kabuto mouth=(175.0,0.0,-180.0) face_deg=90.0
P2_PROJECTILE_KABUTO_ACTION phase=Attack action=FireStone tick=8
P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=0 rig=0 mouth=(175.0,0.0,-180.0)
P2_PROJECTILE_STRIKE kind=Attack damage=250.0 target=1234 attributed=5678 source=0 health_zeroed=1
P2_PROJECTILE_ENGINE_STRIKE target=1234 kind=Attack damage=250.0 applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0 source=0
P2_PROJECTILE_STONE_CONTACT target=1234 kind=1 health_zeroed=1
P2_PROJECTILE_STONE_DESTROY reason=health traces=4 floors=0 walls=0
"""


class ProjectileEngineReceiverTests(unittest.TestCase):
    def test_build_config_stone(self):
        text = build_config('stone')
        self.assertTrue(text.startswith(MAGIC))
        self.assertIn('seed 1', text)
        self.assertIn('stone ', text)
        self.assertIn('engine_receiver 1', text)
        self.assertIn('receiver any 20', text)
        self.assertNotIn('kabuto ', text)

    def test_build_config_kabuto(self):
        text = build_config('kabuto')
        self.assertIn('kabuto Kabuto ', text)

    def test_parse_engine_strikes(self):
        strikes = parse_engine_strikes(SAMPLE_LOG)
        self.assertEqual(len(strikes), 1)
        hit = strikes[0]
        self.assertEqual(hit['kind'], 'Attack')
        self.assertEqual(hit['applied'], 1)
        self.assertEqual(hit['stored_before'], 0.0)
        self.assertEqual(hit['stored_after'], 250.0)

    def test_evaluate_teki_attack_mutation_passes(self):
        result = evaluate(SAMPLE_LOG)
        gates = result['gates']
        self.assertEqual(gates['window_960x540_centered'], 'PASS')
        self.assertEqual(gates['config_ready'], 'PASS')
        self.assertEqual(gates['stone_contact'], 'PASS')
        self.assertEqual(gates['cannon_fire_fsm'], 'PASS')
        self.assertEqual(gates['teki_attack_receiver_mutation'], 'PASS')
        self.assertEqual(gates['stone_destroy_teardown'], 'PASS')

    def test_evaluate_teki_mutation_fails_on_immune(self):
        log = SAMPLE_LOG.replace(
            'applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0',
            'applied=0 rejected=1 health=180.0->180.0 stored=0.0->0.0')
        result = evaluate(log)
        self.assertEqual(result['gates']['teki_attack_receiver_mutation'], 'FAIL')
        self.assertEqual(result['gates']['stone_contact'], 'PASS')

    def test_evaluate_press_mutation(self):
        log = SAMPLE_LOG.replace(
            'kind=Attack damage=250.0 applied=1 rejected=0 health=180.0->180.0 stored=0.0->250.0',
            'kind=Press damage=10.0 applied=1 rejected=0 health=300.0->290.0 stored=0.0->0.0')
        result = evaluate(log)
        self.assertEqual(result['gates']['navipiki_press_receiver_mutation'], 'PASS')
        self.assertEqual(result['gates']['teki_attack_receiver_mutation'], 'FAIL')

    def test_missing_window_is_fail(self):
        result = evaluate(SAMPLE_LOG.replace('960x540 windowed and centered', 'nope'))
        self.assertEqual(result['gates']['window_960x540_centered'], 'FAIL')

    def test_stone_config_contains_disc_parms(self):
        row = stone_config()
        self.assertIn(' 250 ', row)     # moveSpeed fp06
        self.assertIn(' 99999 ', row)   # health fp00
        self.assertTrue(row.count(' ') >= 14)

    def test_kabuto_config_mouth(self):
        row = kabuto_config()
        self.assertIn('Kabuto', row)
        self.assertIn(' 175', row)


if __name__ == '__main__':
    unittest.main()
