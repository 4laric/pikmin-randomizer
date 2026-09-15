"""Contract tests for ``scripts.audit_p2_placement_evidence.run_audit``.

The final contract is::

    def run_audit(probe, catalog_doc=None, identities=IDENTITIES,
                  arena_stage=None, allow_unmapped=False) -> dict

``probe`` is a ``build_probe`` output (or a hand-crafted snapshot of it). When
``probe['unmapped_generators']`` is non-empty and ``allow_unmapped`` is false the
audit hard-fails with ``SystemExit`` (the ``--allow-unmapped`` guard). With a
catalog join, every mapped ``slot`` must exist in ``catalog_doc['slots']`` and,
when ``arena_stage`` is given, the slot's ``stage`` must match; otherwise the
audit stamps ``probe['slots']`` evidence onto the catalog and reports
before/after admission. Without a join it returns an arena-only fallback report.

These tests craft a synthetic ``p2-placement-v1`` catalog document inline (they
never import the full catalog) so the join/mismatch/fallback paths can be
exercised deterministically regardless of the current campaign tables.

The script is a namespace package (``scripts/`` has no ``__init__.py``) so the
repo root is added to ``sys.path`` before importing it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import scripts.audit_p2_placement_evidence as auditplugin
from randomizer import p2_placement, p2_placement_catalog


def _ground_slot(uid, stage):
    return p2_placement.normalize_slot({
        'uid': uid, 'label': f'slot-{uid}', 'stage': stage, 'terrain': 'ground',
        'radius': 100.0, 'corpse_route': True,
    })


def _water_slot(uid, stage):
    return p2_placement.normalize_slot({
        'uid': uid, 'label': f'slot-{uid}', 'stage': stage, 'terrain': 'water',
        'radius': 100.0, 'corpse_route': True, 'water_depth': 2.0,
    })


def _profile(identity):
    return p2_placement.normalize_profile({
        'identity': identity, 'terrains': ['ground'], 'requires_corpse_route': True,
        'accepted_gates': [],
    })


def catalog_doc():
    return p2_placement.validate_document({
        'schema': p2_placement.SCHEMA,
        'slots': [
            _ground_slot(111, 0),
            _ground_slot(222, 3),
            _ground_slot(333, 0),
            _water_slot(444, 0),
        ],
        'profiles': [_profile('YellowKochappy'), _profile('BlueKochappy')],
    })


def _probe(mapping, unmapped=None, slots=None):
    """Craft a snapshot matching ``build_probe`` output shape."""
    return {
        'schema': 'p2-placement-probe-v1',
        'catalog_join': bool(mapping),
        'mapping': mapping,
        'slots': slots if slots is not None else [
            {'uid': m['slot'], 'xyz': m['xyz'], 'terrain': m['terrain'],
             'route': m['route']} for m in mapping
        ],
        'unmapped_generators': unmapped if unmapped is not None else [],
    }


def _mapping(slot, xyz=True, terrain=True, route=True):
    return [{
        'generator': 211001, 'slot': slot, 'xyz': xyz, 'terrain': terrain,
        'route': route, 'position': [-150.0, 30.0, 1850.0],
    }]


def test_unmatched_mapped_uid_raises():
    probe = _probe(_mapping(999999999))
    with pytest.raises(SystemExit):
        auditplugin.run_audit(probe, catalog_doc=catalog_doc())


def test_matched_stamping_admits_injected():
    probe = _probe(_mapping(111))
    report = auditplugin.run_audit(probe, catalog_doc=catalog_doc(), arena_stage=0)
    assert report['catalog_join'] is True
    assert report['matched_slot_uids'] == [111]
    assert report['injected_legal_admitted']['YellowKochappy'] == [111]
    assert report['injected_legal_admitted']['BlueKochappy'] == [111]
    assert report['slot_evidence']['111'] == {'xyz': True, 'terrain': True, 'route': True}


def test_stage_mismatch_raises():
    probe = _probe(_mapping(222))
    with pytest.raises(SystemExit):
        auditplugin.run_audit(probe, catalog_doc=catalog_doc(), arena_stage=0)


def test_unmapped_generator_fails_without_allow():
    probe = _probe(_mapping(111), unmapped=[211002])
    with pytest.raises(SystemExit):
        auditplugin.run_audit(probe, catalog_doc=catalog_doc())
    report = auditplugin.run_audit(probe, catalog_doc=catalog_doc(), allow_unmapped=True)
    assert report['catalog_join'] is True
    assert report['unmapped_generators'] == [211002]


def test_arena_only_fallback():
    probe = _probe([], unmapped=[])
    report = auditplugin.run_audit(probe, catalog_doc=catalog_doc())
    assert report['catalog_join'] is False
    assert 'catalog_join_note' in report
    assert report['unmapped_generators'] == []
