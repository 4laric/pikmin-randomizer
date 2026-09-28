"""Tests for experimental.pikmin2_kogane_content (lane rd-p2-kogane-content, #494).

Hermetic: every test synthesizes its own extracted `<content>/Kogane/` tree
(`beetles.json` plus deterministic pose `.mod` bytes) and its own run
directory under `tmp_path`, so no retail disc image is required. The bank
clip shapes mirror the real `pikmin2_kogane_assets.extract` output on
GPVE01 (move/wait: 15 frames, sampled 0/7/14; damage: 50 frames, sampled
0/24/49); the sidecar grammar mirror below is transcribed from the native
loader sources:

* `native/pc_port/pc_p2_kogane_policy.h:8-17` (`p2kogane::read`: header,
  karada 0..64, 1..100 unique generator rows with species 9..11, exactly
  three unique clips from {move, wait, damage} with count 2..24, duration
  1..10000 and strictly increasing frames spanning [0, duration)).
* `native/pc_port/pc_p2_kogane.cpp:48` (pre-pass opens
  `assets/dataDir/courses/pikmin2room/kogane_<clip>_%02d.mod`) and `:61`
  (`gameflow.loadShape("courses/pikmin2room/kogane_<clip>_%02d.mod")` --
  one staged file satisfies both reads).
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_kogane_content import (  # noqa: E402
    NATIVE_TXT,
    ROOM,
    StagingError,
    plan,
    stage_kogane_host,
)

# Real bank shapes from extract(iso, out, pose_limit=3) on GPVE01.
BANK_CLIPS = {
    'move': dict(duration=15, frames=[0, 7, 14]),
    'wait': dict(duration=15, frames=[0, 7, 14]),
    'damage': dict(duration=50, frames=[0, 24, 49]),
}

SIDECAR = ('P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 '
           'move 2 15 0 14 wait 2 15 0 14 damage 2 50 0 49\n')


def make_source(root, clips=None, corrupt=None):
    """Write a synthetic extracted Kogane tree; `corrupt` mutates the manifest."""
    clips = clips if clips is not None else BANK_CLIPS
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_clips = []
    for clip, spec in clips.items():
        poses = []
        for ordinal, frame in enumerate(spec['frames']):
            name = f'{clip}_{ordinal:02d}.mod'
            data = b'KOGANE-POSE %s %d\n' % (clip.encode(), frame)
            (root / name).write_bytes(data)
            poses.append({
                'frame': frame,
                'file': name,
                'sha256': hashlib.sha256(data).hexdigest(),
            })
        manifest_clips.append({
            'file': f'{clip}.bca',
            'events': [],
            'sha256': hashlib.sha256(b'KOGANE-BCA %s' % clip.encode()).hexdigest(),
            'source_frames': spec['duration'],
            'status': 'converted',
            'poses': poses,
        })
    document = {
        'schema': 1,
        'family': 'Kogane',
        'species': {
            'kogane': {'enemy_id': 9},
            'wealthy': {'enemy_id': 10},
            'fart': {'enemy_id': 11},
        },
        'shared': {'joints': ['world_root'], 'clips': manifest_clips},
    }
    if corrupt is not None:
        corrupt(document)
    (root / 'beetles.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return root


def make_run(root, sidecar=SIDECAR):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    if sidecar is not None:
        (run / NATIVE_TXT).write_text(sidecar, encoding='ascii')
    return run


def test_staged_files_match_native_open_shape(tmp_path):
    """Each staged file is the exact bank mesh at the sidecar-selected ordinal."""
    source = make_source(tmp_path / 'Kogane')
    run = make_run(tmp_path / 'run')
    receipt = stage_kogane_host(source, run)
    # Sidecar count=2 per clip: exactly indices 00,01 -- the third bank pose
    # (ordinal 02) is never opened by setup and is never staged.
    expected = [f'kogane_{clip}_{ii:02d}.mod'
                for clip in ('move', 'wait', 'damage') for ii in (0, 1)]
    assert sorted(receipt['files']) == sorted(str(ROOM / name) for name in expected)
    for clip in ('move', 'wait', 'damage'):
        for ordinal in (0, 1):
            staged = run / ROOM / f'kogane_{clip}_{ordinal:02d}.mod'
            # Ordinal selection, not sampled-frame selection: move_01 carries
            # bank frame 7, matching native `%02d` positional indexing.
            frame = BANK_CLIPS[clip]['frames'][ordinal]
            assert staged.read_bytes() == b'KOGANE-POSE %s %d\n' % (clip.encode(), frame)
    assert not (run / ROOM / 'kogane_move_02.mod').exists()
    assert receipt['species'] == 'Kogane' and receipt['source_id'] == 9
    assert receipt['staged'] == 'written'
    assert receipt['clips']['move'] == {'count': 2, 'frames': [0, 14]}


def test_repeat_call_is_noop(tmp_path):
    source = make_source(tmp_path / 'Kogane')
    run = make_run(tmp_path / 'run')
    first = stage_kogane_host(source, run)
    stamps = {name: (tmp_path / 'run' / name).stat().st_mtime_ns for name in first['files']}
    second = stage_kogane_host(source, run)
    assert second['staged'] == 'existing_identical'
    assert second['files'] == first['files']
    assert {name: (tmp_path / 'run' / name).stat().st_mtime_ns
            for name in first['files']} == stamps


def test_conflicting_staged_file_refused_before_write(tmp_path):
    source = make_source(tmp_path / 'Kogane')
    run = make_run(tmp_path / 'run')
    stage_kogane_host(source, run)
    victim = run / ROOM / 'kogane_wait_00.mod'
    victim.write_bytes(b'CONFLICT')
    missing = run / ROOM / 'kogane_move_00.mod'
    missing.unlink()
    with pytest.raises(StagingError):
        stage_kogane_host(source, run)
    assert victim.read_bytes() == b'CONFLICT'
    assert not missing.exists()


def test_missing_manifest_raises(tmp_path):
    source = Path(tmp_path / 'Kogane')
    source.mkdir()
    run = make_run(tmp_path / 'run')
    with pytest.raises(StagingError):
        stage_kogane_host(source, run)


def test_missing_mesh_raises(tmp_path):
    source = make_source(tmp_path / 'Kogane')
    (source / 'damage_01.mod').unlink()
    run = make_run(tmp_path / 'run')
    with pytest.raises(StagingError):
        stage_kogane_host(source, run)


def test_hash_mismatch_raises(tmp_path):
    source = make_source(tmp_path / 'Kogane')
    (source / 'move_00.mod').write_bytes(b'TAMPERED')
    run = make_run(tmp_path / 'run')
    with pytest.raises(StagingError):
        stage_kogane_host(source, run)


def test_missing_sidecar_raises(tmp_path):
    source = make_source(tmp_path / 'Kogane')
    run = make_run(tmp_path / 'run', sidecar=None)
    with pytest.raises(StagingError):
        stage_kogane_host(source, run)


def test_malformed_sidecar_raises(tmp_path):
    source = make_source(tmp_path / 'Kogane')
    for bad in (
            'P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 '
            'move 2 15 0 14 wait 2 15 0 14 damage 2 50 0 49 EXTRA\n',
            'P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 '
            'move 2 15 0 14 wait 2 15 0 14 nap 2 50 0 49\n',
            'P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 '
            'move 2 15 0 14 wait 2 15 0 14 damage 2 50 0 48\n',
    ):
        run = make_run(tmp_path / f'run-{abs(hash(bad)) % 100000}', sidecar=bad)
        with pytest.raises(StagingError):
            stage_kogane_host(source, run)


def test_sidecar_count_beyond_bank_poses_raises(tmp_path):
    """A sidecar asking for 3 wait poses when the bank holds 2 fails closed."""
    source = make_source(tmp_path / 'Kogane', clips={
        'move': dict(duration=15, frames=[0, 14]),
        'wait': dict(duration=15, frames=[0, 14]),
        'damage': dict(duration=50, frames=[0, 49]),
    })
    sidecar = ('P2_KOGANE_NATIVE_1 karada 0 actors 1 219001 9 '
               'move 2 15 0 14 wait 3 15 0 7 14 damage 2 50 0 49\n')
    run = make_run(tmp_path / 'run', sidecar=sidecar)
    with pytest.raises(StagingError):
        stage_kogane_host(source, run)


def test_unconverted_bank_clip_raises(tmp_path):
    source = make_source(
        tmp_path / 'Kogane',
        corrupt=lambda doc: doc['shared']['clips'][0].update(status='unsupported', poses=[]))
    run = make_run(tmp_path / 'run')
    with pytest.raises(StagingError):
        stage_kogane_host(source, run)


def test_plan_writes_nothing(tmp_path):
    source = make_source(tmp_path / 'Kogane')
    run = make_run(tmp_path / 'run')
    mesh_files, clips, digest = plan(source, run)
    assert sorted(mesh_files) == sorted(
        f'kogane_{clip}_{ii:02d}.mod'
        for clip in ('move', 'wait', 'damage') for ii in (0, 1))
    assert [name for name, _count, _frames in clips] == ['move', 'wait', 'damage']
    assert len(digest) == 64
    assert [p.name for p in (run / ROOM).iterdir()] == []
