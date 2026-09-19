"""Muse packaging lane (#493): candidate-only staging for 41/57/58/78.

Uses synthetic identity sources and a synthetic retail-free run: no retail
assets are read. Proves the candidate-only generated-session path stages
hash-verified sidecars for Fuefuki/Kurage/MiniHoudai, delegates BombSarai to
the family installer as-is, and fails closed on missing/wrong identity, cache
replay and generator-binding disagreement.
"""
import json
import shutil

import pytest

from experimental import pikmin2_family_install as family
from experimental import pikmin2_muse_packaging as packaging
from experimental.pikmin2_staging import StagingError


BOMBSARAI_MANIFEST = {
    'schema': 1,
    'policy': 'P2_BOMBSARAI_IMPORT_1',
    'disc_id': 'GPVE01',
    'disc_revision': 0,
    'source_revision': '632af93787b9c95b63f0c13be32b161375ce3a96',
    'payload': {'enemy': 'Bomb', 'enemy_id': 36, 'child_num': 2},
    'species': {
        'BombSarai': {
            'enemy_id': 58,
            'role': 'carrier',
            'parameter_blocks': [{}, {'speed': 1}, {'hp': 2}],
            'clips': [
                {'name': name, 'source_frames': 2, 'status': 'converted',
                 'poses': [{'frame': 0}]}
                for name in ('wait1', 'wait2', 'release1', 'dead1')
            ],
        }
    },
}

LAYOUT_ALL_FOUR = {'bindings': [
    {'target': 'slot-fuefuki', 'source_id': 41, 'enum_name': 'Fuefuki'},
    {'target': 'slot-kurage', 'source_id': 57, 'enum_name': 'Kurage'},
    {'target': 'slot-bombsarai', 'source_id': 58, 'enum_name': 'BombSarai'},
    {'target': 'slot-minihoudai', 'source_id': 78, 'enum_name': 'MiniHoudai'},
]}
ACTORS_ALL_FOUR = {'slot-fuefuki': 41001, 'slot-kurage': 57001,
                   'slot-bombsarai': 58001, 'slot-minihoudai': 78001}


def seed_content(root):
    content = root / 'content'
    for source_id, enum_name in packaging.CANDIDATES.items():
        ident = content / enum_name
        ident.mkdir(parents=True)
        if source_id == 58:
            (ident / 'bombsarai.json').write_text(json.dumps(BOMBSARAI_MANIFEST))
        else:
            (ident / 'identity.json').write_text(json.dumps(
                {'schema': 1, 'source_id': source_id, 'enum_name': enum_name}))
    return content


def prepare_room(run):
    room = run / 'assets' / 'dataDir' / 'courses' / 'pikmin2room'
    room.mkdir(parents=True)
    return room


def make_retail(root):
    retail = root / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    (retail / 'dataDir' / 'stages' / 'base.bin').write_bytes(b'retail')
    return retail


def test_candidate_identities_resolve_through_family_binding():
    assert family.resolve_family(58) == 'bombsarai'
    assert family.resolve_family('BombSarai') == 'bombsarai'
    # #442 adds family bindings for Kurage (57) and MiniHoudai (78) alongside
    # the unchanged candidate sidecar path; only Fuefuki (41) stays out.
    assert family.resolve_family(57) == 'kurage'
    assert family.resolve_family('Kurage') == 'kurage'
    assert family.resolve_family(78) == 'minihoudai'
    assert family.resolve_family('MiniHoudai') == 'minihoudai'
    for identity in (41, 'Fuefuki'):
        with pytest.raises(ValueError):
            family.resolve_family(identity)


def test_stage_all_four_candidates(tmp_path):
    content = seed_content(tmp_path)
    retail = make_retail(tmp_path)
    run = tmp_path / 'run'
    receipt = packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content,
                                         ACTORS_ALL_FOUR, retail_assets=retail)
    assert receipt['candidate_only'] is True and receipt['admission'] == 'none'
    assert set(receipt['sidecars']) == {'Fuefuki', 'Kurage', 'MiniHoudai'}
    assert receipt['family_receipt']['receipts']['slot-bombsarai']['enemy_id'] == 58
    assert (run / 'p2-bombsarai-actors.txt').is_file()
    assert (run / packaging.actors_filename('Fuefuki')).is_file()
    assert packaging.verify_staging(run, LAYOUT_ALL_FOUR, ACTORS_ALL_FOUR)['verified']


def test_missing_identity_source_fails_closed(tmp_path):
    content = seed_content(tmp_path)
    shutil.rmtree(content / 'Kurage')
    run = tmp_path / 'run'
    prepare_room(run)
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content, ACTORS_ALL_FOUR)
    assert not (run / packaging.RECEIPT).exists()


def test_wrong_identity_source_fails_closed(tmp_path):
    content = seed_content(tmp_path)
    (content / 'Kurage' / 'identity.json').write_text(json.dumps(
        {'schema': 1, 'source_id': 999, 'enum_name': 'Kurage'}))
    run = tmp_path / 'run'
    prepare_room(run)
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content, ACTORS_ALL_FOUR)


def test_generator_binding_disagreement_fails_closed(tmp_path):
    content = seed_content(tmp_path)
    run = tmp_path / 'run'
    prepare_room(run)
    layout = {'bindings': [
        {'target': 'slot-x', 'source_id': 41, 'enum_name': 'Kurage'},
    ]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, layout, content, {'slot-x': 41001})


def test_missing_actor_binding_fails_closed(tmp_path):
    content = seed_content(tmp_path)
    run = tmp_path / 'run'
    prepare_room(run)
    actors = dict(ACTORS_ALL_FOUR)
    del actors['slot-kurage']
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content, actors)


def test_duplicate_generator_fails_closed(tmp_path):
    content = seed_content(tmp_path)
    run = tmp_path / 'run'
    prepare_room(run)
    actors = dict(ACTORS_ALL_FOUR)
    actors['slot-kurage'] = actors['slot-fuefuki']
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content, actors)


def test_non_candidate_binding_rejected(tmp_path):
    content = seed_content(tmp_path)
    run = tmp_path / 'run'
    prepare_room(run)
    layout = {'bindings': [
        {'target': 'slot-dwarf', 'source_id': 44, 'enum_name': 'BlueKochappy'},
    ]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, layout, content, {'slot-dwarf': 44001})


def test_cache_replay_without_sources(tmp_path):
    content = seed_content(tmp_path)
    retail = make_retail(tmp_path)
    run = tmp_path / 'run'
    cache = tmp_path / 'cache'
    first = packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content,
                                       ACTORS_ALL_FOUR, retail_assets=retail,
                                       cache_dir=cache)
    assert first.get('cached') is not True
    shutil.rmtree(run)
    shutil.rmtree(content)
    second = packaging.stage_candidates(tmp_path / 'run', LAYOUT_ALL_FOUR,
                                        tmp_path / 'gone', ACTORS_ALL_FOUR,
                                        retail_assets=retail, cache_dir=cache)
    assert second.get('cached') is True
    assert second['plan_digest'] == first['plan_digest']
    assert packaging.verify_staging(tmp_path / 'run', LAYOUT_ALL_FOUR,
                                    ACTORS_ALL_FOUR)['verified']


def test_receipt_replay_without_cache(tmp_path):
    content = seed_content(tmp_path)
    retail = make_retail(tmp_path)
    run = tmp_path / 'run'
    first = packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content,
                                       ACTORS_ALL_FOUR, retail_assets=retail)
    shutil.rmtree(content)
    second = packaging.stage_candidates(run, LAYOUT_ALL_FOUR, tmp_path / 'gone',
                                        ACTORS_ALL_FOUR)
    assert second.get('cached') is True
    assert second['plan_digest'] == first['plan_digest']


def test_conflicting_receipt_refused(tmp_path):
    content = seed_content(tmp_path)
    retail = make_retail(tmp_path)
    run = tmp_path / 'run'
    packaging.stage_candidates(run, LAYOUT_ALL_FOUR, content, ACTORS_ALL_FOUR,
                               retail_assets=retail)
    other = {'bindings': [LAYOUT_ALL_FOUR['bindings'][0]]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, other, content, {'slot-fuefuki': 41001})


def test_candidate_command_entrypoint(tmp_path, capsys):
    content = seed_content(tmp_path)
    retail = make_retail(tmp_path)
    run = tmp_path / 'run'
    layout_path = tmp_path / 'layout.json'
    layout_path.write_text(json.dumps(LAYOUT_ALL_FOUR))
    actors_path = tmp_path / 'actors.json'
    actors_path.write_text(json.dumps(ACTORS_ALL_FOUR))
    code = packaging.main(['--run', str(run), '--layout', str(layout_path),
                           '--content-root', str(content),
                           '--actor-bindings', str(actors_path),
                           '--retail', str(retail)])
    assert code == 0
    assert json.loads(capsys.readouterr().out)['candidate_only'] is True
