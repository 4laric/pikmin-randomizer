"""Tests for experimental.pikmin2_dangomushi_content (Crawbster identity).

Hermetic: every test synthesizes its own extracted ``<content>/DangoMushi/``
tree (``dangomushi.json`` plus deterministic
``snake_DangoMushi_<clip>_%02d.mod`` bytes) under ``tmp_path``, so no retail
disc image or cross-lane staging area is required. The clip/event fixtures
reuse the audited source values
(``experimental.pikmin2_snagret_assets.EXPECTED_EVENTS['DangoMushi']``). The
native grammar mirrors below are transcribed from the loader sources:

* ``engine/pc_port/pc_p2_batch3.cpp`` ``parseActors`` (``P2_<X>_ACTORS_1
  <count>`` + ``<generator> <species>`` rows, 1..100 rows, no trailing data),
  ``parseBank`` (``P2_<X>_BANK_1`` header, ``species <Species> <id>`` rows
  before ``clip <Species> <name> <frames> <events> poses <poses> [<status>]
  <status>`` rows, poses in 0..64) and ``loadPose`` (room-relative
  ``<prefix>_<Species>_<clip>_%02d.mod`` with the ``snake`` snagret prefix).
* ``engine/pc_port/pc_p2_batch2_clock.h:102-136`` (``parseEvents``: ``-`` or
  ``frame:key,...`` with frame in 0..100000).
* ``engine/pc_port/pc_p2_dangomushi.cpp:737-806``
  (``pc_p2_dangomushi_setup``: keeps ``species == "DangoMushi"`` bank rows
  with the ``status`` keyword tolerated, loops on fly/wait/move, rolls on
  ``attack`` event 4 and flicks on ``attack_2`` event 2, then binds
  ``species == "DangoMushi"`` actor rows to ``TEKI_Chappy`` hosts and enters
  ``DANGO_STAY`` on ``fly``).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_dangomushi_content import (  # noqa: E402
    ACTORS_TXT,
    BANK_TXT,
    REQUIRED_CLIPS,
    ROOM,
    StagingError,
    plan,
    stage_dangomushi,
    validate_source,
)

# Audited DangoMushi key events (snagret_assets.EXPECTED_EVENTS['DangoMushi']):
# the empty-event clip (recover) exercises the `-` token path.
CLIPS = {
    'fly.bca': dict(frames=[0, 13, 30, 35], duration=40,
                    events=[[13, 2], [30, 3], [35, 4]]),
    'wait.bca': dict(frames=[0, 20, 39], duration=40,
                     events=[[0, 0], [39, 1]]),
    'move.bca': dict(frames=[0, 8, 19], duration=20,
                     events=[[0, 0], [8, 2], [19, 1]]),
    'attack.bca': dict(frames=[0, 6, 17, 23, 50, 100, 118], duration=120,
                       events=[[6, 2], [17, 3], [23, 4], [50, 0], [100, 1],
                               [118, 5]]),
    'attack_2.bca': dict(frames=[0, 26, 32, 38, 50, 57, 65], duration=70,
                         events=[[26, 2], [32, 3], [38, 2], [50, 3], [57, 2],
                                 [65, 3]]),
    'turn.bca': dict(frames=[0, 10, 32, 81, 108, 114], duration=120,
                     events=[[10, 2], [32, 0], [81, 1], [108, 3], [114, 4]]),
    'recover.bca': dict(frames=[0, 20], duration=30, events=[[20, 2]]),
    'dead.bca': dict(frames=[0, 32, 40], duration=50,
                     events=[[32, 2], [40, 3]]),
    'carry.bca': dict(frames=[0, 10, 29], duration=30,
                      events=[[10, 0], [29, 1]]),
}

ACTORS = [(219094, 'DangoMushi')]
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def make_source(root, clips=None, corrupt=None):
    """Write a synthetic extracted DangoMushi tree; `corrupt` mutates it."""
    clips = clips if clips is not None else CLIPS
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_clips = []
    for clip, spec in clips.items():
        stem = Path(clip).stem
        poses = []
        for index, frame in enumerate(spec['frames']):
            name = f'snake_DangoMushi_{stem}_{index:02}.mod'
            data = b'DANGOMUSHI-POSE %s %d\n' % (clip.encode(), frame)
            (root / name).write_bytes(data)
            poses.append({
                'frame': frame,
                'file': name,
                'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest(),
            })
        manifest_clips.append({
            'file': clip,
            'events': [list(event) for event in spec['events']],
            'source_frames': spec['duration'],
            'sha256': hashlib.sha256(b'DANGOMUSHI-BCA %s' % clip.encode()).hexdigest(),
            'status': 'converted',
            'poses': poses,
        })
    document = {
        'schema': 1,
        'species': 'DangoMushi',
        'enemy_id': 94,
        'joints': ['world_root', 'back_born', 'tail01'],
        'clips': manifest_clips,
    }
    if corrupt is not None:
        corrupt(document)
    (root / 'dangomushi.json').write_text(json.dumps(document, indent=2) + '\n',
                                          encoding='utf-8')
    return root


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


def _parse_actors(text):
    """Strict mirror of batch-3 parseActors plus the DangoMushi actor scan."""
    tokens = text.split()
    assert tokens[0] == 'P2_SNAGRET_ACTORS_1'
    count = int(tokens[1])
    assert 1 <= count <= 100
    assert len(tokens) == 2 + 2 * count
    wanted = {}
    for index in range(2, len(tokens), 2):
        generator = int(tokens[index])
        assert 0 < generator <= 0xFFFFFFFF
        assert generator not in wanted
        wanted[generator] = tokens[index + 1]
    return wanted


def _parse_bank(text):
    """Strict mirror of batch-3 parseBank plus the DangoMushi clip scan."""
    tokens = text.split()
    assert tokens[0] == 'P2_SNAGRET_BANK_1'
    species_blocks, current, pos = {}, None, 1
    while pos < len(tokens):
        word = tokens[pos]
        if word == 'species':
            current = tokens[pos + 1]
            assert tokens[pos + 2] == str(
                {'DangoMushi': 94, 'SnakeCrow': 34, 'SnakeWhole': 70}[current])
            assert current not in species_blocks
            species_blocks[current] = {}
            pos += 3
        elif word == 'clip':
            assert current is not None
            sp, name = tokens[pos + 1], tokens[pos + 2]
            assert sp == current
            frames, events, marker = int(tokens[pos + 3]), tokens[pos + 4], tokens[pos + 5]
            poses = int(tokens[pos + 6])
            assert marker == 'poses' and 0 <= poses <= 64
            value = tokens[pos + 7]
            if value == 'status':
                status, width = tokens[pos + 8], 9
            else:
                status, width = value, 8
            assert status == 'converted'
            if events != '-':
                for pair in events.split(','):
                    frame, kind = pair.split(':')
                    assert 0 <= int(frame) <= 100000
            species_blocks[current][name] = (frames, events, poses)
            pos += width
            if pos < len(tokens) and tokens[pos] == 'frames':
                # Optional P2_BANK_FRAMES_1 trailer (#895): 0..frames-1, rising.
                listed = [int(v) for v in tokens[pos + 1].split(',')]
                assert len(listed) == poses and listed[0] == 0 and listed[-1] == frames - 1
                assert all(a < b for a, b in zip(listed, listed[1:]))
                pos += 2
        else:
            raise AssertionError(f'unexpected bank token: {word}')
    assert species_blocks
    return species_blocks


def test_stage_dangomushi(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    receipt = stage_dangomushi(source, run, ACTORS)
    assert receipt['species'] == 'DangoMushi' and receipt['source_id'] == 94
    assert receipt['generators'] == [219094]

    actors = (run / ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219094: 'DangoMushi'}

    bank = (run / BANK_TXT).read_text(encoding='ascii')
    blocks = _parse_bank(bank)
    assert set(blocks) == {'DangoMushi'}
    for required in REQUIRED_CLIPS:
        assert required in blocks['DangoMushi']
    # The roll/flick gates the native setup reads.
    assert blocks['DangoMushi']['attack'][1].split(',')[2] == '23:4'
    assert blocks['DangoMushi']['attack_2'][1].split(',')[0] == '26:2'
    # Canonical bank_text shape carries the literal `status` keyword.
    assert 'poses 4 status converted' in bank

    room_files = sorted(p.name for p in (run / ROOM).glob('*.mod'))
    assert room_files and all(name.startswith('snake_DangoMushi_') for name in room_files)


def test_stage_is_idempotent_and_conflicts_refused(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    first = stage_dangomushi(source, run, ACTORS)
    assert first['staged'] == 'written'
    second = stage_dangomushi(source, run, ACTORS)
    assert second['staged'] == 'existing_identical'
    assert second['files'] == first['files']

    (run / BANK_TXT).write_bytes(b'P2_SNAGRET_BANK_1\nspecies DangoMushi 94\n')
    with pytest.raises(StagingError, match='conflicting'):
        stage_dangomushi(source, run, ACTORS)


def test_validate_source_fails_closed(tmp_path):
    source = make_source(tmp_path / 'content')
    assert validate_source(source) is True
    empty = tmp_path / 'empty'
    empty.mkdir()
    with pytest.raises(StagingError):
        validate_source(empty)


def test_plan_rejects_bad_actors_and_anchors(tmp_path):
    source = make_source(tmp_path / 'content')
    with pytest.raises(StagingError):
        plan(source, [])
    with pytest.raises(StagingError):
        plan(source, [(0, 'DangoMushi')])
    with pytest.raises(StagingError):
        plan(source, [(219094, 'DangoMushi'), (219094, 'DangoMushi')])
    with pytest.raises(StagingError):
        plan(source, [(219094, 'SnakeCrow')])

    no_anchor = {name: spec for name, spec in CLIPS.items()
                 if Path(name).stem != 'fly'}
    make_source(tmp_path / 'no-anchor', clips=no_anchor)
    with pytest.raises(StagingError, match='anchor'):
        plan(tmp_path / 'no-anchor', ACTORS)


def test_plan_rejects_hash_mismatch_and_identity_mismatch(tmp_path):
    source = make_source(tmp_path / 'content')
    (source / 'snake_DangoMushi_move_00.mod').write_bytes(b'tampered')
    with pytest.raises(StagingError, match='hash mismatch'):
        plan(source, ACTORS)

    make_source(tmp_path / 'bad-id',
                corrupt=lambda document: document.update(enemy_id=70))
    with pytest.raises(StagingError, match='identity mismatch'):
        plan(tmp_path / 'bad-id', ACTORS)


def test_family_install_dangomushi_identity(tmp_path):
    """DangoMushi binds through the lane-05 family layer, not the proxy path."""
    from experimental import pikmin2_family_install as family_install

    assert family_install.resolve_family(94) == 'dangomushi'
    assert family_install.resolve_family('DangoMushi') == 'dangomushi'

    content_root = tmp_path / 'content'
    make_source(content_root / 'DangoMushi')
    retail = tmp_path / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    run = tmp_path / 'run'
    layout = {'bindings': [{'target': 'gen-094', 'source_id': 94,
                            'enum_name': 'DangoMushi'}]}
    receipt = family_install.install_layout(
        run, layout, content_root, {'gen-094': 219094}, retail_assets=retail)
    assert set(receipt['receipts']) == {'gen-094'}
    actors = (run / ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219094: 'DangoMushi'}
    bank = (run / BANK_TXT).read_text(encoding='ascii')
    assert set(_parse_bank(bank)) == {'DangoMushi'}


def test_proxy_and_dangomushi_coexistence_fails_closed(tmp_path):
    """A restored proxy declaration colliding with the identity row fails."""
    import shutil
    from pathlib import Path as _Path

    from randomizer import p2_proxy as proxy

    proxy_dir = tmp_path / 'p2_proxy'
    shutil.copytree(_Path(proxy.__file__).parent, proxy_dir,
                    ignore=shutil.ignore_patterns('__pycache__'))
    (proxy_dir / '94_DangoMushi.json').write_text(
        '{"schema": 1, "source_id": 94, "enum_name": "DangoMushi", '
        '"host_teki": 4, "pose_limit": 4}\n', encoding='utf-8')
    with pytest.raises(ValueError, match='non-proxy'):
        proxy.load_rows(directory=proxy_dir)
