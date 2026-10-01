"""Tests for the BlueKochappy44 generated-identity gate-1 observer (#461).

Contract tests over synthetic birth-marker logs: the observer accepts only a
fully correlated natural chain (manifest UID == placement UID == family UID,
health/XYZ match, route evidence, no taint) and rejects every adversarial
class: swapped source, slot/generator mismatch, missing legs, unmapped slot,
bad terrain/route, injected taint, and generator-0 placeholder identity.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    'pikmin2_bluekochappy44_observer',
    ROOT / 'experimental/pikmin2_bluekochappy44_observer.py')
_observer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_observer)

observe_gate1 = _observer.observe_gate1
parse_manifest = _observer.parse_manifest
ObserverError = _observer.ObserverError

MANIFEST = {'source_id': 44, 'generator': 3670065,
            'expected_xyz': [547.06, -71.11, 2503.95], 'health': 250.0}

READY = ('P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy '
         'generator=3670065 x=547.064 y=-71.110 z=2503.953 '
         'health=250.0 max_health=250.0 behavior=native')
PLACEHOLDER = ('P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy '
               'generator=0 x=547.064 y=-71.110 z=2503.953 '
               'health=250.0 max_health=250.0 behavior=generated')
FAMILY = ('P2_KOCHAPPY_STATE generator=3670065 state=wait\n'
          'P2_KOCHAPPY_POS generator=3670065 state=wait x=546.52 z=2503.46\n'
          'P2_KOCHAPPY_POS generator=3670065 state=wait x=544.77 z=2501.87\n'
          'P2_KOCHAPPY_POS generator=3670065 state=wait x=541.85 z=2499.22\n'
          'P2_KOCHAPPY_DEAD generator=3670065 source_id=44 health=0.0')


def test_accepts_fully_correlated_natural_chain():
    result = observe_gate1(MANIFEST, PLACEHOLDER + '\n' + READY + '\n' + FAMILY)
    assert result['gate1_ok'], result['checks']
    assert result['generator'] == 3670065


def test_rejects_swapped_source_on_same_uid():
    log = READY.replace('source_id=44', 'source_id=45', 1) + '\n' + FAMILY
    result = observe_gate1(MANIFEST, log)
    assert not result['gate1_ok']
    assert result['checks']['single_uid'] is False


def test_rejects_slot_generator_mismatch():
    log = READY.replace('generator=3670065', 'generator=3670099') + '\n' + FAMILY.replace('3670065', '3670099')
    result = observe_gate1(MANIFEST, log)
    assert not result['gate1_ok']
    assert result['checks']['single_uid'] is False


def test_rejects_missing_placement_leg():
    result = observe_gate1(MANIFEST, FAMILY)
    assert not result['gate1_ok']
    assert result['checks']['ready_present'] is False


def test_rejects_missing_family_leg():
    result = observe_gate1(MANIFEST, READY)
    assert not result['gate1_ok']
    assert result['checks']['family_bound'] is False


def test_rejects_missing_manifest_leg():
    for bad in ({}, {'source_id': 44}, {'source_id': 44, 'generator': 0, 'expected_xyz': [0, 0, 0]}):
        try:
            observe_gate1(bad, READY + '\n' + FAMILY)
        except ObserverError:
            continue
        raise AssertionError('expected ObserverError')


def test_rejects_unmapped_slot():
    manifest = dict(MANIFEST, generator=9999999)
    result = observe_gate1(manifest, READY + '\n' + FAMILY)
    assert not result['gate1_ok']


def test_rejects_placeholder_only_identity():
    result = observe_gate1(MANIFEST, PLACEHOLDER + '\n' + FAMILY.replace('3670065', '0'))
    assert not result['gate1_ok']
    assert result['checks']['ready_present'] is False


def test_rejects_stray_placeholder_position():
    stray = PLACEHOLDER.replace('x=547.064 y=-71.110 z=2503.953', 'x=100.000 y=30.000 z=100.000')
    result = observe_gate1(MANIFEST, stray + '\n' + READY + '\n' + FAMILY)
    assert not result['gate1_ok']
    assert result['checks']['no_placeholder_identity'] is False


def test_rejects_health_mismatch():
    result = observe_gate1(MANIFEST, READY.replace('health=250.0', 'health=100.0') + '\n' + FAMILY)
    assert not result['gate1_ok']
    assert result['checks']['health_match'] is False


def test_rejects_xyz_mismatch():
    result = observe_gate1(MANIFEST, READY.replace('x=547.064 y=-71.110 z=2503.953', 'x=0.000 y=30.000 z=0.000') + '\n' + FAMILY)
    assert not result['gate1_ok']
    assert result['checks']['xyz_match'] is False


def test_rejects_missing_route_evidence():
    log = READY + '\nP2_KOCHAPPY_STATE generator=3670065 state=wait\n'
    result = observe_gate1(MANIFEST, log)
    assert not result['gate1_ok']
    assert result['checks']['route_evidence'] is False


def test_rejects_static_route_positions():
    static = ('P2_KOCHAPPY_POS generator=3670065 state=wait x=546.52 z=2503.46\n' * 4)
    result = observe_gate1(MANIFEST, READY + '\n' + static)
    assert not result['gate1_ok']
    assert result['checks']['route_evidence'] is False


def test_rejects_injected_taint():
    for taint in ('P2_LIFECYCLE_INJECT kill', 'TELEPORT actor', 'actor->mHealth = 0;'):
        result = observe_gate1(MANIFEST, READY + '\n' + FAMILY + '\n' + taint)
        assert not result['gate1_ok']
        assert result['checks']['no_taint'] is False