import math
import struct
import unittest
from scripts.stage_pikmin2_tutorial_upper_traversal import floor_at, starts, relocate
from scripts.run_pikmin2_tutorial_upper_traversal import assess, environment, validate_proof, validate_timeout, SUITE, TARGET, SOURCE


def room():
    return dict(vertices=[[-600, 80, 800], [600, 80, 800], [0, 80, 1400]], triangles=[[0, 1, 2]], planes=[[0, 1, 0, 80]])


def generator():
    row = bytearray(100); row[:8] = b'    0.0v'; row[72:76] = b'ikip'
    row[80:84] = b'p00\x04'; row[88:92] = b'p01\x04'; struct.pack_into('>i', row, 92, 1)
    return b'1.0v'+struct.pack('>4fI', 0., 80., 0., 0., 20)+bytes(row)*20


class Inputs(unittest.TestCase):
    def test_missing_or_nonfinite_floor_refuses(self):
        for point in ((9999, 9999), (math.nan, 0)):
            with self.assertRaises(ValueError): floor_at(room(), *point)

    def test_original_spawn_water_radius_refuses_even_clearance_would_be_dry(self):
        box = dict(min=[-300, 0, 950], max=[-200, 100, 1050], surface=100)
        with self.assertRaises(ValueError): starts(room(), [box])

    def test_twenty_unique_native_read_ids_and_per_spawn_floor(self):
        data, rows = relocate(generator(), room(), [])
        self.assertEqual([q['uid'] for q in rows], list(range(1, 21)))
        self.assertEqual(struct.unpack_from('>I', data, 20)[0], 20)
        for i in range(20):
            self.assertEqual(struct.unpack_from('<I', data, 24+i*100+8)[0], i+1)
            self.assertEqual(struct.unpack_from('>f', data, 24+i*100+52)[0], 120.)

    def test_wrong_count_or_color_refuses(self):
        bad = bytearray(generator()); struct.pack_into('>I', bad, 20, 19)
        with self.assertRaises(ValueError): relocate(bad, room(), [])
        bad = bytearray(generator()); struct.pack_into('>i', bad, 24+92, 0)
        with self.assertRaises(ValueError): relocate(bad, room(), [])

    def test_deadline_cannot_expand_or_nan(self):
        for value in (0, -1, 61, math.inf, math.nan):
            with self.assertRaises(ValueError): validate_timeout(value)
        validate_timeout(60)

    def test_environment_scrubs_inherited_fixture_flags_preserves_broker(self):
        env = environment({'P2_WRITES': '1', 'coop_owner': '1', 'NECTAR_SAVE_DIR': 'old',
                           'FIXTURE_SUITE': SUITE, 'PIKMIN_SHA': 'a'*40}, 'positive', 'private', 'exe')
        self.assertNotIn('P2_WRITES', env); self.assertNotIn('coop_owner', env)
        self.assertEqual(env['FIXTURE_SUITE'], SUITE); self.assertEqual(env['NECTAR_SAVE_DIR'], 'private')
        self.assertEqual(env['PIKMIN_SHA'], 'a'*40)

    def test_build_receipt_and_wrong_source_cannot_authorize_runtime(self):
        proof = dict(admitted=True, target=TARGET, source=SOURCE, pins=dict(FIXTURE_SUITE=SUITE,
                     PIKMIN_SHA='a'*40, NATIVE_SHA='b'*40, FIXTURE_SOURCE_SHA256='c'*64))
        validate_proof(proof, 'a'*40, 'b'*40, 'c'*64)
        for key, value in [('FIXTURE_SUITE', 'tutorial-upper-traversal-build'), ('NATIVE_SHA', 'd'*40), ('FIXTURE_SOURCE_SHA256', 'e'*64)]:
            bad = dict(proof, pins=dict(proof['pins'], **{key: value}))
            with self.assertRaises(ValueError): validate_proof(bad, 'a'*40, 'b'*40, 'c'*64)

    def test_timeout_guard_and_ready_cannot_be_gameplay(self):
        raw = dict(passed=True, exit_code=0, captain_down=False, timed_out=False)
        ready = 'P2_UPPER_WINDOW size=960x540 centered=1\nP2_UPPER_READY live=20 faces=5332 waters=3 start=west_bank gameplay_pass=0'
        self.assertTrue(assess('ready', raw, ready)); self.assertFalse(assess('positive', raw, ready))
        self.assertFalse(assess('ready', dict(raw, timed_out=True), ready))
        self.assertFalse(assess('ready', dict(raw, captain_down=True), ready))
        neg = dict(exit_code=86, captain_down=True, timed_out=False)
        self.assertTrue(assess('forced-down', neg, 'P2_FIXTURE_CAPTAIN_DOWN'))
        self.assertFalse(assess('forced-down', neg, 'P2_FIXTURE_CAPTAIN_DOWN\n'+ready))

    def test_positive_requires_current_authored_route_and_original_squad(self):
        raw = dict(passed=True, exit_code=0, captain_down=False, timed_out=False)
        ready = 'P2_UPPER_WINDOW size=960x540 centered=1\nP2_UPPER_READY live=20 faces=5332 waters=3 start=west_bank gameplay_pass=0\n'
        result = 'PASS P2_UPPER_TRAVERSAL original_reds=20 original_captain=1 all_outbound=21 all_returned=21 source_faces=5332 source_water=3 route=retail_bank_20_19 high_ridge=UNPROVEN ordinary_SDL=1 actor_writes=0 gamefeel=UNPLAYED'
        self.assertTrue(assess('positive', raw, ready + result))
        for before, after in [('all_returned=21', 'all_returned=20'),
                              ('route=retail_bank_20_19 high_ridge=UNPROVEN ', ''),
                              ('high_ridge=UNPROVEN', 'high_ridge=PASS')]:
            self.assertFalse(assess('positive', raw, ready + result.replace(before, after)))


if __name__ == '__main__': unittest.main()
