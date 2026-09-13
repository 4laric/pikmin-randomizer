"""Tests for experimental/pikmin2_queen_actor (#256) and the native policy.

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
from experimental import pikmin2_queen_actor as qa

ROOT = Path(__file__).resolve().parents[1]

CLIPS = [
    dict(species='Queen', name='dead', duration=140, frames=[0, 139]),
    dict(species='Queen', name='sleep', duration=210, frames=[0, 59, 118, 209]),
    dict(species='Queen', name='wait1', duration=30, frames=[0, 29]),
    dict(species='Queen', name='damage', duration=50, frames=[0, 49]),
    dict(species='Queen', name='flick', duration=60, frames=[0, 40, 59]),
    dict(species='Queen', name='rolling_l', duration=110, frames=[0, 20, 67, 69, 109]),
    dict(species='Queen', name='rolling_r', duration=110, frames=[0, 20, 67, 69, 109]),
    dict(species='Queen', name='born', duration=28, frames=[0, 24, 27]),
    dict(species='Baby', name='born', duration=35, frames=[0, 34]),
    dict(species='Baby', name='move', duration=12, frames=[0, 11]),
    dict(species='Baby', name='dead', duration=100, frames=[0, 99]),
]
PLACEMENTS = [
    dict(placement_id=230010, variant='default', larvae=True, xyz=[-120, 30, 1800], yaw=0),
    dict(placement_id=230011, variant='f_01', larvae=False, xyz=[150, 30, 1500], yaw=90),
]


class ProtocolTests(unittest.TestCase):
    def test_good_profile_round_trip(self):
        text = qa.protocol(CLIPS, PLACEMENTS).decode('ascii')
        lines = text.splitlines()
        self.assertEqual(lines[0], 'P2_QUEEN_ACTOR_1')
        self.assertEqual(lines[1], '11')
        self.assertEqual(lines[13], '2')
        self.assertTrue(lines[14].startswith('230010 default 1 -120 30 1800 0'))
        self.assertTrue(lines[15].startswith('230011 f_01 0 150 30 1500 90'))

    def test_duration_must_match_reference(self):
        bad = [dict(c, duration=139) if c['name'] == 'dead' else dict(c) for c in CLIPS]
        with self.assertRaises(ValueError):
            qa.protocol(bad, PLACEMENTS)

    def test_rejections(self):
        def reject(clips=CLIPS, placements=PLACEMENTS):
            with self.assertRaises(ValueError):
                qa.protocol(clips, placements)
        # duplicate clip, unknown clip, carry excluded, unsorted frames
        reject(CLIPS + [dict(CLIPS[0])])
        reject([dict(c, name='attack') if c['name'] == 'flick' else dict(c) for c in CLIPS])
        reject([dict(c, name='carry') if c['name'] == 'flick' else dict(c) for c in CLIPS])
        reject([dict(c, frames=[139, 0]) if c['name'] == 'dead' else dict(c) for c in CLIPS])
        # missing Queen clip
        reject([c for c in CLIPS if c['name'] != 'born' or c['species'] != 'Queen'])
        # duplicate id, id overflow, unknown variant, bad flag, f_01 + larvae
        reject(placements=PLACEMENTS + [dict(PLACEMENTS[0])])
        reject(placements=[dict(PLACEMENTS[0], placement_id=1 << 32)])
        reject(placements=[dict(PLACEMENTS[0], variant='x_99')])
        reject(placements=[dict(PLACEMENTS[0], larvae=1)])
        reject(placements=[dict(placement_id=230012, variant='f_01', larvae=True, xyz=[0, 0, 0])])
        # non-finite / out-of-bounds transforms
        reject(placements=[dict(PLACEMENTS[0], xyz=[float('nan'), 0, 0])])
        reject(placements=[dict(PLACEMENTS[0], xyz=[100001, 0, 0])])
        reject(placements=[dict(PLACEMENTS[0], yaw=361)])
        # larvae placement without the Baby clip set
        reject([c for c in CLIPS if c['species'] != 'Baby'])
        # same clip set is fine when larvae are off
        qa.protocol([c for c in CLIPS if c['species'] != 'Baby'],
                    [dict(PLACEMENTS[0], larvae=False)])

    def test_full_clip_set_uses_reference_durations(self):
        sampled = {(s, n): [0, bb_clips['frames'] - 1]
                   for s, table in (('Queen', bb.QUEEN_CLIPS), ('Baby', bb.BABY_CLIPS))
                   for n, bb_clips in table.items()}
        clips = qa.full_clip_set(sampled)
        self.assertEqual(len(clips), 8 + 6)  # 8 Queen + Baby dead/deadpress/move/attack/attackfail/born
        for c in clips:
            self.assertEqual(c['duration'], bb.SPECIES[c['species']]['clips'][c['name']]['frames'])
        # and the full set validates, including a larvae placement
        qa.protocol(clips, [PLACEMENTS[0]])


class ConsistencyTests(unittest.TestCase):
    """Native policy constants must keep matching the #227 reference."""

    def test_reference_facts_used_by_the_actor(self):
        self.assertEqual(bb.QUEEN_PROPER_PARMS['rolling_time']['disc'], 3.5)
        self.assertEqual(bb.QUEEN_PROPER_PARMS['birth_interval']['disc'], 2.0)
        self.assertEqual(bb.QUEEN_PROPER_PARMS['max_births']['disc'], 50)
        self.assertEqual(bb.QUEEN_PROPER_PARMS['min_births']['disc'], 25)
        self.assertEqual(bb.QUEEN_GENERAL_DISC['health']['value'], 5000.0)
        self.assertEqual(bb.QUEEN_PROPER_PARMS['hob_health']['disc'], 3300.0)
        self.assertEqual(bb.QUEEN_GENERAL_DISC['territory_radius']['value'], 200.0)
        self.assertEqual(bb.QUEEN_GENERAL_DISC['attack_radius']['value'], 150.0)
        self.assertEqual(bb.QUEEN_GENERAL_DISC['attack_hit_angle']['value'], 25.0)
        self.assertEqual(bb.QUEEN_GENERAL_DISC['attack_damage']['value'], 10.0)
        self.assertEqual(bb.QUEEN_SHAKE_OFF_DISC['blows'], (30, 35, 45, 50))
        self.assertEqual(bb.QUEEN_SHAKE_OFF_DISC['sticking'], (5, 10, 15))
        self.assertEqual(bb.QUEEN_LARVAE['launch_speed']['disc'], 50.0)
        self.assertEqual(bb.BABY_GENERAL_DISC['health']['value'], 5.0)
        self.assertEqual(bb.BABY_GENERAL_DISC['move_speed']['value'], 40.0)
        self.assertEqual(bb.BABY_GENERAL_DISC['sight_radius']['value'], 800.0)
        self.assertEqual(bb.QUEEN_TERRITORY_CRASH_MARGIN, 50.0)
        self.assertEqual(bb.QUEEN_WAIT_IDLE_SLEEP_SECONDS, 30.0)

    def test_native_policy_executable(self):
        candidates = [ROOT / 'native' / 'pc_port']
        if os.environ.get('P2_NATIVE_PC_PORT'):
            candidates.insert(0, Path(os.environ['P2_NATIVE_PC_PORT']))
        candidates.append(ROOT.parent / 'p2-kimi-bulblax-native' / 'pc_port')
        include = next((c for c in candidates if (c / 'pc_p2_queen_policy.h').is_file()), None)
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if include is None or not compiler.is_file():
            return  # reference-consistency checks above still guard the contract
        source = ROOT / 'tests' / 'pikmin2_queen_policy.cpp'
        with tempfile.TemporaryDirectory(prefix='p2-queen-policy-') as tmp:
            exe = Path(tmp) / 'queen_policy.exe'
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(include),
                            str(source), '-o', str(exe)], check=True, capture_output=True, env=env)
            run = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            self.assertIn('PASS', run.stdout)


if __name__ == '__main__':
    unittest.main()
