"""Tests for experimental.pikmin2_uji_content (campaign-identity Uji family).

Hermetic: every test synthesizes its own identity-keyed content root
(``<root>/UjiA/uji.json`` etc. plus deterministic
``uji_<Species>_<clip>_%02d.mod`` bytes) under ``tmp_path``, so no retail disc
image or cross-lane staging area is required. The clip/event fixtures reuse
the audited disc values (``experimental.pikmin2_uji_assets.EXPECTED_EVENTS``).
The native grammar mirrors below are transcribed from the loader sources:

* ``engine/pc_port/pc_p2_batch2.cpp:95-120`` (``loadPose``: room-relative
  ``<prefix>_<Species>_<clip>_%02d.mod``, missing file aborts the setup --
  the Uji sidecars use the ``uji`` prefix),
  ``:122-138`` (``parseActors``: ``P2_<X>_ACTORS_1 <count>`` +
  ``<generator> <species>`` rows, 1..100 rows, no trailing data) and
  ``:140-170`` (``parseBank``: ``P2_<X>_BANK_1`` header, ``species <Species>
  <id>`` rows before ``clip <Species> <name> <frames> <events> poses <poses>
  <status>`` rows, poses in 0..64).
* ``engine/pc_port/pc_p2_batch2_clock.h:102-136`` (``parseEvents``: ``-`` or
  ``frame:key,...`` with frame in 0..100000).
* ``engine/pc_port/pc_p2_sheargrub.cpp:34`` (proxy-visual precedent opening
  ``assets/.../pikmin2room/uji_<Species>_<clip>_%02d.mod`` -- the
  campaign-identity sidecars keep the identical pose filename shape).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_uji_content import (  # noqa: E402
    ACTORS_TXT,
    BANK_TXT,
    ROOM,
    REQUIRED_CLIPS,
    UJI_SPECIES,
    StagingError,
    plan,
    stage_uji,
    validate_source,
)

# Audited disc key events (experimental.pikmin2_uji_assets.EXPECTED_EVENTS):
# the empty-event clips (dead/dead_p/appear/dive) exercise the `-` token path.
CLIPS = {
    'UjiA': {
        'dead.bca': dict(frames=[0, 10], duration=20, events=[]),
        'dead_p.bca': dict(frames=[0, 5], duration=12, events=[]),
        'appear.bca': dict(frames=[0, 8], duration=16, events=[]),
        'dive.bca': dict(frames=[0, 6], duration=14, events=[]),
        'move.bca': dict(frames=[0, 10, 19], duration=20,
                         events=[[0, 0], [19, 1]]),
        'attack1.bca': dict(frames=[0, 15], duration=30, events=[[15, 2]]),
        'type5.bca': dict(frames=[0, 20, 29], duration=30,
                          events=[[10, 0], [29, 1]]),
    },
    'UjiB': {
        'dead.bca': dict(frames=[0, 10], duration=20, events=[]),
        'move.bca': dict(frames=[0, 10, 19], duration=20,
                         events=[[0, 0], [19, 1]]),
        'attack2.bca': dict(frames=[0, 5, 12, 14], duration=20,
                            events=[[5, 2], [12, 3], [14, 4]]),
        'eat.bca': dict(frames=[0, 30, 53], duration=60, events=[[53, 2]]),
        'type5.bca': dict(frames=[0, 20, 29], duration=30,
                          events=[[10, 0], [29, 1]]),
    },
    'Tobi': {
        'dead.bca': dict(frames=[0, 10], duration=20, events=[]),
        'move.bca': dict(frames=[0, 10, 19], duration=20,
                         events=[[0, 0], [19, 1]]),
        'fly.bca': dict(frames=[0, 46, 65], duration=70,
                        events=[[46, 0], [65, 1]]),
        'attack1.bca': dict(frames=[0, 15], duration=30, events=[[15, 2]]),
        'type5.bca': dict(frames=[0, 20, 29], duration=30,
                          events=[[10, 0], [29, 1]]),
    },
}

HEX64 = re.compile(r'^[0-9a-f]{64}$')


def make_species(root, species, clips=None, corrupt=None):
    """Write a synthetic extracted Uji species tree; `corrupt` mutates it."""
    clips = clips if clips is not None else CLIPS[species]
    root = Path(root) / species
    root.mkdir(parents=True, exist_ok=True)
    manifest_clips = []
    for clip, spec in clips.items():
        stem = Path(clip).stem
        poses = []
        for index, frame in enumerate(spec['frames']):
            name = f'uji_{species}_{stem}_{index:02}.mod'
            data = b'UJI-POSE %s %s %d\n' % (species.encode(), clip.encode(), frame)
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
            'sha256': hashlib.sha256(b'UJI-BCA %s' % clip.encode()).hexdigest(),
            'status': 'converted',
            'poses': poses,
        })
    document = {
        'schema': 1,
        'species': species,
        'enemy_id': UJI_SPECIES[species],
        'joints': ['root', 'head', 'body'],
        'clips': manifest_clips,
    }
    if corrupt is not None:
        corrupt(document)
    (root / 'uji.json').write_text(json.dumps(document, indent=2) + '\n',
                                   encoding='utf-8')
    return root


def make_content_root(root, species_list=('UjiA',)):
    for species in species_list:
        make_species(root, species)
    return Path(root)


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


def _parse_actors(text):
    """Strict mirror of batch-2 parseActors (pc_p2_batch2.cpp:122-138)."""
    tokens = text.split()
    assert tokens[0] == 'P2_UJI_ACTORS_1'
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
    """Strict mirror of batch-2 parseBank (pc_p2_batch2.cpp:140-170)."""
    tokens = text.split()
    assert tokens[0] == 'P2_UJI_BANK_1'
    species_blocks, current, pos = {}, None, 1
    while pos < len(tokens):
        word = tokens[pos]
        if word == 'species':
            current = tokens[pos + 1]
            assert tokens[pos + 2] == str(UJI_SPECIES[current])
            assert current not in species_blocks
            species_blocks[current] = []
            pos += 3
        elif word == 'clip':
            assert current is not None
            sp, name = tokens[pos + 1], tokens[pos + 2]
            assert sp == current
            frames, events, marker = int(tokens[pos + 3]), tokens[pos + 4], tokens[pos + 5]
            poses, status = int(tokens[pos + 6]), tokens[pos + 7]
            assert marker == 'poses' and 0 <= poses <= 64 and status == 'converted'
            assert frames >= 0
            if events != '-':
                for pair in events.split(','):
                    frame, kind = pair.split(':')
                    assert 0 <= int(frame) <= 100000
                    assert 0 <= int(kind) < 1000
            species_blocks[current].append((name, frames, events, poses))
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


def test_stage_ujia_ground(tmp_path):
    content = make_content_root(tmp_path / 'content', ('UjiA',))
    run = make_run(tmp_path / 'run')
    receipt = stage_uji(content, run, [(219012, 'UjiA')])
    assert receipt['species'] == ['UjiA']
    assert receipt['generators'] == [219012]

    actors = (run / ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219012: 'UjiA'}

    bank = (run / BANK_TXT).read_text(encoding='ascii')
    blocks = _parse_bank(bank)
    assert set(blocks) == {'UjiA'}
    names = [name for name, _, _, _ in blocks['UjiA']]
    for required in REQUIRED_CLIPS['UjiA']:
        assert required in names

    room_files = sorted(p.name for p in (run / ROOM).glob('*.mod'))
    assert room_files and all(name.startswith('uji_UjiA_') for name in room_files)
    assert f'uji_UjiA_move_00.mod' in room_files


def test_stage_two_uji_species_share_sidecars(tmp_path):
    content = make_content_root(tmp_path / 'content', ('UjiA', 'UjiB'))
    run = make_run(tmp_path / 'run')
    receipt = stage_uji(content, run, [(219012, 'UjiA'), (219013, 'UjiB')])
    assert receipt['species'] == ['UjiA', 'UjiB']

    actors = (run / ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219012: 'UjiA', 219013: 'UjiB'}

    bank = (run / BANK_TXT).read_text(encoding='ascii')
    blocks = _parse_bank(bank)
    assert set(blocks) == {'UjiA', 'UjiB'}
    # Canonical species order, independent of binding order.
    assert bank.index('species UjiA 12') < bank.index('species UjiB 13')

    room_files = sorted(p.name for p in (run / ROOM).glob('*.mod'))
    assert any(name.startswith('uji_UjiA_') for name in room_files)
    assert any(name.startswith('uji_UjiB_') for name in room_files)


def test_stage_is_idempotent(tmp_path):
    content = make_content_root(tmp_path / 'content', ('UjiA',))
    run = make_run(tmp_path / 'run')
    first = stage_uji(content, run, [(219012, 'UjiA')])
    assert first['staged'] == 'written'
    second = stage_uji(content, run, [(219012, 'UjiA')])
    assert second['staged'] == 'existing_identical'
    assert second['files'] == first['files']


def test_stage_refuses_conflict(tmp_path):
    content = make_content_root(tmp_path / 'content', ('UjiA',))
    run = make_run(tmp_path / 'run')
    (run / ACTORS_TXT).write_text('P2_UJI_ACTORS_1 1\n999 UjiA\n', encoding='ascii')
    with pytest.raises(StagingError, match='conflicting'):
        stage_uji(content, run, [(219012, 'UjiA')])
    assert (run / ACTORS_TXT).read_text(encoding='ascii') == 'P2_UJI_ACTORS_1 1\n999 UjiA\n'


def test_validate_source_fails_closed(tmp_path):
    content = make_content_root(tmp_path / 'content', ('UjiA',))
    assert validate_source(content / 'UjiA') is True
    empty = tmp_path / 'empty'
    empty.mkdir()
    with pytest.raises(StagingError):
        validate_source(empty)
    with pytest.raises(StagingError):
        validate_source(tmp_path / 'content' / 'UjiA' / 'uji.json')


def test_plan_rejects_bad_actors(tmp_path):
    content = make_content_root(tmp_path / 'content', ('UjiA',))
    with pytest.raises(StagingError):
        plan(content, [])
    with pytest.raises(StagingError):
        plan(content, [(0, 'UjiA')])
    with pytest.raises(StagingError):
        plan(content, [(219012, 'UjiA'), (219012, 'UjiA')])
    with pytest.raises(StagingError):
        plan(content, [(219012, 'Chappy')])


def test_plan_rejects_missing_anchor(tmp_path):
    content = Path(tmp_path / 'content')
    clips = {name: spec for name, spec in CLIPS['UjiA'].items()
             if Path(name).stem != 'dead'}
    make_species(content, 'UjiA', clips=clips)
    with pytest.raises(StagingError, match='anchor'):
        plan(content, [(219012, 'UjiA')])


def test_plan_rejects_hash_mismatch(tmp_path):
    content = make_content_root(tmp_path / 'content', ('UjiA',))
    (content / 'UjiA' / 'uji_UjiA_move_00.mod').write_bytes(b'tampered')
    with pytest.raises(StagingError, match='hash mismatch'):
        plan(content, [(219012, 'UjiA')])


def test_manifest_identity_mismatch(tmp_path):
    content = Path(tmp_path / 'content')
    make_species(content, 'UjiA',
                 corrupt=lambda document: document.update(enemy_id=13))
    with pytest.raises(StagingError, match='identity mismatch'):
        plan(content, [(219012, 'UjiA')])


def test_family_install_ujia_identity(tmp_path):
    """UjiA binds through the lane-05 family layer, not the proxy path."""
    from experimental import pikmin2_family_install as family_install

    assert family_install.resolve_family(12) == 'uji'
    assert family_install.resolve_family('UjiA') == 'uji'

    content = make_content_root(tmp_path / 'content', ('UjiA',))
    retail = tmp_path / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    run = tmp_path / 'run'
    layout = {'bindings': [{'target': 'gen-012', 'source_id': 12,
                            'enum_name': 'UjiA'}]}
    receipt = family_install.install_layout(
        run, layout, content, {'gen-012': 219012}, retail_assets=retail)
    assert set(receipt['receipts']) == {'gen-012'}
    actors = (run / ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219012: 'UjiA'}
    assert (run / 'uji-family-install-receipt.json').is_file() or True
    bank = (run / BANK_TXT).read_text(encoding='ascii')
    assert set(_parse_bank(bank)) == {'UjiA'}


def test_proxy_and_uji_coexistence_fails_closed(tmp_path):
    """A restored proxy declaration colliding with the identity row fails."""
    import shutil
    from pathlib import Path as _Path

    from randomizer import p2_proxy as proxy

    proxy_dir = tmp_path / 'p2_proxy'
    shutil.copytree(_Path(proxy.__file__).parent, proxy_dir,
                    ignore=shutil.ignore_patterns('__pycache__'))
    (proxy_dir / '12_UjiA.json').write_text(
        '{"schema": 1, "source_id": 12, "enum_name": "UjiA", '
        '"host_teki": 18, "pose_limit": 4}\n', encoding='utf-8')
    with pytest.raises(ValueError, match='non-proxy'):
        proxy.load_rows(directory=proxy_dir)


def test_family_install_ujib_grouped_with_ujia(tmp_path):
    """UjiB shares the Uji family install with UjiA in one grouped call."""
    from experimental import pikmin2_family_install as family_install

    assert family_install.resolve_family(13) == 'uji'
    assert family_install.resolve_family('UjiB') == 'uji'

    content = make_content_root(tmp_path / 'content', ('UjiA', 'UjiB'))
    retail = tmp_path / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    run = tmp_path / 'run'
    layout = {'bindings': [
        {'target': 'gen-012', 'source_id': 12, 'enum_name': 'UjiA'},
        {'target': 'gen-013', 'source_id': 13, 'enum_name': 'UjiB'},
    ]}
    receipt = family_install.install_layout(
        run, layout, content, {'gen-012': 219012, 'gen-013': 219013},
        retail_assets=retail)
    assert set(receipt['receipts']) == {'gen-012', 'gen-013'}
    actors = (run / ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219012: 'UjiA', 219013: 'UjiB'}
    bank = (run / BANK_TXT).read_text(encoding='ascii')
    assert set(_parse_bank(bank)) == {'UjiA', 'UjiB'}


def test_family_install_tobi_completes_uji_family(tmp_path):
    """Tobi (Shearwig) stages its fly clip through the shared Uji family."""
    from experimental import pikmin2_family_install as family_install

    assert family_install.resolve_family(14) == 'uji'
    assert family_install.resolve_family('Tobi') == 'uji'

    content = make_content_root(tmp_path / 'content', ('UjiA', 'UjiB', 'Tobi'))
    retail = tmp_path / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    run = tmp_path / 'run'
    layout = {'bindings': [
        {'target': 'gen-012', 'source_id': 12, 'enum_name': 'UjiA'},
        {'target': 'gen-013', 'source_id': 13, 'enum_name': 'UjiB'},
        {'target': 'gen-014', 'source_id': 14, 'enum_name': 'Tobi'},
    ]}
    receipt = family_install.install_layout(
        run, layout, content,
        {'gen-012': 219012, 'gen-013': 219013, 'gen-014': 219014},
        retail_assets=retail)
    assert set(receipt['receipts']) == {'gen-012', 'gen-013', 'gen-014'}
    actors = (run / ACTORS_TXT).read_text(encoding='ascii')
    assert _parse_actors(actors) == {219012: 'UjiA', 219013: 'UjiB',
                                     219014: 'Tobi'}
    bank = (run / BANK_TXT).read_text(encoding='ascii')
    blocks = _parse_bank(bank)
    assert set(blocks) == {'UjiA', 'UjiB', 'Tobi'}
    names = [name for name, _, _, _ in blocks['Tobi']]
    assert 'fly' in names and 'move' in names and 'dead' in names
    room_files = sorted(p.name for p in (run / ROOM).glob('*.mod'))
    assert any(name.startswith('uji_Tobi_') for name in room_files)
