"""Batch-2 install + arena tests for the remaining P2 enemy families (#346, #349, #350, #352, #353).

Parameterized over :data:`experimental.pikmin2_batch2_families.FAMILIES`, using
synthetic schema-1 manifests with real bytes and recorded SHA-256 hashes. Covers
installed artifacts (not just generated output) and the arena translation
contract. Real-disc round-trips are recorded separately under private output.
"""
import json
import struct
from pathlib import Path
from unittest.mock import patch

import pytest

import experimental.pikmin2_batch2_core as core
from experimental.pikmin2_batch2_core import P1_CHAPPY_TYPE, sha
from experimental.pikmin2_batch2_families import FAMILIES

CONFIGS = list(FAMILIES.values())
IDS = sorted({cfg['name']: cfg for cfg in CONFIGS})
BY_NAME = {cfg['name']: cfg for cfg in CONFIGS}


def fake_imported(root, cfg, omit_poses=False, tamper=False):
    """Synthetic schema-1 manifest: real pose bytes, recorded hashes."""
    root.mkdir(parents=True)
    species = {}
    for name, identity in cfg['species'].items():
        (root / name).mkdir()
        clips = []
        for clip in cfg['anchors'].get(name, ()):
            pose = f'{cfg["name"]}_{name}_{clip}_00.mod'
            data = f'{name}:{clip}:pose'.encode()
            if not omit_poses:
                (root / name / pose).write_bytes(data)
            clips.append(dict(name=clip, status='converted', events=[],
                              source_frames=10,
                              poses=[dict(file=pose, frame=0, bytes=len(data),
                                          sha256=sha(data))]))
        species[name] = dict(enemy_id=identity, role='synthetic',
                             parameter_blocks=[{}, {'fp00': 200.0}, {'fp01': 2.0}],
                             proper_retail={'fp01': 2.0}, clips=clips)
    manifest = dict(schema=1, policy=cfg['policy'], disc_id='GPVE01', disc_revision=0,
                    species=species)
    (root / cfg['manifest']).write_text(json.dumps(manifest))
    if tamper:
        first = cfg['actors'][0]
        clip = cfg['anchors'][first][0]
        (root / first / f'{cfg["name"]}_{first}_{clip}_00.mod').write_bytes(b'TAMPERED')
    return root


def fake_run(tmp_path):
    run = tmp_path / 'run'
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    return run


def actor_list(cfg, count=None):
    species = cfg['actors'] if count is None else cfg['actors'][:count]
    return [(1000 + index, name) for index, name in enumerate(species)]


def entry(kind=b'iket', identity=1):
    record = bytearray(100)
    record[:8] = b'    0.0v'
    struct.pack_into('<I', record, 8, identity)
    record[72:76] = kind
    return bytes(record)


def staged(tmp_path, cfg, existing=None, template=None):
    source = tmp_path / 'dataDir/stages/practice/default.gen'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'1.0v' + struct.pack('>4fI', 47, 30, 1919, 180, 1))
    with patch.object(core, 'records', return_value=existing or [entry(b'goal')]), \
            patch.object(core, 'generator', return_value=b'x' * 24 + (template or entry())):
        return core.roster(cfg, tmp_path)


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_actor_count_rejected_before_io(tmp_path, cfg):
    for actors in ([], [(i, cfg['actors'][0]) for i in range(101)]):
        with pytest.raises(ValueError):
            core.plan(cfg, Path('missing'), actors)


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_duplicate_and_invalid_ids_rejected(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    first = cfg['actors'][0]
    with pytest.raises(ValueError):
        core.plan(cfg, imported, [(5, first), (5, first)])
    for bad in [(-1, first), ('5', first), (True, first), (1, 'NotASpecies')]:
        with pytest.raises(ValueError):
            core.plan(cfg, imported, [bad])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_schema_and_identity_rejected(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    meta = json.loads((imported / cfg['manifest']).read_text())
    first = cfg['actors'][0]
    for key, value in (('schema', 2), ('policy', 'P2_OTHER_1'),
                       ('disc_id', 'GPVJ01'), ('disc_revision', 1)):
        broken = dict(meta, **{key: value})
        (imported / cfg['manifest']).write_text(json.dumps(broken))
        with pytest.raises(ValueError):
            core.plan(cfg, imported, [(1, first)])
        (imported / cfg['manifest']).write_text(json.dumps(meta))
    broken = json.loads(json.dumps(meta))
    broken['species'][first]['enemy_id'] = 999
    (imported / cfg['manifest']).write_text(json.dumps(broken))
    with pytest.raises(ValueError, match='species/ID'):
        core.plan(cfg, imported, [(1, first)])
    broken = json.loads(json.dumps(meta))
    broken['species'].pop(cfg['actors'][-1])
    (imported / cfg['manifest']).write_text(json.dumps(broken))
    with pytest.raises(ValueError):
        core.plan(cfg, imported, [(1, first)])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_missing_anchor_rejected(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    first = cfg['actors'][0]
    anchor = cfg['anchors'][first][0]
    meta = json.loads((imported / cfg['manifest']).read_text())
    meta['species'][first]['clips'] = [
        clip for clip in meta['species'][first]['clips'] if clip['name'] != anchor]
    (imported / cfg['manifest']).write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='anchor'):
        core.plan(cfg, imported, [(1, first)])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_pose_hash_mismatch_rejected(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg, tamper=True)
    with pytest.raises(ValueError, match='hash mismatch'):
        core.plan(cfg, imported, [(1, cfg['actors'][0])])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_install_and_verify_roundtrip(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    run = fake_run(tmp_path)
    actors = actor_list(cfg, 2)
    receipt = core.install(cfg, imported, run, actors)
    assert receipt['visuals'] == 'installed'
    assert receipt['file_sha256']
    for name, value in receipt['file_sha256'].items():
        installed = (run / 'assets/dataDir/courses/pikmin2room' / name).read_bytes()
        assert sha(installed) == value
    verified = core.verify_install(cfg, imported, run, actors)
    assert verified['verified'] == sorted(receipt['file_sha256'])
    config = (run / cfg['actors_txt']).read_text().split()
    assert config[:4] == [cfg['actors_header'], '2', str(actors[0][0]), actors[0][1]]
    assert config[0] == cfg['actors_header']


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_install_refuses_overwrite(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    run = fake_run(tmp_path)
    core.install(cfg, imported, run, [(1, cfg['actors'][0])])
    with pytest.raises(ValueError, match='Refusing existing'):
        core.install(cfg, imported, run, [(2, cfg['actors'][0])])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_verify_detects_tampered_pose(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    run = fake_run(tmp_path)
    first = cfg['actors'][0]
    core.install(cfg, imported, run, [(1, first)])
    name = f'{cfg["name"]}_{first}_{cfg["anchors"][first][0]}_00.mod'
    (run / 'assets/dataDir/courses/pikmin2room' / name).write_bytes(b'X')
    with pytest.raises(ValueError, match='visual mismatch'):
        core.verify_install(cfg, imported, run, [(1, first)])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_verify_detects_config_tamper(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    run = fake_run(tmp_path)
    first = cfg['actors'][0]
    core.install(cfg, imported, run, [(1, first)])
    (run / cfg['actors_txt']).write_text(f'{cfg["actors_header"]}\n1\n999 Nope\n')
    with pytest.raises(ValueError, match='actor config mismatch'):
        core.verify_install(cfg, imported, run, [(1, first)])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_absent_visual_bank_preserves_baseline(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg, omit_poses=True)
    run = fake_run(tmp_path)
    receipt = core.install(cfg, imported, run, [(1, cfg['actors'][0])])
    assert receipt['visuals'] == 'absent_baseline_preserved'
    assert receipt['file_sha256'] == {}
    assert not list((run / 'assets/dataDir/courses/pikmin2room').iterdir())


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_partial_visual_bank_refused(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    first = cfg['actors'][0]
    anchor = cfg['anchors'][first][0]
    (imported / first / f'{cfg["name"]}_{first}_{anchor}_00.mod').unlink()
    with pytest.raises(ValueError, match='Incomplete'):
        core.plan(cfg, imported, [(1, first)])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_sibling_generator_overlap_refused(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    run = fake_run(tmp_path)
    (run / 'p2-dwarf-bear-actors.txt').write_text('P2_DWARF_BEAR_ACTORS_1 1\n1000\n')
    with pytest.raises(ValueError, match='overlap'):
        core.install(cfg, imported, run, [(1000, cfg['actors'][0])])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_non_junction_room_required(tmp_path, cfg):
    imported = fake_imported(tmp_path / 'imported', cfg)
    run = tmp_path / 'run'
    run.mkdir()
    with pytest.raises(ValueError, match='non-junction'):
        core.install(cfg, imported, run, [(1, cfg['actors'][0])])


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_roster_requires_real_stage_records(cfg):
    with pytest.raises(Exception):
        core.roster(cfg, Path('missing'))


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_roster_translation_only(tmp_path, cfg):
    data, actors = staged(tmp_path, cfg)
    assert struct.unpack_from('>I', data, 20)[0] == 1 + len(cfg['arena_species'])
    assert [a['species'] for a in actors] == list(cfg['arena_species'])
    assert [a['generator'] for a in actors] == list(cfg['arena_ids'])
    assert [a['native_teki_type'] for a in actors] == [
        cfg['arena_proxy'][s] for s in cfg['arena_species']]
    assert [tuple(a['expected_xyz']) for a in actors] == [
        tuple(p) for p in cfg['arena_positions']]
    for actor in actors:
        assert actor['offset'] == [0, 0, 0]
        assert actor['source_yaw'] is None and actor['source_yaw_applied'] is False
        assert len(actor['expected_xyz']) == 3


@pytest.mark.parametrize('cfg', CONFIGS, ids=lambda cfg: cfg['name'])
def test_generator_id_collision_rejected(tmp_path, cfg):
    with pytest.raises(ValueError, match='collision'):
        staged(tmp_path, cfg, existing=[entry(identity=cfg['arena_ids'][1])])


def test_proxy_types_match_native_registry():
    # engine/include/teki.h: 17 Beatle (Armored Cannon Beetle), 2 Iwagon
    # (Rolling Boulder), 3 Chappy (Dwarf Bulborb).
    assert core.P1_CHAPPY_TYPE == 3
    cannon = BY_NAME['cannon']
    assert cannon['arena_proxy']['Kabuto'] == 17
    assert cannon['arena_proxy']['Rock'] == 2
    assert cannon['arena_proxy']['Bomb'] == 3


def test_gates_cover_batch1_open_items():
    assert 'native_identity' in BY_NAME['dweevil']['gates']
    assert 'otakara_shared_base' in BY_NAME['dweevil']['gates']
    assert 'candypop_shared_pom_base' in BY_NAME['flora']['gates']
    assert 'cannon_projectile_pool' in BY_NAME['cannon']['gates']
    assert 'tyre_roll_crush' in BY_NAME['waterwraith']['gates']
    assert 'sokkuri_disguise' in BY_NAME['ground']['gates']
    for cfg in CONFIGS:
        assert 'blocked' in cfg['blocked']['native_identity'].lower()


def test_disc_registry_ids_unchanged():
    assert BY_NAME['dweevil']['species'] == {
        'FireOtakara': 59, 'WaterOtakara': 60, 'GasOtakara': 61,
        'ElecOtakara': 62, 'BombOtakara': 93}
    assert BY_NAME['waterwraith']['species'] == {'Tyre': 98, 'BlackMan': 99}
    assert BY_NAME['flora']['species']['RandPom'] == 8
    assert BY_NAME['cannon']['species']['Kabuto'] == 75
    assert BY_NAME['ground']['species']['Armor'] == 15


def test_flora_stages_refreshed_pelplant_on_retail_vehicle():
    # #405/#397: Pelplant now converts (10/10) and is staged as the first flora
    # actor on the neutral Chappy vehicle. The arena id/provider sets grow with
    # it, and the receptor/reward behavior stays explicitly blocked.
    flora = BY_NAME['flora']
    assert flora['actors'][0] == 'Pelplant'
    assert flora['anchors']['Pelplant'] == (
        'wait1', 'wait2', 'wait3', 'grow1', 'grow2', 'damage3', 'dead3',
        'bgrow1', 'bdamage1', 'bdead1')
    assert flora['arena_ids'][0] == 353001
    assert len(flora['arena_ids']) == len(flora['arena_species'])
    assert flora['arena_positions'][-1] == (240.0, 30.0, 1500.0)
    assert flora['arena_proxy']['Pelplant'] == core.P1_CHAPPY_TYPE
    assert 'pelplant_receptor' in flora['blocked']
    assert '10/10' in flora['blocked']['pelplant_receptor']

