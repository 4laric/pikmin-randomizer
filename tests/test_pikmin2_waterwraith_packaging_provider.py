"""Waterwraith packaging provider (#576): BlackMan99 + owned Tyre98 helper.

Uses synthetic identity sources and a synthetic retail-free run: no retail
assets are read. Proves hash-verified candidate-only staging for BlackMan99
(source/name agreement, fail-closed content), the owned-helper rule for
Tyre98 (same-target owner, never independent), immutable replay cache with
receipts, and the exact receipt/file contract consumer #572 consumes.
Existing four-candidate behavior is preserved untouched.
"""
import json
import shutil

import pytest

from experimental import pikmin2_muse_packaging as packaging
from experimental.pikmin2_staging import StagingError


LAYOUT_99 = {'bindings': [
    {'target': 'slot-waterwraith', 'source_id': 99, 'enum_name': 'BlackMan'},
]}
ACTORS_99 = {'slot-waterwraith': 99001}
LAYOUT_99_TYRE = {'bindings': [
    {'target': 'slot-waterwraith', 'source_id': 99, 'enum_name': 'BlackMan'},
    {'target': 'slot-waterwraith', 'source_id': 98, 'enum_name': 'Tyre'},
]}


def seed_waterwraith_content(root):
    content = root / 'content'
    blackman = content / 'BlackMan'
    blackman.mkdir(parents=True)
    (blackman / 'identity.json').write_text(json.dumps(
        {'schema': 1, 'source_id': 99, 'enum_name': 'BlackMan'}))
    tyre = content / 'Tyre'
    tyre.mkdir(parents=True)
    (tyre / 'identity.json').write_text(json.dumps(
        {'schema': 1, 'source_id': 98, 'enum_name': 'Tyre'}))
    return content


def test_four_candidate_maps_preserved():
    assert packaging.CANDIDATES[41] == 'Fuefuki'
    assert packaging.CANDIDATES[57] == 'Kurage'
    assert packaging.CANDIDATES[58] == 'BombSarai'
    assert packaging.CANDIDATES[78] == 'MiniHoudai'
    assert packaging.FULL_INSTALL_IDS == frozenset({58})


def test_blackman99_agreement_and_helper_rule():
    assert packaging._check_candidate_agreement('t', 99, 'BlackMan') == 99
    assert packaging._check_candidate_agreement('t', 99, 'blackman') == 99
    assert packaging._check_waterwraith_helper('t', 98, 'Tyre') == 99
    assert packaging._check_waterwraith_helper('t', 99, 'BlackMan') is None
    assert packaging._check_waterwraith_helper('t', 41, 'Fuefuki') is None
    with pytest.raises(StagingError):
        packaging._check_candidate_agreement('t', 99, 'Kurage')
    with pytest.raises(StagingError):
        packaging._check_candidate_agreement('t', 100, 'Whatever')
    with pytest.raises(StagingError):
        packaging._check_candidate_agreement('t', 98, 'Tyre')
    with pytest.raises(StagingError):
        packaging._check_waterwraith_helper('t', 98, 'BlackMan')


def test_stage_blackman99_only(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    receipt = packaging.stage_candidates(run, LAYOUT_99, content, ACTORS_99)
    assert receipt['candidate_only'] is True and receipt['admission'] == 'none'
    assert set(receipt['sidecars']) == {'BlackMan'}
    assert receipt['sidecars']['BlackMan']['generators'] == [99001]
    assert 'helpers' not in receipt
    assert (run / packaging.actors_filename('BlackMan')).is_file()
    assert (run / packaging.identity_filename('BlackMan')).is_file()
    assert packaging.verify_staging(run, LAYOUT_99, ACTORS_99)['verified']


def test_stage_blackman99_with_owned_tyre98(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    receipt = packaging.stage_candidates(run, LAYOUT_99_TYRE, content, ACTORS_99)
    assert set(receipt['sidecars']) == {'BlackMan'}
    helper = receipt['helpers']['Tyre']
    assert helper['owner_source_id'] == 99
    assert helper['owner_targets'] == ['slot-waterwraith']
    assert helper['generators'] == [99001]
    assert receipt['slot_acceptance'] == packaging.SLOT_ACCEPTANCE_PENDING
    assert (run / packaging.actors_filename('Tyre')).is_file()
    assert (run / packaging.identity_filename('Tyre')).is_file()
    assert packaging.verify_staging(run, LAYOUT_99_TYRE, ACTORS_99)['verified']


def test_consumer_572_contract_shape(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    receipt = packaging.stage_candidates(run, LAYOUT_99_TYRE, content, ACTORS_99)
    blackman = receipt['sidecars']['BlackMan']
    tokens = (run / blackman['actors_file']).read_text(encoding='ascii').split()
    assert tokens[0] == 'P2_MUSE_BLACKMAN_ACTORS_1'
    assert tokens[1] == '1' and tokens[2] == '99001' and tokens[3] == 'BlackMan'
    helper = receipt['helpers']['Tyre']
    tokens = (run / helper['actors_file']).read_text(encoding='ascii').split()
    assert tokens[0] == 'P2_MUSE_TYRE_ACTORS_1'
    assert tokens[2] == '99001' and tokens[3] == 'Tyre'
    for key in ('generators', 'actors_file', 'actors_sha256',
                'identity_file', 'identity_sha256'):
        assert blackman[key] and helper[key]


def test_tyre98_never_independent(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    lonely = {'bindings': [
        {'target': 'slot-tyre', 'source_id': 98, 'enum_name': 'Tyre'},
    ]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, lonely, content, {'slot-tyre': 98001})
    assert not (run / packaging.RECEIPT).exists()


def test_tyre98_requires_same_target_owner(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    elsewhere = {'bindings': [
        {'target': 'slot-waterwraith', 'source_id': 99, 'enum_name': 'BlackMan'},
        {'target': 'slot-other', 'source_id': 98, 'enum_name': 'Tyre'},
    ]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, elsewhere, content,
                                   {'slot-waterwraith': 99001, 'slot-other': 98001})
    assert not (run / packaging.RECEIPT).exists()


def test_tyre98_missing_actor_mapping_fails_closed(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, LAYOUT_99_TYRE, content, {})
    assert not (run / packaging.RECEIPT).exists()


def test_missing_helper_identity_fails_closed(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    shutil.rmtree(content / 'Tyre')
    run = tmp_path / 'run'
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, LAYOUT_99_TYRE, content, ACTORS_99)
    assert not (run / packaging.RECEIPT).exists()


def test_wrong_helper_identity_fails_closed(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    (content / 'Tyre' / 'identity.json').write_text(json.dumps(
        {'schema': 1, 'source_id': 98, 'enum_name': 'BlackMan'}))
    run = tmp_path / 'run'
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, LAYOUT_99_TYRE, content, ACTORS_99)


def test_duplicate_helper_binding_fails_closed(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    doubled = {'bindings': LAYOUT_99_TYRE['bindings'] + [
        {'target': 'slot-waterwraith', 'source_id': 98, 'enum_name': 'Tyre'},
    ]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, doubled, content, ACTORS_99)


def test_duplicate_generator_across_99_fails_closed(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    doubled = {'bindings': LAYOUT_99['bindings'] + [
        {'target': 'slot-second', 'source_id': 99, 'enum_name': 'BlackMan'},
    ]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, doubled, content,
                                   {'slot-waterwraith': 99001, 'slot-second': 99001})


def test_non_candidate_still_rejected(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    layout = {'bindings': [
        {'target': 'slot-x', 'source_id': 100, 'enum_name': 'Whatever'},
    ]}
    with pytest.raises(StagingError):
        packaging.stage_candidates(run, layout, content, {'slot-x': 1})


def test_cache_replay_with_helpers(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    cache = tmp_path / 'cache'
    first = packaging.stage_candidates(run, LAYOUT_99_TYRE, content, ACTORS_99,
                                       cache_dir=cache)
    assert first.get('cached') is not True
    shutil.rmtree(run)
    shutil.rmtree(content)
    second = packaging.stage_candidates(tmp_path / 'run', LAYOUT_99_TYRE,
                                        tmp_path / 'gone', ACTORS_99,
                                        cache_dir=cache)
    assert second.get('cached') is True
    assert second['plan_digest'] == first['plan_digest']
    assert second['helpers']['Tyre']['generators'] == [99001]
    assert packaging.verify_staging(tmp_path / 'run', LAYOUT_99_TYRE,
                                    ACTORS_99)['verified']


def test_tampered_helper_sidecar_fails_verify(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    packaging.stage_candidates(run, LAYOUT_99_TYRE, content, ACTORS_99)
    with (run / packaging.actors_filename('Tyre')).open('a', encoding='ascii') as stream:
        stream.write('99002 Tyre\n')
    with pytest.raises(StagingError):
        packaging.verify_staging(run, LAYOUT_99_TYRE, ACTORS_99)


def test_plan_digest_disagreement_fails_verify(tmp_path):
    content = seed_waterwraith_content(tmp_path)
    run = tmp_path / 'run'
    packaging.stage_candidates(run, LAYOUT_99, content, ACTORS_99)
    with pytest.raises(StagingError):
        packaging.verify_staging(run, LAYOUT_99_TYRE, ACTORS_99)


if __name__ == '__main__':
    raise SystemExit('Run with pytest: py -3.12 -m pytest tests/test_pikmin2_waterwraith_packaging_provider.py -q')
