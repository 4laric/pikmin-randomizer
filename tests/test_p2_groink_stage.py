"""Groink (78/97) native OWN staging (#888 WP5): formats, adapters, native round trip.

Hermetic: every ISO-reading path is replaced by a synthetic extractor tree
shaped exactly like ``pikmin2_minihoudai_assets.extract`` /
``pikmin2_cannon_projectile_assets.extract`` output. No retail bytes are used.
The native round trip compiles the engine-free native parser
(``pc_port/pc_p2_groink_fsm.cpp``) from ``engine/pc_port`` or from
``$P2_NATIVE_PC_PORT`` when a C++17 compiler is available, and otherwise skips.
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_groink_stage as groink  # noqa: E402
from experimental.pikmin2_groink_carcass_teki import sidecar_config  # noqa: E402

# Retail-shaped event rows (docs/PIKMIN2_CANNON_PROJECTILE_ASSETS.md:102).
EVENTS = {
    'walk': [[10, 0], [18, 2], [25, 1]],
    'search1': [],
    'turn1': [[5, 0], [16, 1]],
    'attack1': [[11, 2], [22, 3], [25, 4], [32, 5]],
    'flick1': [[10, 2]],
    'dead1': [[32, 2], [52, 3]],
    'type5': [[10, 0], [29, 1]],
    'rebirth': [[32, 2], [45, 3]],
}
FRAMES = {'walk': 36, 'search1': 60, 'turn1': 30, 'attack1': 44, 'flick1': 40,
          'dead1': 70, 'type5': 40, 'rebirth': 60}
JOINT = [[0.0, 0.0, 1.0, 1.5], [0.0, 1.0, 0.0, 32.25], [-1.0, 0.0, 0.0, 18.0]]

# Synthetic retail-layout enemyparm.txt: CreatureProps, general, proper; the
# proper fp11/fp12 deliberately collide with the general fp11/fp12 tags.
PARM = (
    '# CreatureProps\n{\n\t{s000} 4 0.500000 \t# friction\n\t{s003} 4 0.100000 \t# accel\n{_eof}\n}\n'
    '# EnemyParmsBase\n{\n\t{fp00} 4 1200.000000 \t# life\n\t{fp06} 4 60.000000 \t# speed\n'
    '\t{fp11} 4 70.000000 \t# private\n\t{fp12} 4 500.000000 \t# sight\n'
    '\t{fp14} 4 250.000000 \t# search\n\t{fp22} 4 15.000000 \t# radius\n'
    '\t{ip01} 4 20 \t# blowA\n{_eof}\n}\n'
    '# EnemyParmsBase\n{\n\t{fp11} 4 30.000000 \t# gauge\n\t{fp12} 4 10.000000 \t# respawn\n{_eof}\n}\n'
).encode('shift_jis')
FIXED_PARM = PARM.replace(b'1200.000000', b'700.000000').replace(
    b'{fp11} 4 30.000000', b'{fp11} 4 2.000000').replace(b'{fp12} 4 10.000000', b'{fp12} 4 118.000000')


def chunk(tag, payload):
    return struct.pack('>II', tag, len(payload)) + payload


def mesh(pose):
    """Minimal MOD: shared render resources (32/34/48) + a pose-dependent chunk."""
    return (chunk(0x10, struct.pack('>I', pose)) + chunk(32, b'mat') + chunk(34, b'tex')
            + chunk(48, b'tev') + chunk(0xffff, b''))


def sample(frames, limit):
    count = min(limit, frames)
    return [round(i * (frames - 1) / max(1, count - 1)) for i in range(count)]


def minihoudai_tree(root, muzzle=True, unsupported=()):
    """Shape of pikmin2_minihoudai_assets.extract output (identity + manifest + poses)."""
    root.mkdir(parents=True)
    (root / 'identity.json').write_text(json.dumps(dict(schema=1, source_id=78, enum_name='MiniHoudai')))
    (root / 'enemyparm.txt').write_bytes(PARM)
    (root / 'fixed-enemyparm.txt').write_bytes(FIXED_PARM)
    clips = []
    serial = 0
    for stem in groink.CLIPS:
        clip = dict(file=f'{stem}.bca', events=EVENTS[stem], source_frames=FRAMES[stem],
                    poses=[], muzzle_samples=[], unsupported_frames=[], status='converted')
        if stem in unsupported:
            clip['status'] = 'unsupported'
        else:
            for index, frame in enumerate(sample(FRAMES[stem], groink.POSE_LIMITS[stem])):
                name = groink.pose_name(stem, index)
                data = mesh(serial)
                serial += 1
                (root / name).write_bytes(data)
                clip['poses'].append(dict(file=name, frame=frame, sha256=hashlib.sha256(data).hexdigest()))
        clips.append(clip)
    manifest = dict(schema=1, species='MiniHoudai', enemy_id=78, enum_name='MiniHoudai', clips=clips,
                    muzzle=dict(clip='attack1', frame=25, joint_matrix=JOINT) if muzzle else None)
    (root / 'minihoudai.json').write_text(json.dumps(manifest))
    return root


def cannon_tree(root):
    """Shape of the cannon extractor output's FminiHoudai bank."""
    species = root / 'FminiHoudai'
    species.mkdir(parents=True)
    (species / 'enemyparm.txt').write_bytes(FIXED_PARM)
    clips = []
    for stem in groink.CLIPS:
        poses = []
        for index, frame in enumerate(sample(FRAMES[stem], 3)):
            name = f'cannon_FminiHoudai_{stem}_{index:02}.mod'
            data = mesh(1000 + index)
            (species / name).write_bytes(data)
            poses.append(dict(file=name, frame=frame, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        clips.append(dict(name=stem, source_frames=FRAMES[stem], events=EVENTS[stem], poses=poses,
                          status='converted'))
    manifest = dict(schema=1, policy='P2_CANNON_PROJECTILE_1', species=dict(FminiHoudai=dict(
        clips=clips, muzzle=dict(clip='attack1', frame=25, joint_matrix=JOINT))))
    (root / 'cannon_projectile.json').write_text(json.dumps(manifest))
    return root


def private_run(tmp_path, name='run'):
    run = tmp_path / name
    (run / groink.ROOM).mkdir(parents=True)
    return run


# ------------------------------------------------------------------ parms
def test_enemyparm_blocks_are_told_apart_by_content():
    general, proper = groink.parse_enemyparm(PARM)
    assert general['fp00'] == 1200.0 and general['fp11'] == 70.0 and general['fp12'] == 500.0
    assert proper == {'fp11': 30.0, 'fp12': 10.0}
    assert general['ip01'] == 20.0


@pytest.mark.parametrize('bad', [
    b'{\n\t{fp06} 4 80.0\n{_eof}\n}\n',                                   # no general block
    b'{\n\t{fp00} 4 1.0\n\t{fp14} 4 2.0\n\t{fp00} 4 3.0\n{_eof}\n}\n',    # conflicting duplicate
    b'{\n\t{fp00} 4 nan\n\t{fp14} 4 2.0\n{_eof}\n}\n',                    # nonfinite
    b'{\n\t{fp00} 4 0.0\n\t{fp14} 4 2.0\n{_eof}\n}\n',                    # nonphysical life
    b'{\n\t{fp00} 4\n',                                                    # truncated
])
def test_enemyparm_fails_closed(bad):
    with pytest.raises(groink.GroinkStageError):
        groink.parse_enemyparm(bad)


def test_gauge_profile_is_source_derived_not_the_fixture_profile():
    assert groink.gauge_profile(PARM) == (30.0, 10.0, 1200.0)
    assert groink.gauge_profile(FIXED_PARM) == (2.0, 118.0, 700.0)
    assert groink.gauge_profile(None) == groink.DEFAULT_GAUGE
    assert groink.gauge_profile(PARM) != (2.0, 3.0, 1200.0)


# ------------------------------------------------------------------ bank
def test_bank_round_trips_through_the_python_grammar(tmp_path):
    plan = groink.plan_minihoudai(minihoudai_tree(tmp_path / 'MiniHoudai'))
    parsed = groink.parse_bank(plan['bank'])
    assert sorted(parsed['clips']) == list(range(8))
    for anim, stem in enumerate(groink.CLIPS):
        clip = parsed['clips'][anim]
        assert clip['name'] == stem and clip['frames'] == FRAMES[stem]
        assert clip['events'] == [tuple(e) for e in EVENTS[stem]]
        assert clip['poses'] == sample(FRAMES[stem], groink.POSE_LIMITS[stem])
    assert parsed['muzzle'] == [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [1.5, 32.25, 18.0]]
    text = plan['bank'].decode('ascii')
    assert text.startswith('P2_GROINK_BANK_1 8\nclip 0 walk 36 3 10 0 18 2 25 1 '
                           '16 0 2 5 7 9 12 14 16 19 21 23 26 28 30 33 35\n')
    assert 'clip 3 attack1 44 4 11 2 22 3 25 4 32 5 16 ' in text  # 16 poses (#895)
    assert text.endswith('muzzle 0 0 -1 0 1 0 1 0 0 1.5 32.25 18\nEND\n')


@pytest.mark.parametrize('mutate, message', [
    (lambda c: c[0].update(frames=1), 'frame count'),
    (lambda c: c[0].update(events=[(40, 2)]), 'key event'),
    (lambda c: c[0].update(events=[(5, 2), (4, 3)]), 'key event'),
    (lambda c: c[0].update(poses=[0, 0]), 'pose frame'),
    (lambda c: c[0].update(poses=list(range(25))), 'too many'),
    (lambda c: c[1].update(anim_id=0), 'anim id'),
    (lambda c: c[0].update(name='two words'), 'clip name'),
])
def test_bank_writer_refuses_what_native_would_reject(mutate, message):
    clips = [dict(anim_id=0, name='walk', frames=36, events=[(10, 0)], poses=[0, 35]),
             dict(anim_id=1, name='search1', frames=60, events=[], poses=[])]
    mutate(clips)
    with pytest.raises(groink.GroinkStageError, match=message):
        groink.bank_text(clips)


@pytest.mark.parametrize('text', [
    'P2_GROINK_BANK_2 1\nclip 0 walk 36 0 0\nEND\n',
    'P2_GROINK_BANK_1 9\nEND\n',
    'P2_GROINK_BANK_1 1\nclip 0 walk 36 1 36 2 0\nEND\n',
    'P2_GROINK_BANK_1 1\nclip 0 walk 36 0 2 5 5\nEND\n',
    'P2_GROINK_BANK_1 1\nclip 0 walk 36 0 0\n',
    'P2_GROINK_BANK_1 1\nclip 0 walk 36 0 0\nmuzzle 1 2 3\nEND\n',
    'P2_GROINK_BANK_1 2\nclip 0 walk 36 0 0\nclip 0 walk 36 0 0\nEND\n',
])
def test_bank_reader_fails_closed_like_native(text):
    with pytest.raises(groink.GroinkStageError):
        groink.parse_bank(text)


# ------------------------------------------------------------------ plans + stage
def test_minihoudai_stage_writes_every_native_input(tmp_path):
    source = minihoudai_tree(tmp_path / 'MiniHoudai')
    run = private_run(tmp_path)
    receipt = groink.stage_from(source, run)
    assert (run / groink.PARMS_78).read_bytes() == PARM
    assert (run / groink.PARMS_97).read_bytes() == FIXED_PARM
    parsed = groink.parse_bank((run / groink.BANK_TXT).read_bytes())
    total = sum(groink.POSE_LIMITS.values())
    assert receipt['poses'] == total and receipt['muzzle'] is True
    room = run / groink.ROOM
    for clip in parsed['clips'].values():
        for index in range(len(clip['poses'])):
            assert (room / groink.pose_name(clip['name'], index)).is_file()
    assert len(list(room.glob('minihoudai_*.mod'))) == total
    assert total * len(mesh(0)) == receipt['pose_bytes']


def test_stage_without_private_room_writes_a_poseless_bank(tmp_path):
    source = minihoudai_tree(tmp_path / 'MiniHoudai')
    run = tmp_path / 'bare'
    run.mkdir()
    receipt = groink.stage_from(source, run)
    parsed = groink.parse_bank((run / groink.BANK_TXT).read_bytes())
    assert all(clip['poses'] == [] for clip in parsed['clips'].values())
    assert parsed['clips'][3]['events'] == [(11, 2), (22, 3), (25, 4), (32, 5)]
    assert receipt['poses'] == 0 and receipt['poses_skipped']


def test_unsupported_clip_stages_timing_without_poses(tmp_path):
    source = minihoudai_tree(tmp_path / 'MiniHoudai', unsupported=('search1',))
    run = private_run(tmp_path)
    groink.stage_from(source, run)
    parsed = groink.parse_bank((run / groink.BANK_TXT).read_bytes())
    assert parsed['clips'][1]['poses'] == [] and parsed['clips'][1]['frames'] == 60


def test_plan_rejects_tampered_or_reordered_trees(tmp_path):
    source = minihoudai_tree(tmp_path / 'a')
    (source / groink.pose_name('walk', 0)).write_bytes(mesh(999))
    with pytest.raises(groink.GroinkStageError, match='hash'):
        groink.plan_minihoudai(source)
    other = minihoudai_tree(tmp_path / 'b')
    manifest = json.loads((other / 'minihoudai.json').read_text())
    manifest['clips'][0], manifest['clips'][1] = manifest['clips'][1], manifest['clips'][0]
    (other / 'minihoudai.json').write_text(json.dumps(manifest))
    with pytest.raises(groink.GroinkStageError, match='clip order'):
        groink.plan_minihoudai(other)
    third = minihoudai_tree(tmp_path / 'c')
    (third / groink.pose_name('dead1', 1)).write_bytes(chunk(32, b'other') + chunk(34, b'tex')
                                                       + chunk(48, b'tev') + chunk(0xffff, b''))
    manifest = json.loads((third / 'minihoudai.json').read_text())
    for clip in manifest['clips']:
        for pose in clip['poses']:
            pose['sha256'] = hashlib.sha256((third / pose['file']).read_bytes()).hexdigest()
    (third / 'minihoudai.json').write_text(json.dumps(manifest))
    with pytest.raises(groink.GroinkStageError, match='render resources'):
        groink.plan_minihoudai(third)


def test_fminihoudai_plan_from_the_cannon_tree(tmp_path):
    plan = groink.plan_fminihoudai(cannon_tree(tmp_path / 'FminiHoudai'))
    assert sorted(plan['parms']) == [groink.PARMS_97] and plan['muzzle']
    assert [name for name, _ in plan['room']][:3] == [groink.pose_name('walk', i) for i in range(3)]
    parsed = groink.parse_bank(plan['bank'])
    assert parsed['clips'][5]['events'] == [(32, 2), (52, 3)]


def test_78_then_97_share_one_bank(tmp_path):
    run = private_run(tmp_path)
    groink.stage_from(minihoudai_tree(tmp_path / 'MiniHoudai'), run)
    bank = (run / groink.BANK_TXT).read_bytes()
    receipt = groink.stage_from(cannon_tree(tmp_path / 'FminiHoudai'), run)
    assert receipt['bank'] == 'kept' and (run / groink.BANK_TXT).read_bytes() == bank
    assert (run / groink.PARMS_97).read_bytes() == FIXED_PARM


def test_97_then_78_keeps_the_first_bank_and_refuses_conflicting_parms(tmp_path):
    run = private_run(tmp_path)
    groink.stage_from(cannon_tree(tmp_path / 'FminiHoudai'), run)
    receipt = groink.stage_from(minihoudai_tree(tmp_path / 'MiniHoudai'), run)
    assert receipt['bank'] == 'kept' and (run / groink.PARMS_78).read_bytes() == PARM
    (run / groink.PARMS_78).write_bytes(PARM + b'#')
    with pytest.raises(groink.GroinkStageError, match='refusing'):
        groink.stage_from(minihoudai_tree(tmp_path / 'again'), run)


def test_existing_bank_with_missing_poses_is_refused(tmp_path):
    run = private_run(tmp_path)
    groink.stage_from(minihoudai_tree(tmp_path / 'MiniHoudai'), run)
    (run / groink.ROOM / groink.pose_name('attack1', 3)).unlink()
    with pytest.raises(groink.GroinkStageError, match='missing poses'):
        groink.stage_from(cannon_tree(tmp_path / 'FminiHoudai'), run)


# ------------------------------------------------------------------ adapters
def test_minihoudai_adapter_stages_bank_parms_and_a_source_timeline_sidecar(tmp_path):
    from experimental.pikmin2_family_install import GROINK_TEKI_TXT, _adapt_minihoudai
    source = minihoudai_tree(tmp_path / 'MiniHoudai')
    run = private_run(tmp_path)
    receipt = _adapt_minihoudai(source, run, [(1254096625, 'MiniHoudai'), (5465461, 'MiniHoudai')])
    sidecar = (run / GROINK_TEKI_TXT).read_text(encoding='ascii')
    assert sidecar == sidecar_config(5465461, 0, 30.0, 10.0, 1200.0)
    assert '2.0 3.0 1200.0' not in sidecar
    assert receipt['carcass_profile'] == [30.0, 10.0, 1200.0]
    assert receipt['groink']['poses'] == sum(groink.POSE_LIMITS.values())
    for name in (groink.PARMS_78, groink.PARMS_97, groink.BANK_TXT):
        assert (run / name).is_file()
    # Repeat call is idempotent (Kurage-adapter contract).
    again = _adapt_minihoudai(source, run, [(5465461, 'MiniHoudai')])
    assert again['actors_config_sha256'] == receipt['actors_config_sha256']


def test_minihoudai_sidecar_parses_under_the_native_reader_shape(tmp_path):
    from experimental.pikmin2_family_install import GROINK_TEKI_TXT, _adapt_minihoudai
    run = private_run(tmp_path)
    _adapt_minihoudai(minihoudai_tree(tmp_path / 'MiniHoudai'), run, [(7, 'MiniHoudai')])
    tokens = (run / GROINK_TEKI_TXT).read_text(encoding='ascii').split()
    # p2groink::read: magic, count 1, generator>0, type, gauge, recovery, health, no tail.
    assert tokens[:2] == ['P2_GROINK_TEKI_1', '1'] and len(tokens) == 7
    assert int(tokens[2]) == 7 and int(tokens[3]) == 0
    gauge, recovery, health = map(float, tokens[4:])
    assert gauge >= 0 and recovery > 0 and health > 0


def test_cannon_adapter_stages_groink_inputs_only_for_fminihoudai(tmp_path, monkeypatch):
    from experimental import pikmin2_cannon_projectile_install as cannon
    from experimental.pikmin2_family_install import _installer
    calls = []
    monkeypatch.setattr(cannon, 'install', lambda source, run, actors: calls.append(actors) or {'cannon': True})
    source = cannon_tree(tmp_path / 'FminiHoudai')
    run = private_run(tmp_path)
    receipt = _installer('cannon_projectile')(source, run, [(9, 'FminiHoudai')])
    assert calls == [[(9, 'FminiHoudai')]] and receipt['cannon'] is True
    assert receipt['groink']['parms'] == [groink.PARMS_97]
    assert (run / groink.BANK_TXT).is_file()
    other = private_run(tmp_path, 'kabuto-run')
    receipt = _installer('cannon_projectile')(source, other, [(3, 'Kabuto')])
    assert 'groink' not in receipt and not (other / groink.BANK_TXT).exists()


def test_extractor_pose_limits_and_emission_frame():
    from experimental import pikmin2_minihoudai_assets as minihoudai
    assert minihoudai.clip_pose_limit('attack1') == groink.POSE_LIMITS['attack1'] == 16  # #895 density
    assert minihoudai.clip_pose_limit('attack1', 3) == 3
    assert minihoudai.emission_frame(EVENTS['attack1']) == 25
    with pytest.raises(ValueError):
        minihoudai.emission_frame([[11, 2]])
    assert all(2 <= n <= groink.MAX_POSES for n in groink.POSE_LIMITS.values())
    assert set(groink.POSE_LIMITS) == set(groink.CLIPS)


# ------------------------------------------------------------------ native
NATIVE_HARNESS = r'''
#include "pc_p2_groink_fsm.h"
#include <cstdio>
#include <fstream>
using namespace p2groinkfsm;
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    Bank bank = defaultBank();
    std::ifstream in(argv[1]);
    std::string error;
    if (!parseBank(in, bank, error)) { std::printf("BANK_FAIL %s\n", error.c_str()); return 1; }
    for (int a = 0; a < AnimCount; ++a) {
        const Clip& c = bank.clip[a];
        std::printf("clip %d %s %d %d", a, c.name.c_str(), c.frames, c.staged ? 1 : 0);
        for (const auto& e : c.events) std::printf(" e%d:%d", e.frame, e.type);
        for (int p : c.poses) std::printf(" p%d", p);
        std::printf("\n");
    }
    const P2GroinkMuzzle& m = bank.muzzle;
    std::printf("muzzle %d %g %g %g %g %g %g\n", bank.muzzleStaged ? 1 : 0, m.column0.x, m.column0.z,
                m.column2.x, m.column3.x, m.column3.y, m.column3.z);
    Params p;
    std::ifstream parm(argv[2]);
    if (!parseEnemyParm(parm, p, error)) { std::printf("PARM_FAIL %s\n", error.c_str()); return 1; }
    std::printf("parms %d %g %g %g %g %g %d\n", p.retail ? 1 : 0, p.health, p.sightRadius, p.privateRadius,
                p.healthGaugeTimer, p.respawnRate, p.shakeOffBlowA);
    return 0;
}
'''
NATIVE_SOURCES = ('pc_p2_groink_fsm.cpp', 'pc_p2_groink.cpp', 'pc_p2_groink_attack.cpp',
                  'pc_p2_groink_volley.cpp', 'pc_p2_groink_hit.cpp', 'pc_p2_groink_target.cpp')


def _native_dir():
    for candidate in (os.environ.get('P2_NATIVE_PC_PORT'), ROOT / 'engine' / 'pc_port'):
        if candidate and (Path(candidate) / 'pc_p2_groink_fsm.cpp').is_file():
            return Path(candidate)
    return None


def test_native_parser_accepts_the_staged_bank_and_parms(tmp_path):
    native = _native_dir()
    compiler = shutil.which('g++') or shutil.which('clang++')
    if native is None or compiler is None:
        pytest.skip('native Groink FSM sources or a C++17 compiler unavailable')
    run = private_run(tmp_path)
    groink.stage_from(minihoudai_tree(tmp_path / 'MiniHoudai'), run)
    source = tmp_path / 'harness.cpp'
    source.write_text(NATIVE_HARNESS)
    exe = tmp_path / 'harness'
    subprocess.run([compiler, '-std=c++17', '-I', str(native), str(source),
                    *[str(native / name) for name in NATIVE_SOURCES], '-o', str(exe)],
                   check=True, capture_output=True, text=True)
    out = subprocess.run([str(exe), str(run / groink.BANK_TXT), str(run / groink.PARMS_78)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.splitlines()
    assert lines[3].startswith('clip 3 attack1 44 1 e11:2 e22:3 e25:4 e32:5 p0 ')
    assert lines[0] == 'clip 0 walk 36 1 e10:0 e18:2 e25:1 ' + ' '.join(
        f'p{f}' for f in sample(36, groink.POSE_LIMITS['walk']))
    assert all(line.split()[4] == '1' for line in lines[:8])
    assert lines[8] == 'muzzle 1 0 -1 1 1.5 32.25 18'
    assert lines[9] == 'parms 1 1200 500 70 30 10 20'
