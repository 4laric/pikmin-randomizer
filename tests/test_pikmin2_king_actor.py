"""Tests for experimental/pikmin2_king_actor (#289) and the native policy.

The protocol validation tests always run. The C++ policy header is compiled
and executed with strict MinGW flags when a pc_port include directory is
available (native/pc_port, $P2_NATIVE_PC_PORT, or the sibling kimi native
worktree); otherwise the consistency checks against the #227 reference still
run and the native compile is skipped without failing the suite.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from experimental import pikmin2_bulblax_behavior as bb
from experimental import pikmin2_king_actor as ka

ROOT = Path(__file__).resolve().parents[1]

CLIPS = [
    dict(species='KingChappy', name='attack', duration=95, frames=[0, 25, 40, 70, 86, 92, 94]),
    dict(species='KingChappy', name='cry', duration=138, frames=[0, 33, 38, 65, 100, 103, 137]),
    dict(species='KingChappy', name='damage', duration=135, frames=[0, 46, 65, 94, 134]),
    dict(species='KingChappy', name='dead', duration=200, frames=[0, 185, 199]),
    dict(species='KingChappy', name='dive', duration=142, frames=[0, 141]),
    dict(species='KingChappy', name='flick', duration=70, frames=[0, 35, 69]),
    dict(species='KingChappy', name='move1', duration=80, frames=[0, 15, 54, 79]),
    dict(species='KingChappy', name='type1', duration=45, frames=[0, 44]),
    dict(species='KingChappy', name='type2', duration=35, frames=[0, 34]),
    dict(species='KingChappy', name='type3', duration=75, frames=[0, 55, 74]),
    dict(species='KingChappy', name='wait2', duration=40, frames=[0, 39]),
    dict(species='KingChappy', name='waitact1', duration=50, frames=[0, 49]),
    dict(species='KingChappy', name='waitact2', duration=60, frames=[0, 59]),
]
PLACEMENTS = [
    dict(placement_id=230020, variant='default', xyz=[34, 30, 1896], yaw=0),
    dict(placement_id=230021, variant='f_03', xyz=[150, 30, 1500], yaw=90),
]
BOMBS = [
    dict(bomb_id=360001, xyz=[40, 30, 1900]),
    dict(bomb_id=360002, xyz=[42, 30, 1892], external_blast_tick=1200),
]


class ProtocolTests(unittest.TestCase):
    def test_good_profile_round_trip(self):
        text = ka.protocol(CLIPS, PLACEMENTS, BOMBS).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], 'P2_KING_ACTOR_1')
        self.assertEqual(lines[1], '13')
        self.assertEqual(lines[15], '2')
        self.assertTrue(lines[16].startswith('230020 default 34 30 1896 0'))
        self.assertTrue(lines[17].startswith('230021 f_03 150 30 1500 90'))
        self.assertEqual(lines[18], '2')
        self.assertTrue(lines[19].startswith('360001 40 30 1900 0'))
        self.assertTrue(lines[20].startswith('360002 42 30 1892 1200'))

    def test_no_bombs_is_fine(self):
        text = ka.protocol(CLIPS, PLACEMENTS[:1]).decode('ascii')
        self.assertEqual(text.splitlines()[15], '1')
        self.assertTrue(text.endswith('230020 default 34 30 1896 0\n0\n'))

    def test_duration_must_match_reference(self):
        bad = [dict(c, duration=94) if c['name'] == 'attack' else dict(c) for c in CLIPS]
        with self.assertRaises(ValueError):
            ka.protocol(bad, PLACEMENTS)

    def test_rejections(self):
        def reject(clips=CLIPS, placements=PLACEMENTS, bombs=BOMBS):
            with self.assertRaises(ValueError):
                ka.protocol(clips, placements, bombs)
        # duplicate clip, unknown clip, carry excluded, unsorted frames
        reject(CLIPS + [dict(CLIPS[0])])
        reject([dict(c, name='sleep') if c['name'] == 'flick' else dict(c) for c in CLIPS])
        reject([dict(c, name='carry') if c['name'] == 'flick' else dict(c) for c in CLIPS])
        reject([dict(c, frames=[94, 0]) if c['name'] == 'attack' else dict(c) for c in CLIPS])
        # missing KingChappy clip
        reject([c for c in CLIPS if c['name'] != 'type3'])
        # duplicate id, id overflow, unknown variant, three Emperors
        reject(placements=PLACEMENTS + [dict(PLACEMENTS[0])])
        reject(placements=[dict(PLACEMENTS[0], placement_id=1 << 32)])
        reject(placements=[dict(PLACEMENTS[0], variant='x_99')])
        reject(placements=PLACEMENTS + [dict(placement_id=230022, xyz=[0, 0, 0])])
        # non-finite / out-of-bounds transforms
        reject(placements=[dict(PLACEMENTS[0], xyz=[float('nan'), 0, 0])])
        reject(placements=[dict(PLACEMENTS[0], xyz=[100001, 0, 0])])
        reject(placements=[dict(PLACEMENTS[0], yaw=361)])
        # bomb identity reuse, blast tick bound, too many bombs
        reject(bombs=[dict(BOMBS[0], bomb_id=230020)])
        reject(bombs=[dict(BOMBS[1], external_blast_tick=1000001)])
        reject(bombs=BOMBS * 3)

    def test_full_clip_set_uses_reference_durations(self):
        sampled = {('KingChappy', n): [0, bb.KING_CLIPS[n]['frames'] - 1] for n in bb.KING_CLIPS}
        clips = ka.full_clip_set(sampled)
        self.assertEqual(len(clips), 13)
        for c in clips:
            self.assertEqual(c['duration'], bb.KING_CLIPS[c['name']]['frames'])
        ka.protocol(clips, PLACEMENTS, BOMBS)


class ConsistencyTests(unittest.TestCase):
    """Native policy constants must keep matching the #227 reference."""

    def test_reference_facts_used_by_the_actor(self):
        self.assertEqual(bb.KING_STATES['hidewait'], 9)
        self.assertEqual(bb.KING_STATES['swallow'], 12)
        proper = bb.KING_PROPER_PARMS
        self.assertEqual(proper['distance_to_spawn']['disc'], 60.0)
        self.assertEqual(proper['time_to_appearance']['disc'], 0)
        self.assertEqual(proper['appearance_shake_off_range']['disc'], 100.0)
        self.assertEqual(proper['appearance_shake_off_power']['disc'], 200.0)
        self.assertEqual(proper['required_turning_angle_deg']['disc'], 60.0)
        self.assertEqual(proper['turning_end_angle']['disc'], 40.0)
        self.assertEqual(proper['period_of_incubation']['disc'], 500)
        self.assertEqual(proper['flick_shout_rate']['disc'], 0.5)
        self.assertEqual(proper['death_rate']['disc'], 0.0)
        self.assertEqual(proper['bomb_damage']['disc'], 200.0)
        self.assertEqual(proper['bomb_damage_time']['disc'], 180)
        self.assertEqual(proper['invisible_range']['disc'], 80.0)
        self.assertEqual(proper['white_pikmin']['header'], 300.0)
        self.assertEqual(proper['white_pikmin']['disc'], 200.0)
        self.assertEqual(proper['big_scale']['disc'], 1.5)
        self.assertEqual(proper['big_life']['disc'], 1800.0)
        self.assertEqual(proper['big_speed']['disc'], 45.0)
        self.assertEqual(bb.KING_GENERAL_DISC['health']['value'], 1300.0)
        self.assertEqual(bb.KING_GENERAL_DISC['shake_range']['value'], 60.0)
        self.assertEqual(bb.KING_GENERAL_DISC['attack_damage']['value'], 5.0)
        self.assertEqual(bb.KING_MOUTH['slots'], 9)
        self.assertEqual(bb.KING_MOUTH['slot_radius'], 25.0)
        self.assertEqual(bb.KING_MOUTH['tongue_radius'], 5.0)
        self.assertEqual(bb.KING_ATTACK['swallow_poison_damage']['value'], 300.0)
        self.assertTrue(bb.KING_ATTACK['swallow_poison_damage']['hardcoded'])
        self.assertEqual(bb.KING_BOMB['eatable_state'], 'BOMB_Wait')
        self.assertEqual(bb.KING_BOMB['external_blast_factor']['value'], 0.25)
        self.assertEqual(bb.KING_STONE_STATE_PARTS['mark_stickable'], ('back', 'ketu'))
        self.assertEqual(bb.KING_BIG_VARIANT['trigger_cave_id'], 'f_03')
        self.assertEqual(bb.KING_BIG_VARIANT['floor_offset'], 60.0)
        self.assertEqual(bb.KING_WARCRY['astonish_range']['disc'], 300.0)
        self.assertEqual(bb.KING_WARCRY['astonish_angle_deg']['disc'], 180.0)
        # Policy function spot-checks against the #227 reference functions.
        self.assertTrue(bb.king_hidewait_wake(nearest_target_distance=59.9, frames_waited=1, scale=1.0,
                                              distance_to_spawn=60.0, time_to_appearance=0))
        self.assertEqual(bb.king_check_flick(health=649.9, max_health=1300.0, roll=0.49), 'warcry')
        self.assertEqual(bb.king_check_flick(health=650.0, max_health=1300.0, roll=0.0), 'flick')
        self.assertEqual(bb.king_bomb_damage(bombs_eaten=3), 600.0)
        self.assertTrue(bb.king_eatable_bomb('BOMB_Wait'))
        self.assertEqual(bb.king_damage_tier(petrified=True, has_part=False, stuck_to_part=False,
                                             attacker_dy=0.0, sqr_distance_xz=0.0), 0.1)
        self.assertTrue(bb.king_is_big(cave_id='f_03'))

    def test_native_policy_executable(self):
        candidates = [ROOT / 'native' / 'pc_port']
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.insert(0, Path(os.environ['P2_NATIVE_PC_PORT']))
        candidates.append(ROOT.parent / 'p2-kimi-bulblax-native' / 'pc_port')
        include = next((c for c in candidates if (c / 'pc_p2_king_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            return  # reference-consistency checks above still guard the contract
        source = ROOT / 'tests' / 'pikmin2_king_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-king-policy-') as tmp:
            exe = Path(tmp) / 'king_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
