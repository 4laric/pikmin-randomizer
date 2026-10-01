"""Tests for experimental.pikmin2_tamago_content (Mitite identity).

Hermetic: every test synthesizes its own extracted ``<content>/TamagoMushi/`` tree
(``tamagomushi.json`` plus deterministic ``ginv_TamagoMushi_<clip>_%02d.mod`` bytes)
under ``tmp_path``, so no retail disc image or cross-lane staging area is
required. The clip/event fixtures reuse the audited source values
(``experimental.pikmin2_ground_inverts_assets.EXPECTED_EVENTS['TamagoMushi']``).
The native grammar mirrors below are transcribed from the loader sources:

* ``engine/pc_port/pc_p2_batch2.cpp:95-120`` (``loadPose``: room-relative
  ``<prefix>_<Species>_<clip>_%02d.mod`` with prefix ``ginv``),
  ``:122-138`` (``parseActors``) and ``:140-170`` (``parseBank``).
* ``engine/pc_port/pc_p2_batch2_clock.h:102-136`` (``parseEvents``).
* ``engine/pc_port/pc_p2_tamago.cpp:378-421`` (``pc_p2_tamago_setup``: keeps
  ``species == "TamagoMushi"`` clip rows, then binds ``species ==
  "TamagoMushi"`` actor rows to ``TEKI_Chappy`` hosts and enters
  ``TAMAGO_APPEAR`` on ``set``).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_tamago_content import (  # noqa: E402
    REQUIRED_CLIPS,
    ROOM,
    StagingError,
    plan,
    stage_tamago_ground,
    validate_source,
)
from experimental import pikmin2_ground_species_content as ground  # noqa: E402

# Audited TamagoMushi key events (ground_inverts_assets.EXPECTED_EVENTS['TamagoMushi']):
# the empty-event clips (dead/dive) exercise the `-` token path.
CLIPS = {
    'dead.bca': dict(frames=[0, 10], duration=20, events=[]),
    'dive.bca': dict(frames=[0, 8], duration=16, events=[]),
    'move.bca': dict(frames=[0, 5, 9], duration=10, events=[[0, 0], [9, 1]]),
    'set.bca': dict(frames=[0, 2, 10], duration=12, events=[[2, 2]]),
    'wait.bca': dict(frames=[0, 7, 14], duration=15, events=[[0, 0], [14, 1]]),
    'carry.bca': dict(frames=[0, 10, 29], duration=30,
                      events=[[10, 0], [29, 1]]),
}

ACTORS = [(219068, 'TamagoMushi'), (219069, 'TamagoMushi')]
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def make_source(root, clips=None, corrupt=None):
    """Write a synthetic extracted TamagoMushi tree; `corrupt` mutates the manifest."""
    clips = clips if clips is not None else CLIPS
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_clips = []
    for clip, spec in clips.items():
        stem = Path(clip).stem
        poses = []
        for index, frame in enumerate(spec['frames']):
            name = f'ginv_TamagoMushi_{stem}_{index:02}.mod'
            data = b'TAMAGO-POSE %s %d\n' % (clip.encode(), frame)
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
            'sha256': hashlib.sha256(b'TAMAGO-BCA %s' % clip.encode()).hexdigest(),
            'status': 'converted',
            'poses': poses,
        })
    document = {
        'schema': 1,
        'species': 'TamagoMushi',
        'enemy_id': 68,
        'joints': ['world_root', 'body', 'kamu'],
        'clips': manifest_clips,
    }
    if corrupt is not None:
        corrupt(document)
    (root / 'tamagomushi.json').write_text(json.dumps(document, indent=2) + '\n',
                                       encoding='utf-8')
    return root


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


def _parse_actors(text):
    """Strict mirror of batch-2 parseActors plus the TamagoMushi setup actor scan."""
    tokens = text.split()
    assert tokens[0] == 'P2_GROUND_ACTORS_1'
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
    """Strict mirror of batch-2 parseBank plus the TamagoMushi setup clip scan."""
    tokens = text.split()
    assert tokens[0] == 'P2_GROUND_BANK_1'
    species_blocks, current, pos = {}, None, 1
    while pos < len(tokens):
        word = tokens[pos]
        if word == 'species':
            current = tokens[pos + 1]
            assert tokens[pos + 2] == str(
                {'ElecBug': 28, 'Sokkuri': 79, 'TamagoMushi': 68}[current])
            assert current not in species_blocks
            species_blocks[current] = {}
            pos += 3
        elif word == 'clip':
            assert current is not None
            sp, name = tokens[pos + 1], tokens[pos + 2]
            assert sp == current
            frames, events, marker = int(tokens[pos + 3]), tokens[pos + 4], tokens[pos + 5]
            poses, status = int(tokens[pos + 6]), tokens[pos + 7]
            assert marker == 'poses' and 0 <= poses <= 64 and status == 'converted'
            if events != '-':
                for pair in events.split(','):
                    frame, kind = pair.split(':')
                    assert 0 <= int(frame) <= 100000
            species_blocks[current][name] = (frames, events, poses)
            pos += 8
            # Optional P2_BANK_FRAMES_1 trailer (#895): one source frame per
            # pose, strictly increasing from 0 to the last source frame.
            if pos < len(tokens) and tokens[pos] == 'frames':
                listed = [int(value) for value in tokens[pos + 1].split(',')]
                assert len(listed) == poses and listed[0] == 0 and listed[-1] == frames - 1
                assert all(a < b for a, b in zip(listed, listed[1:]))
                pos += 2
        else:
            raise AssertionError(f'unexpected bank token: {word}')
    assert species_blocks
    return species_blocks


def test_stage_tamago_ground(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    receipt = stage_tamago_ground(source, run, ACTORS)
    assert receipt['species'] == 'TamagoMushi' and receipt['source_id'] == 68
    assert receipt['generators'] == [219068, 219069]

    actors = (run / ground.ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219068: 'TamagoMushi', 219069: 'TamagoMushi'}

    bank = (run / ground.BANK_TXT).read_text(encoding='ascii')
    blocks = _parse_bank(bank)
    assert set(blocks) == {'TamagoMushi'}
    for required in REQUIRED_CLIPS:
        assert required in blocks['TamagoMushi']
    assert blocks['TamagoMushi']['set'][1] == '2:2'
    assert blocks['TamagoMushi']['dead'][1] == '-'

    room_files = sorted(p.name for p in (run / ROOM).glob('*.mod'))
    assert room_files and all(name.startswith('ginv_TamagoMushi_') for name in room_files)


def test_stage_merges_with_sokkuri_rows(tmp_path):
    """TamagoMushi + Sokkuri share one seed's ground sidecars without conflict."""
    from experimental import pikmin2_sokkuri_content as sokkuri_content
    from tests.test_p2_sokkuri_content import make_source as make_sokkuri_source

    sokkuri = make_sokkuri_source(tmp_path / 'sokkuri')
    tamago = make_source(tmp_path / 'tamagomushi')
    run = make_run(tmp_path / 'run')
    sokkuri_content.stage_sokkuri_ground(sokkuri, run, [(219079, 'Sokkuri')])
    receipt = stage_tamago_ground(tamago, run, ACTORS)
    assert receipt['staged'] == 'written'

    actors = (run / ground.ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219079: 'Sokkuri',
                                     219068: 'TamagoMushi', 219069: 'TamagoMushi'}
    bank = (run / ground.BANK_TXT).read_text(encoding='ascii')
    blocks = _parse_bank(bank)
    assert set(blocks) == {'Sokkuri', 'TamagoMushi'}
    # Canonical family order, independent of staging order.
    assert bank.index('species TamagoMushi 68') < bank.index('species Sokkuri 79')

    # Restaging either species over the merged files is a no-op success.
    again = sokkuri_content.stage_sokkuri_ground(sokkuri, run, [(219079, 'Sokkuri')])
    assert again['staged'] == 'existing_identical'
    assert stage_tamago_ground(tamago, run, ACTORS)['staged'] == 'existing_identical'


def test_stage_refuses_generator_rebound_to_other_species(tmp_path):
    from experimental import pikmin2_sokkuri_content as sokkuri_content
    from tests.test_p2_sokkuri_content import make_source as make_sokkuri_source

    sokkuri = make_sokkuri_source(tmp_path / 'sokkuri')
    tamago = make_source(tmp_path / 'tamagomushi')
    run = make_run(tmp_path / 'run')
    sokkuri_content.stage_sokkuri_ground(sokkuri, run, [(219079, 'Sokkuri')])
    with pytest.raises(StagingError, match='already bound'):
        stage_tamago_ground(tamago, run, [(219079, 'TamagoMushi')])
    assert _parse_actors((run / ground.ACTORS_TXT).read_text(encoding='ascii')) == {
        219079: 'Sokkuri'}


def test_stage_is_idempotent_and_conflicts_refused(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    first = stage_tamago_ground(source, run, ACTORS)
    assert first['staged'] == 'written'
    second = stage_tamago_ground(source, run, ACTORS)
    assert second['staged'] == 'existing_identical'
    assert second['files'] == first['files']

    mesh = sorted((run / ROOM).glob('ginv_TamagoMushi_*.mod'))[0]
    mesh.write_bytes(b'corrupted-mesh')
    with pytest.raises(StagingError, match='conflicting'):
        stage_tamago_ground(source, run, ACTORS)


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
        plan(source, [(0, 'TamagoMushi')])
    with pytest.raises(StagingError):
        plan(source, [(219068, 'TamagoMushi'), (219068, 'TamagoMushi')])
    with pytest.raises(StagingError):
        plan(source, [(219068, 'Sokkuri')])

    no_anchor = {name: spec for name, spec in CLIPS.items()
                 if Path(name).stem != 'wait'}
    make_source(tmp_path / 'no-anchor', clips=no_anchor)
    with pytest.raises(StagingError, match='anchor'):
        plan(tmp_path / 'no-anchor', ACTORS)


def test_plan_rejects_hash_mismatch_and_identity_mismatch(tmp_path):
    source = make_source(tmp_path / 'content')
    (source / 'ginv_TamagoMushi_move_00.mod').write_bytes(b'tampered')
    with pytest.raises(StagingError, match='hash mismatch'):
        plan(source, ACTORS)

    make_source(tmp_path / 'bad-id',
                corrupt=lambda document: document.update(enemy_id=79))
    with pytest.raises(StagingError, match='identity mismatch'):
        plan(tmp_path / 'bad-id', ACTORS)


def test_family_install_tamago_identity(tmp_path):
    """TamagoMushi binds through the lane-05 family layer, not the proxy path."""
    from experimental import pikmin2_family_install as family_install

    assert family_install.resolve_family(68) == 'tamago'
    assert family_install.resolve_family('TamagoMushi') == 'tamago'

    content_root = tmp_path / 'content'
    make_source(content_root / 'TamagoMushi')
    retail = tmp_path / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    run = tmp_path / 'run'
    layout = {'bindings': [{'target': 'gen-068', 'source_id': 68,
                            'enum_name': 'TamagoMushi'}]}
    receipt = family_install.install_layout(
        run, layout, content_root, {'gen-068': 219068}, retail_assets=retail)
    assert set(receipt['receipts']) == {'gen-068'}
    actors = (run / ground.ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219068: 'TamagoMushi'}
    bank = (run / ground.BANK_TXT).read_text(encoding='ascii')
    assert set(_parse_bank(bank)) == {'TamagoMushi'}


def test_proxy_and_tamago_coexistence_fails_closed(tmp_path):
    """A restored proxy declaration colliding with the identity row fails."""
    import shutil
    from pathlib import Path as _Path

    from randomizer import p2_proxy as proxy

    proxy_dir = tmp_path / 'p2_proxy'
    shutil.copytree(_Path(proxy.__file__).parent, proxy_dir,
                    ignore=shutil.ignore_patterns('__pycache__'))
    (proxy_dir / '68_TamagoMushi.json').write_text(
        '{"schema": 1, "source_id": 68, "enum_name": "TamagoMushi", '
        '"host_teki": 3, "pose_limit": 4}\n', encoding='utf-8')
    with pytest.raises(ValueError, match='non-proxy'):
        proxy.load_rows(directory=proxy_dir)


def test_three_ground_identities_share_one_layout(tmp_path):
    """Sokkuri + ElecBug + TamagoMushi stage one seed's sidecars together."""
    from experimental import pikmin2_family_install as family_install
    from tests.test_p2_elecbug_content import make_source as make_elecbug_source
    from tests.test_p2_sokkuri_content import make_source as make_sokkuri_source

    content_root = tmp_path / 'content'
    make_sokkuri_source(content_root / 'Sokkuri')
    make_elecbug_source(content_root / 'ElecBug')
    make_source(content_root / 'TamagoMushi')
    retail = tmp_path / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    run = tmp_path / 'run'
    layout = {'bindings': [
        {'target': 'gen-079', 'source_id': 79, 'enum_name': 'Sokkuri'},
        {'target': 'gen-028', 'source_id': 28, 'enum_name': 'ElecBug'},
        {'target': 'gen-068', 'source_id': 68, 'enum_name': 'TamagoMushi'},
    ]}
    receipt = family_install.install_layout(
        run, layout, content_root,
        {'gen-079': 219079, 'gen-028': 219028, 'gen-068': 219068},
        retail_assets=retail)
    assert set(receipt['receipts']) == {'gen-079', 'gen-028', 'gen-068'}
    actors = (run / ground.ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219079: 'Sokkuri', 219028: 'ElecBug',
                                     219068: 'TamagoMushi'}
    bank = (run / ground.BANK_TXT).read_text(encoding='ascii')
    blocks = _parse_bank(bank)
    assert set(blocks) == {'Sokkuri', 'ElecBug', 'TamagoMushi'}
    assert bank.index('species ElecBug 28') < bank.index('species TamagoMushi 68')
    assert bank.index('species TamagoMushi 68') < bank.index('species Sokkuri 79')
    room_files = sorted(p.name for p in (run / ROOM).glob('*.mod'))
    assert any(name.startswith('ginv_Sokkuri_') for name in room_files)
    assert any(name.startswith('ginv_ElecBug_') for name in room_files)
    assert any(name.startswith('ginv_TamagoMushi_') for name in room_files)
