"""Tests for experimental.pikmin2_sarai_install (lane rd-p2-sarai-install, #348).

Hermetic: every test synthesizes its own extracted `<content>/Sarai/` tree
(`sarai.json` plus deterministic pose `.mod` bytes) under `tmp_path`, so no
retail disc image or cross-lane staging area is required. The native grammar
mirrors below are transcribed from the loader sources:

* `engine/pc_port/pc_p2_demon_pose_bank.h:13-41` (`P2DemonPoseBank::load`,
  shared verbatim by the Sarai bank via `pc_p2_sarai_pose_bank.h:7-8`).
* `engine/pc_port/pc_p2_sarai_manager.cpp:52-65` (`readRestOffsets`,
  `P2_DEMON_MOUTHS_1` rest frame), `:67-81` (`buildHost` load order) and
  `:80-96` (retail table plus the five required motions).
* `engine/pc_port/pc_p2_motion_events.h:25-52` (`p2retail::read`).
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_sarai_install import (  # noqa: E402
    EVENTS_TXT,
    MOUTH_TXT,
    POSE_BANKS,
    REST_MOD,
    ROOM,
    StagingError,
    plan,
    stage_sarai_host,
)

CLIPS = {
    'wait1.bca': dict(frames=[0, 10, 16, 17, 30, 49, 59], duration=60,
                      events=[[10, 0], [49, 1]]),
    'move1.bca': dict(frames=[0, 10, 16, 17, 19], duration=20,
                      events=[[0, 0], [19, 1]]),
    'attack1.bca': dict(frames=[0, 10, 13, 16, 17, 30, 49], duration=50,
                        events=[[10, 2], [13, 3], [30, 4]]),
    'waitact1.bca': dict(frames=[0, 8, 10, 16, 17, 19, 25, 29], duration=30,
                         events=[[8, 2], [19, 3], [25, 4]]),
    'waitact2.bca': dict(frames=[0, 10, 16, 17, 30, 39, 49], duration=50,
                         events=[[0, 0], [39, 1]]),
    'flick.bca': dict(frames=[0, 10, 13, 16, 17, 29], duration=30,
                      events=[[13, 2]]),
}

HEX64 = re.compile(r'^[0-9a-f]{64}$')


def _matrix(clip_index, frame):
    base = float(clip_index * 1000 + frame) + 0.25
    return [[base + row * 4 + col + 0.125 for col in range(4)] for row in range(3)]


def make_source(root, clips=None, corrupt=None):
    """Write a synthetic extracted Sarai tree; `corrupt` mutates the manifest."""
    clips = clips if clips is not None else CLIPS
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_clips = []
    for index, (clip, spec) in enumerate(clips.items()):
        poses = []
        for frame in spec['frames']:
            name = f'{Path(clip).stem}_{frame:04}.mod'
            data = b'SARAI-POSE %s %d\n' % (clip.encode(), frame)
            (root / name).write_bytes(data)
            poses.append({
                'frame': frame,
                'file': name,
                'sha256': hashlib.sha256(data).hexdigest(),
                'mouths': [
                    {'joint': 'rkamujnt', 'radius': 15,
                     'matrix': _matrix(index, frame)},
                    {'joint': 'lkamujnt', 'radius': 15,
                     'matrix': _matrix(index, frame + 1)},
                ],
            })
        manifest_clips.append({
            'file': clip,
            'events': [list(event) for event in spec['events']],
            'sha256': hashlib.sha256(b'SARAI-BCA %s' % clip.encode()).hexdigest(),
            'source_frames': spec['duration'],
            'status': 'converted',
            'poses': poses,
        })
    document = {
        'schema': 1,
        'species': 'Sarai',
        'enemy_id': 23,
        'joints': ['world_root', 'rkamujnt', 'lkamujnt'],
        'clips': manifest_clips,
    }
    if corrupt is not None:
        corrupt(document)
    (root / 'sarai.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return root


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


def _parse_bank(text, with_model):
    """Strict mirror of P2DemonPoseBank::load (demon_pose_bank.h:13-41)."""
    lines = text.split('\n')
    assert text.endswith('\n') and not text.endswith('\n\n')
    magic, digest, count = lines[0], lines[1], int(lines[2])
    assert magic in ('P2_DEMON_MOUTHS_1', 'P2_DEMON_POSES_2')
    assert HEX64.match(digest), digest
    assert 1 <= count <= 128
    rows = lines[3:]
    assert len(rows) == count + 1 and rows[-1] == ''
    parsed = []
    previous = -1
    for row in rows[:-1]:
        tokens = row.split(' ')
        frame = int(tokens[0])
        assert frame > previous and frame <= 100000
        previous = frame
        rest = tokens[1:]
        if with_model:
            model = rest[0]
            assert 5 <= len(model) <= 96 and model.endswith('.mod')
            assert re.fullmatch(r'[A-Za-z0-9_]+', model[:-4])
            rest = rest[1:]
        assert len(rest) == 24
        values = [float(token) for token in rest]
        assert all(math.isfinite(v) and abs(v) <= 1e6 for v in values)
        parsed.append((frame, tokens[1] if with_model else None, values))
    return magic, digest, parsed


def _parse_events(text):
    """Strict mirror of p2retail::read (motion_events.h:25-52)."""
    lines = [line for line in text.split('\n')]
    assert text.endswith('\n') and not text.endswith('\n\n')
    magic, registry, count = lines[0].split(' ')
    assert magic == 'P2_RETAIL_EVENTS_1' and HEX64.match(registry)
    assert 1 <= int(count) <= 256
    motions = {}
    cursor = 1
    for _ in range(int(count)):
        name, duration, attribute, sha, n = lines[cursor].split(' ')
        cursor += 1
        assert re.fullmatch(r'[a-z0-9_]+\.bca', name) and 5 <= len(name) <= 68
        assert HEX64.match(sha) and 1 <= int(duration) <= 10000 and 0 <= int(attribute) <= 4
        assert 0 <= int(n) <= 4096 and name not in motions
        events = []
        previous, loop_start = -1, None
        for _ in range(int(n)):
            frame, kind = (int(token) for token in lines[cursor].split(' '))
            cursor += 1
            assert frame >= previous and 0 <= frame < int(duration)
            assert 0 <= kind < 1000
            if kind == 0:
                loop_start = frame
            if kind == 1:
                assert loop_start is not None and frame > loop_start
            previous = frame
            events.append((frame, kind))
        motions[name] = (int(duration), int(attribute), sha, events)
    assert cursor == len(lines) - 1
    return registry, motions


def test_every_file_matches_manifest_and_native_grammar(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    receipt = stage_sarai_host(source, run)
    assert receipt['species'] == 'Sarai' and receipt['source_id'] == 23
    assert receipt['staged'] == 'written'
    manifest_digest = hashlib.sha256((source / 'sarai.json').read_bytes()).hexdigest()

    document = json.loads((source / 'sarai.json').read_text(encoding='utf-8'))
    by_clip = {entry['file']: entry for entry in document['clips']}
    expected_meshes = set()
    for clip, bank in POSE_BANKS:
        payload = (run / bank).read_text(encoding='ascii')
        magic, digest, rows = _parse_bank(payload, with_model=True)
        assert magic == 'P2_DEMON_POSES_2'
        assert digest == manifest_digest
        spec = CLIPS[clip]
        assert [frame for frame, _, _ in rows] == spec['frames']
        poses = by_clip[clip]['poses']
        for (frame, model, values), pose in zip(rows, poses):
            assert model == pose['file'] == f'{Path(clip).stem}_{frame:04}.mod'
            expected_meshes.add(model)
            room_mesh = run / ROOM / model
            assert room_mesh.is_file()
            assert room_mesh.read_bytes() == (source / model).read_bytes()
            assert hashlib.sha256(room_mesh.read_bytes()).hexdigest() == pose['sha256']
            expected = [float(format(v, '.17g')) for mouth in pose['mouths']
                        for row in mouth['matrix'] for v in row]
            assert values == expected

    mouth_payload = (run / MOUTH_TXT).read_text(encoding='ascii')
    magic, digest, rows = _parse_bank(mouth_payload, with_model=False)
    assert magic == 'P2_DEMON_MOUTHS_1' and digest == manifest_digest
    assert [frame for frame, _, _ in rows] == CLIPS['attack1.bca']['frames']
    # buildHost derives the rest offsets from the first mouth row's translation
    # columns (manager.cpp:62-63); the staged first row must carry them.
    rest = rows[0][2]
    assert (rest[3], rest[7], rest[11]) != (rest[15], rest[19], rest[23])

    events_payload = (run / EVENTS_TXT).read_text(encoding='ascii')
    _registry, motions = _parse_events(events_payload)
    for clip in ('wait1.bca', 'move1.bca', 'attack1.bca',
                 'waitact2.bca', 'waitact1.bca'):
        assert clip in motions, f'required retail motion missing: {clip}'
    for entry in document['clips']:
        duration, _attribute, sha, events = motions[entry['file']]
        assert duration == entry['source_frames']
        assert sha == entry['sha256']
        assert list(events) == [tuple(event) for event in entry['events']]

    rest_mesh = run / ROOM / REST_MOD
    assert rest_mesh.is_file()
    assert rest_mesh.read_bytes() == (run / ROOM / 'attack1_0000.mod').read_bytes()

    staged_meshes = {path.name for path in (run / ROOM).glob('*.mod')}
    assert staged_meshes == expected_meshes | {REST_MOD}
    assert set(receipt['files']) == (
        {bank for _, bank in POSE_BANKS} | {MOUTH_TXT, EVENTS_TXT}
        | {str(ROOM / name) for name in staged_meshes})


def test_second_call_is_noop_and_conflicts_refused(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    first = stage_sarai_host(source, run)
    before = {name: (run / name).read_bytes()
              for name in list(first['files'])}
    second = stage_sarai_host(source, run)
    assert second['staged'] == 'existing_identical'
    assert second['files'] == first['files']
    assert all((run / name).read_bytes() == data for name, data in before.items())

    (run / MOUTH_TXT).write_bytes(b'P2_DEMON_MOUTHS_1\n' + b'0' * 64 + b'\n1\n0 ' + b'0 ' * 24 + b'\n')
    with pytest.raises(StagingError):
        stage_sarai_host(source, run)
    # The refused rerun corrupts nothing else.
    assert (run / EVENTS_TXT).read_bytes() == before[EVENTS_TXT]


def test_missing_source_raises_staging_error(tmp_path):
    with pytest.raises(StagingError):
        stage_sarai_host(tmp_path / 'no-such-content', make_run(tmp_path / 'run'))

    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    (source / 'attack1_0010.mod').unlink()
    with pytest.raises(StagingError):
        stage_sarai_host(source, run)

    source = make_source(tmp_path / 'content-sha')
    run = make_run(tmp_path / 'run-sha')
    (source / 'wait1_0000.mod').write_bytes(b'tampered')
    with pytest.raises(StagingError):
        stage_sarai_host(source, run)

    def drop_clip(document):
        document['clips'] = [c for c in document['clips'] if c['file'] != 'move1.bca']
    source = make_source(tmp_path / 'content-clip', corrupt=drop_clip)
    with pytest.raises(StagingError):
        plan(source)

    def break_mouth(document):
        clip = next(c for c in document['clips'] if c['file'] == 'attack1.bca')
        clip['poses'][0]['mouths'][0]['joint'] = 'nosejnt'
    source = make_source(tmp_path / 'content-mouth', corrupt=break_mouth)
    with pytest.raises(StagingError):
        plan(source)

    def break_events(document):
        clip = next(c for c in document['clips'] if c['file'] == 'wait1.bca')
        clip['events'].append([99999, 2])
    source = make_source(tmp_path / 'content-events', corrupt=break_events)
    with pytest.raises(StagingError):
        plan(source)


def test_run_layout_refused(tmp_path):
    source = make_source(tmp_path / 'content')
    with pytest.raises(StagingError):
        stage_sarai_host(source, tmp_path / 'no-such-run')
    bare = tmp_path / 'bare'
    bare.mkdir()
    with pytest.raises(StagingError):
        stage_sarai_host(source, bare)
