"""Giant Breadbug actor lane (#220 batch 4): profile/plan/install and native gate evidence tests."""
import json
import struct
import unittest
from pathlib import Path

import pytest

from experimental.pikmin2_giant_breadbug_actor import prepare, plan, install
from experimental.pikmin2_breadbug_visual import sha
from scripts.test_pikmin2_giant_breadbug_actor_native import evidence

from tests.test_pikmin2_breadbug_lane_install import fake_mod


def fake_lane_import(root):
    """Synthetic breadbug-lane-03 extraction with boss OoPanModoki + PanHouse nest."""
    root = Path(root)
    (root / 'OoPanModoki').mkdir(parents=True)
    (root / 'PanHouse').mkdir()
    clips = []
    for stem, frames in (('wait1', [0, 10, 29]), ('move1', [0, 10, 26])):
        duration = frames[-1] + 1
        poses = []
        for frame in frames:
            data = fake_mod()
            name = f'{stem}_{frame:03}.mod'
            (root / 'OoPanModoki' / name).write_bytes(data)
            poses.append(dict(frame=frame, file=name, sha256=sha(data)))
        clip_file = f'{stem}.mod'
        clips.append(dict(file=clip_file, status='sampled_poses_converted',
                          source_frames=duration, poses=poses))
    nest = fake_mod()
    (root / 'PanHouse/nest.mod').write_bytes(nest)
    lane = dict(schema=1, lane=213,
                classification={'39': {'spawnable': False}, '40': {'boss': True, 'name': 'OoPanModoki'},
                                '83': {'spawnable': False}},
                species={'OoPanModoki': {'clips': clips},
                         'PanHouse': {'static_pose': dict(file='nest.mod', sha256=sha(nest))}})
    (root / 'breadbug-lane.json').write_text(json.dumps(lane))
    return root


def fake_generator_row(identity, type_byte, marker=b'iket'):
    row = bytearray(b'    0.0v' + b'\0' * 88)
    struct.pack_into('<I', row, 8, identity)
    row[72:76] = marker
    row[80] = type_byte
    return bytes(row)


def write_gen(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = b'1.0v' + b'\0' * 16 + struct.pack('>I', len(rows)) + b''.join(rows)
    Path(path).write_bytes(data)


@pytest.fixture()
def profile(tmp_path):
    return prepare(fake_lane_import(tmp_path / 'lane'), tmp_path / 'profile') and tmp_path / 'profile'


def test_prepare_stages_clips_and_nest(tmp_path):
    out = tmp_path / 'profile'
    result = prepare(fake_lane_import(tmp_path / 'lane'), out)
    assert result['params'] == dict(health=2000, carry_speed=45, press_damage=100,
                                    press='purple_only', boss=True, bdt='empty_no_music',
                                    threshold='at_or_above1')
    names = sorted(p.name for p in (out / 'models').iterdir())
    assert names == ['lane_nest_nest.mod', 'lane_ootake_move1_000.mod', 'lane_ootake_move1_010.mod',
                     'lane_ootake_move1_026.mod', 'lane_ootake_wait1_000.mod', 'lane_ootake_wait1_010.mod',
                     'lane_ootake_wait1_029.mod']
    assert [c['name'] for c in result['clips']] == ['wait', 'move']


def test_prepare_rejects_spawnable_helper(tmp_path):
    lane = fake_lane_import(tmp_path / 'lane')
    data = json.loads((lane / 'breadbug-lane.json').read_text())
    data['classification']['83']['spawnable'] = True
    (lane / 'breadbug-lane.json').write_text(json.dumps(data))
    with pytest.raises(ValueError):
        prepare(lane, tmp_path / 'profile')


def test_plan_validates_generator_types(profile):
    giant = fake_generator_row(187001, 8)
    nest = fake_generator_row(187002, 12)
    config, files, metadata = plan(profile, [giant, nest], [(187001, 187002)])
    text = config.decode()
    assert text.startswith('P2_GIANT_BREADBUG_ACTOR_1\n')
    assert '187001 187002' in text
    assert 'lane_nest_nest.mod' in files
    with pytest.raises(ValueError):  # giant must be TEKI_Collec type 8
        plan(profile, [fake_generator_row(187001, 12), nest], [(187001, 187002)])
    with pytest.raises(ValueError):  # nest must be TEKI_Hollec type 12
        plan(profile, [giant, fake_generator_row(187002, 8)], [(187001, 187002)])
    with pytest.raises(ValueError):  # duplicate ids
        plan(profile, [giant, nest], [(187001, 187002), (187001, 187003)])
    with pytest.raises(ValueError):  # giant == nest
        plan(profile, [giant], [(187001, 187001)])


def test_install_refuses_overwrite(profile, tmp_path):
    run = tmp_path / 'run'
    room = run / 'assets/dataDir/courses/pikmin2room'
    room.mkdir(parents=True)
    write_gen(run / 'assets/dataDir/stages/chal0/default.gen',
              [fake_generator_row(187001, 8), fake_generator_row(187002, 12)])
    result = install(profile, run, [(187001, 187002)])
    assert (run / 'p2-giant-breadbug-actor.txt').read_bytes().startswith(b'P2_GIANT_BREADBUG_ACTOR_1')
    assert result['native_validated'] is False
    assert result['pairs'] == [[187001, 187002]]
    with pytest.raises(ValueError):
        install(profile, run, [(187001, 187002)])


FULL_LOG = '\n'.join([
    'P2_GIANT_BREADBUG_ACTOR_READY generator=187001 nest=187002 native_type=8 xyz=-150.000000,30.000000,1850.000000 boss=1 bdt=empty_no_music threshold=at_or_above1 health=2000 carryspeed=45 pressdamage=100',
    'P2_GIANT_NEST_BIRTH generator=187002 xyz=-150.000,30.000,1650.000',
    'P2_GIANT_ARENA_SQUAD count=20 color=red health=2000.0',
    'P2_GIANT_PRESS generator=187001 purple=0 resisted=1 health=2000.0',
    'P2_GIANT_PRESS generator=187001 purple=1 damage=100 health=1900.0',
    'P2_GIANT_ARENA_PRESS non_purple=resisted purple_damage=100 health=1900.0',
    'P2_GIANT_CONTEST_LOST generator=187001 carriers=2 strength=1.5 freeze=0.5s',
    'P2_GIANT_ARENA_CONTEST released=1 tick=77 strength=1.5 carriers=2',
    'P2_GIANT_DIGEST generator=187001 color=1 type=1 stomach=1',
    'P2_GIANT_DIGEST_HEAL generator=187001 health=2000.0',
    'P2_GIANT_ARENA_DIGEST healed=1 health=2000.0 tick=672',
    'P2_GIANT_DEFEATED generator=187001 thrown_back=2',
    'P2_GIANT_THROWUP generator=187001 pellets=2 nest=-150.000,9.172,1650.000',
    'P2_GIANT_ARENA_THROWUP pellets=1 xyz=-241.471,18.114,1608.481',
    'P2_GIANT_NEST_DEATH generator=187002',
    'P2_GIANT_BREADBUG_ACTOR_DRAW generator=187001 scale=2 texture_matrix_animation=gap_static_frames',
    'PASS P2_GIANT_BREADBUG_ARENA spawn_identity press contest digest_heal defeat_throwup nest_linked',
])


def test_evidence_full_pass():
    result = evidence(FULL_LOG, 0)
    assert result['passed']
    assert all(result['checks'].values())


def test_evidence_gate_mutations_fail():
    for old, new in [('health=2000.0\nP2_GIANT_PRESS generator=187001 purple=0', 'health=1999.0\nP2_GIANT_PRESS generator=187001 purple=0'),
                     ('purple=1 damage=100 health=1900.0', 'purple=1 damage=400 health=1600.0'),
                     ('strength=1.5', 'strength=2.5'),
                     ('P2_GIANT_DIGEST generator=187001', ''),
                     ('P2_GIANT_DIGEST_HEAL generator=187001 health=2000.0', 'P2_GIANT_DIGEST_HEAL generator=187001 health=1900.0'),
                     ('P2_GIANT_THROWUP', ''),
                     ('P2_GIANT_NEST_DEATH', ''),
                     ('PASS P2_GIANT_BREADBUG_ARENA', 'FAIL')]:
        assert not evidence(FULL_LOG.replace(old, new), 0)['passed'], old
    assert not evidence(FULL_LOG, 1)['passed']  # non-zero exit fails even with all gates


if __name__ == '__main__':
    unittest.main()
