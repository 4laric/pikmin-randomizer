"""Lane 04 placement-evidence ingestion tests (#440, assignment 3)."""
import json

import pytest

from randomizer import p2_placement as placement
from randomizer import p2_placement_catalog as catalog
from randomizer import p2_placement_evidence as evidence_mod
from randomizer.campaign_data import CAMPAIGN_SLOTS, CAMPAIGN_SOURCES


def _ground_unprotected_row():
    sources = catalog._campaign_index(CAMPAIGN_SOURCES)
    for row in CAMPAIGN_SLOTS:
        if row.get('cohort') == 'ground' and row.get('position') and not sources.get(row['uid'], {}).get('protected'):
            return row
    raise AssertionError('no ground unprotected campaign slot')


def _evidence(position, route=250.0, stage=1, control_others=49,
              delivered=True, injected=False, onion=None):
    if onion is None:
        onion = [position[0] - 300.0, position[1], position[2] + 40.0]
    return {
        'schema': 'p2-placement-evidence-v1',
        'stage': stage,
        'actor_spawn': list(position),
        'generator_position': list(position),
        'onion': list(onion),
        'route_length': route,
        'control_others': control_others,
        'delivered': delivered,
        'injected': injected,
        'ordinary_ledger': True,
        'pod_ledger': False,
    }


def test_apply_evidence_admits_only_observed_slot_and_listed_identities():
    row = _ground_unprotected_row()
    document = catalog.build_document()
    summary = evidence_mod.apply_evidence(document, _evidence(row['position'], stage=row['stage']),
                                          ['YellowKochappy', 'BlueKochappy'])

    assert summary['slot_uid'] == row['uid']
    assert summary['match_distance'] == pytest.approx(0.0)
    assert summary['delivered'] is True
    slot = next(s for s in document['slots'] if s['uid'] == row['uid'])
    assert slot['evidence'] == {'xyz': True, 'terrain': True, 'route': True}

    result = placement.audit(document)
    assert result['admitted'] == {'YellowKochappy': [row['uid']], 'BlueKochappy': [row['uid']]}
    # Only the observed slot is raised: it is the sole admitted slot for the
    # listed identities, it is not in their denied list, and unlisted identities
    # have no admitted slot at all.
    assert row['uid'] not in result['denied']['YellowKochappy']
    assert row['uid'] not in result['denied']['BlueKochappy']
    assert 'Chappy' not in result['admitted']
    assert 'Kochappy' not in result['admitted']


def test_apply_evidence_requires_identities():
    row = _ground_unprotected_row()
    document = catalog.build_document()
    with pytest.raises(ValueError):
        evidence_mod.apply_evidence(document, _evidence(row['position'], stage=row['stage']), [])
    with pytest.raises(ValueError):
        evidence_mod.apply_evidence(document, _evidence(row['position'], stage=row['stage']), ['NotAnIdentity'])


def test_apply_evidence_rejects_untrustworthy_document():
    row = _ground_unprotected_row()
    document = catalog.build_document()
    for mutate in (
        lambda d: d.update(delivered=False),              # no terminal delivery
        lambda d: d.update(injected=True),                # injected run
        lambda d: d.update(control_others=None),          # no control evidence
        lambda d: d.update(route_length=0),               # stale route0
        lambda d: d.update(onion=None),                   # null Onion
        lambda d: d.update(actor_spawn=[float('nan'), 0, 0]),  # non-finite
        lambda d: d.update(stage=999),                    # stage mismatch
    ):
        bad = _evidence(row['position'], stage=row['stage'])
        mutate(bad)
        with pytest.raises(ValueError):
            evidence_mod.apply_evidence(document, bad, ['YellowKochappy'])


def test_apply_evidence_rejects_far_side_slot_match():
    # An observed XYZ far from every slot on that stage must not raise any slot.
    row = _ground_unprotected_row()
    document = catalog.build_document()
    far = [row['position'][0] + 5000.0, row['position'][1], row['position'][2]]
    with pytest.raises(ValueError):
        evidence_mod.apply_evidence(document, _evidence(far, stage=row['stage']),
                                    ['YellowKochappy'])


def test_apply_evidence_rejects_stage_mismatch():
    row = _ground_unprotected_row()
    document = catalog.build_document()
    # Same XYZ but a different stage must not match the stage-`row` slot.
    other = [s for s in CAMPAIGN_SLOTS if s.get('position') and s.get('stage') != row['stage']]
    assert other
    with pytest.raises(ValueError):
        evidence_mod.apply_evidence(document, _evidence(row['position'], stage=other[0]['stage']),
                                    ['YellowKochappy'])


def test_load_rejects_malformed_documents(tmp_path):
    good = _evidence([0.0, 0.0, 0.0])
    path = tmp_path / 'good.json'
    path.write_text(json.dumps(good), encoding='utf-8')
    assert evidence_mod.load(path)['route_length'] == 250.0

    for mutate in (
        lambda d: d.update(schema='wrong'),
        lambda d: d.pop('actor_spawn'),
        lambda d: d.update(actor_spawn=[1.0, 2.0]),
        lambda d: d.update(route_length=0),
        lambda d: d.update(route_length=float('nan')),
        lambda d: d.update(control_others=None),
        lambda d: d.update(delivered=False),
        lambda d: d.update(injected=True),
        lambda d: d.update(onion=None),
        lambda d: d.update(stage=None),
        lambda d: d.update(ordinary_ledger=False),
        lambda d: d.update(pod_ledger=True),
    ):
        bad = _evidence([1.0, 2.0, 3.0])
        mutate(bad)
        path.write_text(json.dumps(bad), encoding='utf-8')
        with pytest.raises(ValueError):
            evidence_mod.load(path)


def test_is_trustworthy_guards():
    assert evidence_mod.is_trustworthy(_evidence([0.0, 0.0, 0.0]))
    assert not evidence_mod.is_trustworthy(_evidence([0.0, 0.0, 0.0], delivered=False))
    assert not evidence_mod.is_trustworthy(_evidence([0.0, 0.0, 0.0], injected=True))
    assert not evidence_mod.is_trustworthy(_evidence([0.0, 0.0, 0.0], control_others=None))
    assert not evidence_mod.is_trustworthy(_evidence([0.0, 0.0, 0.0], route=0.0))
    assert not evidence_mod.is_trustworthy(_evidence([0.0, 0.0, 0.0], stage=None))
    null_onion = _evidence([0.0, 0.0, 0.0])
    null_onion['onion'] = None
    assert not evidence_mod.is_trustworthy(null_onion)


def test_nearest_campaign_slot_matches_exact_position():
    row = _ground_unprotected_row()
    matched, distance = evidence_mod.nearest_campaign_slot(row['position'])
    assert matched['uid'] == row['uid']
    assert distance == pytest.approx(0.0)


def test_match_slot_requires_stage_and_distance():
    row = _ground_unprotected_row()
    matched, distance = evidence_mod.match_slot(row['position'], row['stage'])
    assert matched['uid'] == row['uid']
    assert distance == pytest.approx(0.0)
    with pytest.raises(ValueError):
        evidence_mod.match_slot([row['position'][0] + 10000.0, 0, 0], row['stage'])


def test_rejected_identity_does_not_partially_approve():
    import copy
    row = _ground_unprotected_row()
    document = catalog.build_document()
    before = copy.deepcopy(document)
    with pytest.raises(ValueError):
        evidence_mod.apply_evidence(document, _evidence(row['position'], stage=row['stage']),
                                    ['YellowKochappy', 'NotAnIdentity'])
    assert document == before


def test_publish_rejects_incomplete_delivery_and_removes_stale_approval(tmp_path):
    path = tmp_path / 'placement-evidence.json'
    good = _evidence([0.0, 0.0, 0.0])
    assert evidence_mod.publish_evidence(path, good)
    assert evidence_mod.load(path) == good
    for field, value in [('delivered', False), ('onion', None), ('control_others', None)]:
        assert evidence_mod.publish_evidence(path, good)
        assert not evidence_mod.publish_evidence(path, dict(good, **{field: value}))
        assert not path.exists()
