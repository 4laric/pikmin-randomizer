"""Kurage (source 57) visual staging: layout, idempotence and fail-closed.

Hermetic: builds a synthetic extracted ``<content>/Kurage/`` tree
(``identity.json`` + ``kurage.json`` + synthetic pose bytes) and stages it into
a run whose private room directory already exists. No ISO, no native build and
no runtime run are needed; the contract under test is the file layout the native
visual loader opens and the fail-closed staging behaviour.
"""
import hashlib
import json
from pathlib import Path

import pytest

from experimental.pikmin2_kurage_content import (
    ROOM, plan, stage_kurage_host, validate)
from experimental.pikmin2_staging import StagingError

REQUIRED = ('wait', 'attack')
OPTIONAL = ('move1', 'move2', 'type1', 'type2', 'flick1', 'flick2', 'dead1', 'dead2')
NATIVE_NAMES = REQUIRED + OPTIONAL


def _pose(name):
    return f'synthetic-kurage-{name}'.encode('ascii')


def make_kurage_source(root, names=NATIVE_NAMES):
    source = Path(root) / 'Kurage'
    source.mkdir(parents=True)
    (source / 'identity.json').write_text(
        json.dumps({'schema': 1, 'source_id': 57, 'enum_name': 'Kurage'}),
        encoding='utf-8')
    visuals = []
    for name in names:
        pose = f'{name}_0000.mod'
        data = _pose(name)
        (source / pose).write_bytes(data)
        visuals.append({'name': name, 'clip': f'{name}.bca', 'frame': 0,
                        'pose': pose, 'sha256': hashlib.sha256(data).hexdigest()})
    (source / 'kurage.json').write_text(
        json.dumps({'schema': 1, 'species': 'Kurage', 'enemy_id': 57,
                    'visuals': visuals}), encoding='utf-8')
    return source


def make_run(root):
    run = Path(root) / 'run'
    (run / ROOM).mkdir(parents=True)
    return run


def _rewrite_manifest(source, mutate):
    document = json.loads((source / 'kurage.json').read_text(encoding='utf-8'))
    mutate(document)
    (source / 'kurage.json').write_text(json.dumps(document), encoding='utf-8')


def test_stages_every_native_loader_file(tmp_path):
    source = make_kurage_source(tmp_path)
    run = make_run(tmp_path)
    receipt = stage_kurage_host(source, run)
    assert receipt['staged'] == 'written'
    assert (receipt['species'], receipt['source_id']) == ('Kurage', 57)
    room = run / ROOM
    for name in NATIVE_NAMES:
        staged = room / f'kurage_{name}.mod'
        assert staged.read_bytes() == _pose(name)
        key = str(ROOM / f'kurage_{name}.mod')
        assert receipt['files'][key] == hashlib.sha256(_pose(name)).hexdigest()
    assert sorted(p.name for p in room.glob('kurage_*.mod')) == sorted(
        f'kurage_{name}.mod' for name in NATIVE_NAMES)


def test_plan_is_pure_and_hash_bound(tmp_path):
    source = make_kurage_source(tmp_path)
    before = sorted(p.name for p in source.iterdir())
    files, digest = plan(source)
    assert set(files) == {str(ROOM / f'kurage_{name}.mod') for name in NATIVE_NAMES}
    assert digest == hashlib.sha256((source / 'kurage.json').read_bytes()).hexdigest()
    assert sorted(p.name for p in source.iterdir()) == before


def test_second_stage_is_identical_noop(tmp_path):
    source = make_kurage_source(tmp_path)
    run = make_run(tmp_path)
    first = stage_kurage_host(source, run)
    second = stage_kurage_host(source, run)
    assert second['staged'] == 'existing_identical'
    assert second['files'] == first['files']


def test_optional_pose_absent_is_staged_partial(tmp_path):
    # The loader treats the eight non-wait/attack shapes as optional, so an
    # extractor that could not bake one must still stage the required pair.
    source = make_kurage_source(tmp_path, names=REQUIRED + ('move1',))
    run = make_run(tmp_path)
    stage_kurage_host(source, run)
    room = run / ROOM
    assert (room / 'kurage_wait.mod').is_file()
    assert (room / 'kurage_attack.mod').is_file()
    assert not (room / 'kurage_flick1.mod').exists()


def test_conflicting_staged_file_refused(tmp_path):
    source = make_kurage_source(tmp_path)
    run = make_run(tmp_path)
    stage_kurage_host(source, run)
    (run / ROOM / 'kurage_wait.mod').write_bytes(b'tampered')
    with pytest.raises(StagingError):
        stage_kurage_host(source, run)


def test_missing_required_visual_refused(tmp_path):
    source = make_kurage_source(tmp_path, names=('move1',))
    run = make_run(tmp_path)
    with pytest.raises(StagingError):
        stage_kurage_host(source, run)


def test_missing_pose_mesh_refused(tmp_path):
    source = make_kurage_source(tmp_path)
    (source / 'attack_0000.mod').unlink()
    with pytest.raises(StagingError):
        validate(source)


def test_pose_hash_mismatch_refused(tmp_path):
    source = make_kurage_source(tmp_path)
    (source / 'wait_0000.mod').write_bytes(b'changed')
    with pytest.raises(StagingError):
        validate(source)


def test_unknown_visual_name_refused(tmp_path):
    source = make_kurage_source(tmp_path)
    _rewrite_manifest(source, lambda d: d['visuals'].append(
        {'name': 'wait2', 'clip': 'wait.bca', 'frame': 0, 'pose': 'wait_0000.mod',
         'sha256': hashlib.sha256(_pose('wait')).hexdigest()}))
    with pytest.raises(StagingError):
        validate(source)


def test_wrong_identity_refused(tmp_path):
    source = make_kurage_source(tmp_path)
    _rewrite_manifest(source, lambda d: d.update(enemy_id=72))
    with pytest.raises(StagingError):
        validate(source)


def test_missing_manifest_refused(tmp_path):
    source = make_kurage_source(tmp_path)
    (source / 'kurage.json').unlink()
    with pytest.raises(StagingError):
        validate(source)


def test_missing_room_directory_refused(tmp_path):
    source = make_kurage_source(tmp_path)
    run = Path(tmp_path) / 'run'
    run.mkdir()
    with pytest.raises(StagingError):
        stage_kurage_host(source, run)


def test_visual_names_match_native_loader_contract():
    # Pin the exact filename set engine/pc_port/pc_p2_kurage_visual.cpp:35-48
    # opens, so an extractor/stager drift cannot silently leave a shape unopened.
    from experimental import pikmin2_kurage_assets as assets
    native = {'wait', 'attack', 'move1', 'move2', 'type1', 'type2',
              'flick1', 'flick2', 'dead1', 'dead2'}
    assert {name for name, _clip, _frame in assets.VISUALS} == native
    assert set(REQUIRED) | set(OPTIONAL) == native
    assert {name for name, _clip, _frame in assets.REQUIRED_VISUALS} == set(REQUIRED)
    assert {name for name, _clip, _frame in assets.OPTIONAL_VISUALS} == set(OPTIONAL)
